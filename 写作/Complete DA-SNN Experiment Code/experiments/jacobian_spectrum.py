"""Empirical Jacobian and gradient-stability analysis for DA-SNN.

This experiment compares fixed and adaptive time windows using:

* exact, per-sample local Jacobians of the implemented ``SpikingDense`` maps;
* cumulative Jacobians through the complete spike-time stack; and
* real parameter-gradient norms measured before and after global clipping.

The DA-SNN layers are rectangular, so the reported spectra are singular-value
spectra.  They are empirical conditioning diagnostics, not eigenvalue
unit-circle reproductions and not theoretical guarantees of stable training.

Every invocation creates a new child directory below ``--output-dir``.  An
existing run directory is never reused, which protects earlier experiment data.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import resolve_feature_file
from common.data_loader import EEGTensorDataset, load_feature_bundle
from common.model_builder import build_model
from common.noise_injector import inject_noise
from common.trainer import _update_time_windows, set_seed
from model.TTFS import DA_SNN, SpikingDense


MATRIX_ORDER = ("J1", "J2", "Jout", "J1_2", "J1_out")
CONDITIONS = {"Fixed Window": False, "Adaptive Window": True}
GRADIENT_FIELDS = (
    "condition",
    "seed",
    "epoch",
    "batch",
    "scope",
    "layer",
    "parameter",
    "pre_clip_norm",
    "post_clip_norm",
    "is_finite_pre",
    "is_finite_post",
    "global_pre_clip_norm",
    "clip_factor",
    "clip_applied",
    "optimizer_step",
)


# ---------------------------------------------------------------------------
# Run isolation and deterministic sampling
# ---------------------------------------------------------------------------


def _create_run_dir(output_root: Path | str, run_id: str | None, seed: int) -> Path:
    """Create and return a new run directory without overwriting prior data."""
    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    if run_id is None:
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S_%f")
        run_id = f"seed_{seed}_{stamp}"
    if not run_id or Path(run_id).name != run_id or run_id in {".", ".."}:
        raise ValueError("run_id must be one non-empty directory name")
    run_dir = root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    return run_dir


def _select_analysis_indices(val_indices: np.ndarray, count: int, seed: int) -> np.ndarray:
    """Select sorted, unique validation-set indices reproducibly."""
    if count < 1:
        raise ValueError("Jacobian sample count must be at least 1")
    available = np.unique(np.asarray(val_indices, dtype=np.int64).reshape(-1))
    if available.size < count:
        raise ValueError(
            f"Jacobian analysis requested {count} samples, but only "
            f"available {available.size} validation samples"
        )
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(available, size=count, replace=False)).astype(np.int64)


def _parse_stage_epochs(value: str, max_epochs: int) -> list[int]:
    if max_epochs < 0:
        raise ValueError("max_epochs must be non-negative")
    epochs: list[int] = []
    for token in value.split(","):
        token = token.strip().lower()
        if not token:
            continue
        epoch = max_epochs if token == "max" else int(token)
        if epoch < 0 or epoch > max_epochs:
            raise ValueError(f"stage epoch {epoch} is outside [0, {max_epochs}]")
        epochs.append(epoch)
    epochs.extend((0, max_epochs))
    return sorted(set(epochs))


# ---------------------------------------------------------------------------
# Exact per-sample Jacobians
# ---------------------------------------------------------------------------


def analytical_hidden_jacobian(
    layer: SpikingDense,
    input_times: torch.Tensor,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Return the exact local Jacobian of one hidden ``SpikingDense`` map.

    The implemented hidden map is affine followed by an upper clipping branch.
    Consequently, active output rows equal ``kernel.T`` and clipped output rows
    are zero.  No extra presynaptic mask is inserted: previous-layer clipping
    enters a cumulative Jacobian through matrix multiplication.
    """
    if layer.outputLayer:
        raise ValueError("analytical_hidden_jacobian requires a hidden layer")
    x = input_times.reshape(-1)
    with torch.no_grad():
        output, _ = layer(x.unsqueeze(0))
        output = output.squeeze(0)
        mask = torch.isfinite(output) & (output < layer.t_max)
        jacobian = layer.kernel.transpose(0, 1).detach().clone()
        jacobian = jacobian * mask.to(jacobian.dtype).unsqueeze(1)
    return jacobian, output.detach(), mask.detach()


def _output_local_jacobian(layer: SpikingDense) -> torch.Tensor:
    if not layer.outputLayer:
        raise ValueError("_output_local_jacobian requires the output layer")
    # output = (t_min - input_times) @ kernel + a parameter-only term
    return -layer.kernel.transpose(0, 1).detach().clone()


def collect_spiking_stack_state(model: DA_SNN, x_single: torch.Tensor) -> list[dict[str, object]]:
    """Run one sample and retain inputs, outputs, and masks for every SNN layer."""
    current = x_single.unsqueeze(0)
    states: list[dict[str, object]] = []
    with torch.no_grad():
        for layer in model.layers_list:
            if isinstance(layer, SpikingDense):
                layer_input = current
                current, _ = layer(current)
                output = current.squeeze(0)
                mask = None if layer.outputLayer else (
                    torch.isfinite(output) & (output < layer.t_max)
                )
                states.append(
                    {
                        "layer": layer,
                        "input": layer_input.squeeze(0).detach(),
                        "output": output.detach(),
                        "mask": None if mask is None else mask.detach(),
                    }
                )
            else:
                current = layer(current)
                if isinstance(current, tuple):
                    current = current[0]
    return states


def compute_sample_jacobians(model: DA_SNN, x_single: torch.Tensor) -> dict[str, torch.Tensor]:
    """Compute full local and cumulative spike-time Jacobians for one sample."""
    states = collect_spiking_stack_state(model, x_single)
    hidden_states = [state for state in states if not state["layer"].outputLayer]
    output_states = [state for state in states if state["layer"].outputLayer]
    if not hidden_states:
        raise ValueError("model has no hidden SpikingDense layers")
    if len(output_states) != 1:
        raise ValueError("model must have exactly one output SpikingDense layer")

    matrices: dict[str, torch.Tensor] = {}
    cumulative: torch.Tensor | None = None
    for index, state in enumerate(hidden_states, start=1):
        layer = state["layer"]
        mask = state["mask"]
        local = layer.kernel.transpose(0, 1).detach().clone()
        local = local * mask.to(local.dtype).unsqueeze(1)
        matrices[f"J{index}"] = local
        cumulative = local if cumulative is None else local @ cumulative
        if index > 1:
            matrices[f"J1_{index}"] = cumulative

    output_layer = output_states[0]["layer"]
    output_local = _output_local_jacobian(output_layer)
    matrices["Jout"] = output_local
    matrices["J1_out"] = output_local @ cumulative
    return matrices


def summarize_singular_values(
    matrix: torch.Tensor,
    zero_tol: float = 1e-8,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Return all singular values and finite-aware conditioning diagnostics."""
    if matrix.ndim != 2:
        raise ValueError("Jacobian matrix must be two-dimensional")
    values_t = torch.linalg.svdvals(matrix.detach().to(dtype=torch.float64))
    values = values_t.cpu().numpy().astype(np.float64, copy=False)
    sigma_max = float(values.max()) if values.size else 0.0
    adaptive_tol = np.finfo(np.float64).eps * max(matrix.shape) * sigma_max
    tolerance = float(max(zero_tol, adaptive_tol))
    nonzero = values[values > tolerance]
    rank = int(nonzero.size)
    if rank:
        sigma_min = float(nonzero.min())
        condition = float(sigma_max / sigma_min)
        mean_abs_log = float(np.mean(np.abs(np.log(nonzero))))
    else:
        sigma_min = float("nan")
        condition = float("nan")
        mean_abs_log = float("nan")
    total = int(values.size)
    summary: dict[str, float | int] = {
        "sigma_count": total,
        "sigma_max": sigma_max,
        "sigma_min_nonzero": sigma_min,
        "effective_rank": rank,
        "condition_number": condition,
        "mean_abs_log_sigma": mean_abs_log,
        "frac_above_one": float(np.mean(values > 1.0)) if total else float("nan"),
        "frac_near_zero": float(np.mean(values <= tolerance)) if total else float("nan"),
        "zero_tolerance": tolerance,
    }
    return values, summary


# ---------------------------------------------------------------------------
# Real gradient measurements
# ---------------------------------------------------------------------------


def _norm_and_finiteness(tensors: Iterable[torch.Tensor]) -> tuple[float, bool]:
    squared = 0.0
    seen = False
    finite = True
    for tensor in tensors:
        seen = True
        detached = tensor.detach()
        tensor_finite = bool(torch.isfinite(detached).all().item())
        finite = finite and tensor_finite
        if tensor_finite:
            squared += float(torch.sum(detached.to(torch.float64) ** 2).item())
    if not seen:
        return 0.0, True
    return (math.sqrt(squared), True) if finite else (float("nan"), False)


def _gradient_norm_rows(model: nn.Module) -> list[dict[str, object]]:
    """Measure model-, SNN-layer-, and SNN-parameter-level gradient norms."""
    all_gradients = [p.grad for p in model.parameters() if p.grad is not None]
    total_norm, total_finite = _norm_and_finiteness(all_gradients)
    rows: list[dict[str, object]] = [
        {
            "scope": "model",
            "layer": "all",
            "parameter": "all",
            "grad_norm": total_norm,
            "is_finite": total_finite,
            "grad_present": bool(all_gradients),
        }
    ]
    for module in model.modules():
        if not isinstance(module, SpikingDense):
            continue
        named = [(name, parameter) for name, parameter in module.named_parameters(recurse=False)]
        layer_gradients = [parameter.grad for _, parameter in named if parameter.grad is not None]
        layer_norm, layer_finite = _norm_and_finiteness(layer_gradients)
        rows.append(
            {
                "scope": "layer",
                "layer": module.name,
                "parameter": "all",
                "grad_norm": layer_norm,
                "is_finite": layer_finite,
                "grad_present": bool(layer_gradients),
            }
        )
        for parameter_name, parameter in named:
            gradients = [] if parameter.grad is None else [parameter.grad]
            parameter_norm, parameter_finite = _norm_and_finiteness(gradients)
            rows.append(
                {
                    "scope": "parameter",
                    "layer": module.name,
                    "parameter": parameter_name,
                    "grad_norm": parameter_norm,
                    "is_finite": parameter_finite,
                    "grad_present": parameter.grad is not None,
                }
            )
    return rows


def _all_gradients_finite(model: nn.Module) -> bool:
    return all(
        bool(torch.isfinite(parameter.grad).all().item())
        for parameter in model.parameters()
        if parameter.grad is not None
    )


def _merge_gradient_phases(
    before: list[dict[str, object]],
    after: list[dict[str, object]],
    *,
    condition: str,
    seed: int,
    epoch: int,
    batch: int,
    max_norm: float,
    optimizer_step: bool,
) -> list[dict[str, object]]:
    post = {(row["scope"], row["layer"], row["parameter"]): row for row in after}
    global_before = next(row for row in before if row["scope"] == "model")
    global_norm = float(global_before["grad_norm"])
    if math.isfinite(global_norm):
        clip_factor = min(1.0, max_norm / (global_norm + 1e-6))
        clip_applied = global_norm > max_norm
    else:
        clip_factor = float("nan")
        clip_applied = False
    merged = []
    for row in before:
        key = (row["scope"], row["layer"], row["parameter"])
        post_row = post[key]
        merged.append(
            {
                "condition": condition,
                "seed": seed,
                "epoch": epoch,
                "batch": batch,
                "scope": row["scope"],
                "layer": row["layer"],
                "parameter": row["parameter"],
                "pre_clip_norm": row["grad_norm"],
                "post_clip_norm": post_row["grad_norm"],
                "is_finite_pre": row["is_finite"],
                "is_finite_post": post_row["is_finite"],
                "global_pre_clip_norm": global_norm,
                "clip_factor": clip_factor,
                "clip_applied": clip_applied,
                "optimizer_step": optimizer_step,
            }
        )
    return merged


def train_one_epoch_instrumented(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: optim.Optimizer,
    device: torch.device,
    gamma_ttfs: float,
    *,
    condition: str,
    seed: int,
    epoch: int,
    max_grad_norm: float = 1.0,
    gradient_log_every: int = 1,
    max_batches: int | None = None,
) -> tuple[float, float, list[dict[str, object]]]:
    """Train one epoch while preserving pre-clipping gradient measurements."""
    if gradient_log_every < 1:
        raise ValueError("gradient_log_every must be at least 1")
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    gradient_rows: list[dict[str, object]] = []
    for batch_idx, (features, labels) in enumerate(loader):
        if max_batches is not None and batch_idx >= max_batches:
            break
        features = features.to(device)
        labels = labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(features)
        logits = outputs[0] if isinstance(outputs, tuple) else outputs
        loss = criterion(logits, labels)
        loss.backward()

        should_log = batch_idx % gradient_log_every == 0
        before = _gradient_norm_rows(model) if should_log else []
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=max_grad_norm)
        finite = _all_gradients_finite(model)
        after = _gradient_norm_rows(model) if should_log else []
        if finite:
            optimizer.step()
        else:
            optimizer.zero_grad(set_to_none=True)
        if isinstance(outputs, tuple):
            _update_time_windows(model, outputs[1], gamma_ttfs)
        if should_log:
            gradient_rows.extend(
                _merge_gradient_phases(
                    before,
                    after,
                    condition=condition,
                    seed=seed,
                    epoch=epoch,
                    batch=batch_idx,
                    max_norm=max_grad_norm,
                    optimizer_step=finite,
                )
            )
        running_loss += float(loss.item()) * labels.size(0)
        correct += int((logits.argmax(dim=1) == labels).sum().item())
        total += int(labels.size(0))
    return running_loss / max(total, 1), correct / max(total, 1), gradient_rows


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=np.float64)
    finite = arr[np.isfinite(arr)]
    if not finite.size:
        return {
            "count": int(arr.size),
            "finite_count": 0,
            "mean": float("nan"),
            "std": float("nan"),
            "median": float("nan"),
            "q25": float("nan"),
            "q75": float("nan"),
            "iqr": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
            "coefficient_of_variation": float("nan"),
        }
    mean = float(np.mean(finite))
    std = float(np.std(finite, ddof=1)) if finite.size > 1 else 0.0
    q25, median, q75 = (float(v) for v in np.percentile(finite, [25, 50, 75]))
    return {
        "count": int(arr.size),
        "finite_count": int(finite.size),
        "mean": mean,
        "std": std,
        "median": median,
        "q25": q25,
        "q75": q75,
        "iqr": q75 - q25,
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "coefficient_of_variation": std / abs(mean) if abs(mean) > 1e-12 else float("nan"),
    }


def _summarize_gradient_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        key = (row["condition"], row["seed"], row["epoch"], row["scope"], row["layer"], row["parameter"])
        grouped[key].append(row)
    summaries: list[dict[str, object]] = []
    for key, group in sorted(grouped.items(), key=lambda item: tuple(str(v) for v in item[0])):
        condition, seed, epoch, scope, layer, parameter = key
        pre = _distribution([float(row["pre_clip_norm"]) for row in group])
        post = _distribution([float(row["post_clip_norm"]) for row in group])
        summary: dict[str, object] = {
            "condition": condition,
            "seed": seed,
            "epoch": epoch,
            "scope": scope,
            "layer": layer,
            "parameter": parameter,
        }
        summary.update({f"pre_clip_{name}": value for name, value in pre.items()})
        summary.update({f"post_clip_{name}": value for name, value in post.items()})
        summary["nonfinite_rate"] = float(np.mean([not bool(row["is_finite_pre"]) for row in group]))
        summary["clipping_rate"] = float(np.mean([bool(row["clip_applied"]) for row in group]))
        summary["optimizer_step_rate"] = float(np.mean([bool(row["optimizer_step"]) for row in group]))
        summaries.append(summary)
    return summaries


# ---------------------------------------------------------------------------
# Data/model construction and stage analysis
# ---------------------------------------------------------------------------


def _resolve_device(name: str) -> torch.device:
    if name == "cpu":
        return torch.device("cpu")
    if name == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested but is unavailable")
        return torch.device("cuda")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _load_bundle_and_split(args):
    base = Path(__file__).resolve().parent.parent
    feature_path = resolve_feature_file(args.dataset, args.feature_file)
    if not feature_path.is_absolute():
        feature_path = base / feature_path
    bundle = load_feature_bundle(feature_path, dataset=args.dataset, require_metadata=False)
    indices = np.arange(bundle.labels.shape[0])
    train_idx, _test_idx = train_test_split(
        indices,
        test_size=0.2,
        random_state=args.seed,
        shuffle=True,
        stratify=bundle.labels,
    )
    train_idx, val_idx = train_test_split(
        train_idx,
        test_size=0.1 / 0.8,
        random_state=args.seed,
        shuffle=True,
        stratify=bundle.labels[train_idx],
    )
    return bundle, np.asarray(train_idx, dtype=np.int64), np.asarray(val_idx, dtype=np.int64)


def _warmup_model(model: nn.Module, loader: DataLoader, device: torch.device, max_batches: int = 3) -> None:
    model.train()
    with torch.no_grad():
        for batch_idx, (features, _) in enumerate(loader):
            model(features.to(device))
            if batch_idx + 1 >= max_batches:
                break


def _build_model_and_loaders(args, use_dynamic_window, bundle, train_idx, val_idx, device):
    set_seed(args.seed)
    model = build_model(
        "da_snn",
        args.dataset,
        device,
        da_snn_options={
            "use_depthwise_separable": True,
            "use_dsgm": True,
            "use_ttfs_encoder": True,
            "use_dynamic_window": use_dynamic_window,
        },
    )
    generator = torch.Generator()
    generator.manual_seed(args.seed)
    train_ds = EEGTensorDataset(bundle.features, bundle.labels, train_idx)
    val_ds = EEGTensorDataset(bundle.features, bundle.labels, val_idx)
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=0,
        generator=generator,
    )
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    _warmup_model(model, train_loader, device)
    return model, train_loader, val_loader


def _analyze_stage(model, bundle, selected_indices, condition, seed, epoch, device):
    was_training = model.training
    model.eval()
    per_sample_rows: list[dict[str, object]] = []
    singular_arrays: dict[str, np.ndarray] = {}
    for sample_index in selected_indices:
        sample = torch.as_tensor(bundle.features[int(sample_index)], dtype=torch.float32, device=device)
        matrices = compute_sample_jacobians(model, sample)
        for matrix_name, matrix in matrices.items():
            singular_values, metrics = summarize_singular_values(matrix)
            row: dict[str, object] = {
                "condition": condition,
                "seed": seed,
                "stage": f"epoch_{epoch}",
                "epoch": epoch,
                "sample_index": int(sample_index),
                "matrix": matrix_name,
                "rows": int(matrix.shape[0]),
                "columns": int(matrix.shape[1]),
            }
            row.update(metrics)
            per_sample_rows.append(row)
            key = _safe_token(f"{condition}__epoch_{epoch}__sample_{sample_index}__{matrix_name}")
            singular_arrays[key] = singular_values
    model.train(was_training)
    return per_sample_rows, singular_arrays


def _summarize_jacobian_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metrics = (
        "sigma_max",
        "sigma_min_nonzero",
        "effective_rank",
        "condition_number",
        "mean_abs_log_sigma",
        "frac_above_one",
        "frac_near_zero",
    )
    grouped: dict[tuple, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(row["condition"], row["seed"], row["stage"], row["epoch"], row["matrix"])].append(row)
    summaries: list[dict[str, object]] = []
    for key, group in sorted(grouped.items(), key=lambda item: tuple(str(v) for v in item[0])):
        condition, seed, stage, epoch, matrix = key
        summary: dict[str, object] = {
            "condition": condition,
            "seed": seed,
            "stage": stage,
            "epoch": epoch,
            "matrix": matrix,
            "sample_count": len(group),
        }
        for metric in metrics:
            distribution = _distribution([float(row[metric]) for row in group])
            for statistic in ("mean", "std", "median", "q25", "q75", "min", "max"):
                summary[f"{metric}_{statistic}"] = distribution[statistic]
        summaries.append(summary)
    return summaries


# ---------------------------------------------------------------------------
# Output and visualization
# ---------------------------------------------------------------------------


def _safe_token(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value).strip("_")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: Sequence[str] | None = None) -> None:
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        if not fieldnames:
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False, allow_nan=True, default=str)


def _matrix_sort_key(name: str) -> tuple[int, str]:
    try:
        return MATRIX_ORDER.index(name), name
    except ValueError:
        return len(MATRIX_ORDER), name


def plot_stability_diagnostics(
    jacobian_rows: list[dict[str, object]],
    singular_arrays: dict[str, np.ndarray],
    gradient_summaries: list[dict[str, object]],
    save_dir: Path,
) -> None:
    """Create a four-panel reviewer-facing diagnostic figure."""
    colors = {"Fixed Window": "#2878B5", "Adaptive Window": "#D95319"}
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    # (a) Final-stage cumulative singular-value distribution.
    ax = axes[0, 0]
    final_epoch = max((int(row["epoch"]) for row in jacobian_rows), default=0)
    for condition in CONDITIONS:
        values = []
        prefix = _safe_token(f"{condition}__epoch_{final_epoch}")
        suffix = _safe_token("J1_out")
        for key, array in singular_arrays.items():
            if key.startswith(prefix) and key.endswith(suffix):
                values.extend(np.asarray(array, dtype=float).tolist())
        values_arr = np.asarray(values, dtype=float)
        values_arr = values_arr[np.isfinite(values_arr) & (values_arr > 0)]
        if values_arr.size:
            ax.hist(
                np.log10(values_arr),
                bins=min(30, max(8, int(np.sqrt(values_arr.size)))),
                density=True,
                histtype="step",
                linewidth=2,
                color=colors[condition],
                label=condition,
            )
    ax.axvline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set_title("(a) Cumulative Jacobian singular values")
    ax.set_xlabel(r"$\log_{10}(\sigma)$; 0 corresponds to $\sigma=1$")
    ax.set_ylabel("Density")
    ax.legend(fontsize=8)

    # (b) Per-sample cumulative sigma_max by stage.
    ax = axes[0, 1]
    epochs = sorted({int(row["epoch"]) for row in jacobian_rows})
    for condition in CONDITIONS:
        means, lows, highs = [], [], []
        for epoch in epochs:
            values = np.asarray(
                [
                    float(row["sigma_max"])
                    for row in jacobian_rows
                    if row["condition"] == condition
                    and int(row["epoch"]) == epoch
                    and row["matrix"] == "J1_out"
                ],
                dtype=float,
            )
            values = values[np.isfinite(values)]
            means.append(float(np.median(values)) if values.size else np.nan)
            lows.append(float(np.percentile(values, 25)) if values.size else np.nan)
            highs.append(float(np.percentile(values, 75)) if values.size else np.nan)
        ax.plot(epochs, means, marker="o", color=colors[condition], label=condition)
        ax.fill_between(epochs, lows, highs, color=colors[condition], alpha=0.18)
    ax.axhline(1.0, color="black", linestyle="--", linewidth=1)
    ax.set_yscale("log")
    ax.set_title(r"(b) Cumulative $\sigma_{max}$ (median and IQR)")
    ax.set_xlabel("Epoch")
    ax.set_ylabel(r"$\sigma_{max}$")
    ax.legend(fontsize=8)

    # (c) Pre-clipping layer-gradient trajectories.
    ax = axes[1, 0]
    layer_rows = [row for row in gradient_summaries if row["scope"] == "layer"]
    layers = sorted({str(row["layer"]) for row in layer_rows})
    linestyles = ["-", "--", ":", "-."]
    for condition in CONDITIONS:
        for layer_index, layer in enumerate(layers):
            subset = sorted(
                [row for row in layer_rows if row["condition"] == condition and row["layer"] == layer],
                key=lambda row: int(row["epoch"]),
            )
            if not subset:
                continue
            ax.plot(
                [int(row["epoch"]) for row in subset],
                [max(float(row["pre_clip_median"]), 1e-16) for row in subset],
                color=colors[condition],
                linestyle=linestyles[layer_index % len(linestyles)],
                linewidth=1.5,
                label=f"{condition} / {layer}",
            )
    ax.set_yscale("log")
    ax.set_title("(c) Pre-clipping gradient norms")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Median L2 norm")
    ax.legend(fontsize=6, ncol=2)

    # (d) Clipping rate by condition and epoch.
    ax = axes[1, 1]
    model_rows = [row for row in gradient_summaries if row["scope"] == "model"]
    gradient_epochs = sorted({int(row["epoch"]) for row in model_rows})
    heat = np.full((len(CONDITIONS), len(gradient_epochs)), np.nan)
    for condition_index, condition in enumerate(CONDITIONS):
        for epoch_index, epoch in enumerate(gradient_epochs):
            match = [
                row for row in model_rows
                if row["condition"] == condition and int(row["epoch"]) == epoch
            ]
            if match:
                heat[condition_index, epoch_index] = float(match[0]["clipping_rate"])
    image = ax.imshow(heat, aspect="auto", vmin=0.0, vmax=1.0, cmap="magma")
    ax.set_yticks(np.arange(len(CONDITIONS)), labels=list(CONDITIONS))
    if gradient_epochs:
        tick_positions = np.linspace(0, len(gradient_epochs) - 1, min(6, len(gradient_epochs))).astype(int)
        ax.set_xticks(tick_positions, labels=[gradient_epochs[index] for index in tick_positions])
    ax.set_title("(d) Global-gradient clipping rate")
    ax.set_xlabel("Epoch")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Fraction of logged batches")

    fig.suptitle("DA-SNN empirical Jacobian and gradient diagnostics", fontweight="bold")
    fig.tight_layout()
    fig.savefig(save_dir / "jacobian_gradient_stability.png", dpi=300, bbox_inches="tight")
    fig.savefig(save_dir / "jacobian_gradient_stability.pdf", bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------


def run_jacobian_experiment(args) -> Path:
    """Run one seed and return its newly created, non-overwriting directory."""
    run_dir = _create_run_dir(args.output_dir, args.run_id, args.seed)
    stage_epochs = _parse_stage_epochs(args.stage_epochs, args.max_epochs)
    device = _resolve_device(args.device)
    bundle, train_idx, val_idx = _load_bundle_and_split(args)
    selected_indices = _select_analysis_indices(val_idx, args.jacobian_samples, args.seed)

    artifact_names = [
        "jacobian_per_sample.csv",
        "jacobian_summary.csv",
        "jacobian_singular_values.npz",
        "gradient_per_batch.csv",
        "gradient_per_epoch.csv",
        "run_manifest.json",
        "jacobian_gradient_stability.png",
        "jacobian_gradient_stability.pdf",
    ]
    manifest: dict[str, object] = {
        "status": "running",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "arguments": vars(args),
        "device": str(device),
        "stage_epochs": stage_epochs,
        "selected_validation_indices": selected_indices.tolist(),
        "artifacts": artifact_names,
        "jacobian_scope": "spike-time stack after encoder through logits",
        "spectrum_type": "singular values of per-sample full matrices",
        "interpretation": "empirical relative-conditioning diagnostic; not a stability guarantee",
    }
    _write_json(run_dir / "run_manifest.json", manifest)

    all_jacobian_rows: list[dict[str, object]] = []
    all_singular_arrays: dict[str, np.ndarray] = {}
    all_gradient_summaries: list[dict[str, object]] = []
    gradient_path = run_dir / "gradient_per_batch.csv"
    with gradient_path.open("w", newline="", encoding="utf-8") as gradient_handle:
        gradient_writer = csv.DictWriter(gradient_handle, fieldnames=GRADIENT_FIELDS)
        gradient_writer.writeheader()

        for condition, use_dynamic_window in CONDITIONS.items():
            model, train_loader, _val_loader = _build_model_and_loaders(
                args, use_dynamic_window, bundle, train_idx, val_idx, device
            )
            criterion = nn.CrossEntropyLoss()
            optimizer = optim.Adam(model.parameters(), lr=args.lr)

            stage_rows, stage_arrays = _analyze_stage(
                model, bundle, selected_indices, condition, args.seed, 0, device
            )
            all_jacobian_rows.extend(stage_rows)
            all_singular_arrays.update(stage_arrays)

            for epoch in range(1, args.max_epochs + 1):
                loss, accuracy, gradient_rows = train_one_epoch_instrumented(
                    model,
                    train_loader,
                    criterion,
                    optimizer,
                    device,
                    args.gamma_ttfs,
                    condition=condition,
                    seed=args.seed,
                    epoch=epoch,
                    gradient_log_every=args.gradient_log_every,
                    max_batches=args.max_train_batches,
                )
                gradient_writer.writerows(gradient_rows)
                gradient_handle.flush()
                all_gradient_summaries.extend(_summarize_gradient_rows(gradient_rows))
                print(
                    f"[{condition}] epoch {epoch}/{args.max_epochs}: "
                    f"loss={loss:.6f}, accuracy={accuracy:.4f}",
                    flush=True,
                )
                if epoch in stage_epochs:
                    stage_rows, stage_arrays = _analyze_stage(
                        model, bundle, selected_indices, condition, args.seed, epoch, device
                    )
                    all_jacobian_rows.extend(stage_rows)
                    all_singular_arrays.update(stage_arrays)

    jacobian_summary = _summarize_jacobian_rows(all_jacobian_rows)
    _write_csv(run_dir / "jacobian_per_sample.csv", all_jacobian_rows)
    _write_csv(run_dir / "jacobian_summary.csv", jacobian_summary)
    np.savez_compressed(run_dir / "jacobian_singular_values.npz", **all_singular_arrays)
    _write_csv(run_dir / "gradient_per_epoch.csv", all_gradient_summaries)
    plot_stability_diagnostics(
        all_jacobian_rows,
        all_singular_arrays,
        all_gradient_summaries,
        run_dir,
    )
    manifest["status"] = "completed"
    manifest["completed_at"] = datetime.now().isoformat(timespec="seconds")
    manifest["jacobian_record_count"] = len(all_jacobian_rows)
    manifest["gradient_summary_record_count"] = len(all_gradient_summaries)
    _write_json(run_dir / "run_manifest.json", manifest)
    return run_dir


def parse_args(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Per-sample full Jacobian and real-gradient analysis for DA-SNN",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="seed",
        choices=["seed", "seediv", "seedv", "deap", "dreamer"],
    )
    parser.add_argument("--protocol", type=str, default="random_80_20")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--gamma-ttfs", type=float, default=10.0)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--stage-epochs", type=str, default="0,5,max")
    parser.add_argument("--jacobian-samples", type=int, default=32)
    parser.add_argument("--gradient-log-every", type=int, default=1)
    parser.add_argument("--max-train-batches", type=int, default=None)
    parser.add_argument("--feature-file", type=str, default=None)
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output root; every run creates a new child directory",
    )
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args(argv)
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.jacobian_samples < 1:
        parser.error("--jacobian-samples must be at least 1")
    if args.gradient_log_every < 1:
        parser.error("--gradient-log-every must be at least 1")
    if args.max_train_batches is not None and args.max_train_batches < 1:
        parser.error("--max-train-batches must be at least 1")
    try:
        _parse_stage_epochs(args.stage_epochs, args.max_epochs)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    return args


if __name__ == "__main__":
    cli_args = parse_args()
    if cli_args.output_dir is None:
        project_root = Path(__file__).resolve().parent.parent
        cli_args.output_dir = str(project_root / "experiment_outputs" / "jacobian_spectrum")
    print("DA-SNN Jacobian and gradient-stability diagnostics")
    print(f"  Dataset: {cli_args.dataset}")
    print(f"  Protocol metadata: {cli_args.protocol}")
    print(f"  Seed: {cli_args.seed}")
    print(f"  Jacobian samples: {cli_args.jacobian_samples}")
    print(f"  Output root: {cli_args.output_dir}")
    completed_dir = run_jacobian_experiment(cli_args)
    print(f"Completed run: {completed_dir}")
