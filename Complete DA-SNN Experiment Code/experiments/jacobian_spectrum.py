from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from common.config import DATASET_CONFIGS, resolve_feature_file
from common.data_loader import EEGTensorDataset, build_splits, load_feature_bundle
from common.model_builder import build_model
from common.trainer import ExperimentConfig, set_seed, train_one_epoch, evaluate, _make_train_val_indices
from model.TTFS import DA_SNN, SpikingDense, DF_TTFS_Encoder


def parse_args():
    parser = argparse.ArgumentParser(description="Jacobian spectrum analysis for DA-SNN.")
    parser.add_argument("--dataset", choices=DATASET_CONFIGS.keys(), default="seed")
    parser.add_argument("--protocol", choices=("loso", "subject_80_20", "random_80_20"), default="random_80_20")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--output-dir", default="experiment_outputs/t10_jacobian")
    parser.add_argument("--split-dir", default="splits")
    parser.add_argument("--fixed-window", action="store_true")
    parser.add_argument("--measure-at", nargs="+", type=int, default=[0, 20, 200])
    parser.add_argument("--power-iters", type=int, default=15)
    parser.add_argument("--feature-file", default=None, help="Override default feature file path")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    return parser.parse_args()


class JacobianHook:
    def __init__(self):
        self.T_in = None
        self.T_out = None
        self.M_out = None
        self.handle = None

    def hook_fn(self, module, input_tensors, output_tensors):
        tj = input_tensors[0].detach()
        t_out = output_tensors[0].detach()
        min_ti_info = output_tensors[1]
        self.T_in = tj
        self.T_out = t_out
        if min_ti_info is not None and isinstance(min_ti_info, tuple):
            _, mask = min_ti_info
            self.M_out = mask
        else:
            self.M_out = (t_out < module.t_max.to(t_out.device))

    def register(self, module):
        self.handle = module.register_forward_hook(self.hook_fn)

    def remove(self):
        if self.handle is not None:
            self.handle.remove()


def spectral_norm_power_iter(J_eff: torch.Tensor, n_iters: int = 15) -> torch.Tensor:
    """Power iteration to estimate the spectral norm (largest singular value).
    
    J_eff shape: [d_out, d_in] — the effective Jacobian matrix.
    Power iteration solves for the dominant singular vector of J_eff
    by repeatedly applying J_eff^T J_eff.
    """
    d_out, d_in = J_eff.shape
    vec = torch.randn(d_in, 1, device=J_eff.device, dtype=J_eff.dtype)
    vec = vec / (torch.norm(vec) + 1e-12)
    for _ in range(n_iters):
        Jv = J_eff @ vec
        vec = J_eff.T @ Jv
        vec = vec / (torch.norm(vec) + 1e-12)
    return torch.norm(J_eff @ vec)


def gershgorin_radius(J: torch.Tensor) -> torch.Tensor:
    """Gershgorin circle theorem: max row-sum of absolute values.
    J shape: [d_out, d_in] — the Jacobian matrix."""
    row_sums = torch.abs(J).sum(dim=1)
    return row_sums.max()


def masked_effective_jacobian(W: torch.Tensor, M_in: torch.Tensor, M_out: torch.Tensor) -> torch.Tensor:
    """Return the effective Jacobian masked by both input and output masks.
    
    J_eff = diag(M_out) @ W.T @ diag(M_in)
    
    Non-active rows/columns are physically removed so the matrix is purely
    the active-to-active sub-block.
    """
    active_in = torch.where(M_in)[0]
    active_out = torch.where(M_out)[0]
    if active_in.numel() == 0 or active_out.numel() == 0:
        return torch.zeros(0, 0, device=W.device, dtype=W.dtype)
    W_sub = W[active_in][:, active_out]
    return W_sub.T


@torch.no_grad()
def measure_one_batch(model: DA_SNN, features: torch.Tensor) -> dict:
    """Forward pass with hooks; return per-layer Jacobian metrics for one batch."""
    spiking_layers = []
    for layer in model.layers_list:
        if isinstance(layer, SpikingDense) and not layer.outputLayer:
            spiking_layers.append(layer)

    hooks = {}
    for i, layer in enumerate(spiking_layers):
        hook = JacobianHook()
        hook.register(layer)
        hooks[i] = hook

    model.eval()
    _ = model(features)

    results = {}
    for i, layer in enumerate(spiking_layers):
        hook = hooks[i]
        T_in = hook.T_in
        T_out = hook.T_out
        M_out = hook.M_out
        if T_in is None or T_out is None:
            continue

        W = layer.kernel.detach()
        t_max_val = layer.t_max.item()
        span = float(t_max_val - layer.t_min.item())
        M_in = (T_in < t_max_val)

        batch_size = T_in.shape[0]
        active_in_counts, active_out_counts = [], []
        spectral_norms, gershgorin_radii = [], []

        for b in range(batch_size):
            m_in = M_in[b]
            m_out = M_out[b] if M_out is not None else (T_out[b] < t_max_val)
            act_in = m_in.sum().item()
            act_out = m_out.sum().item()
            active_in_counts.append(act_in)
            active_out_counts.append(act_out)

            J_eff = masked_effective_jacobian(W, m_in, m_out)
            if J_eff.numel() == 0:
                spectral_norms.append(0.0)
                gershgorin_radii.append(0.0)
            else:
                spectral_norms.append(spectral_norm_power_iter(J_eff, 15).item())
                gershgorin_radii.append(gershgorin_radius(J_eff).item())

        d_in = T_in.shape[-1]
        d_out = T_out.shape[-1]
        results[layer.name] = {
            "input_dim": d_in,
            "output_dim": d_out,
            "time_span": span,
            "active_in_ratio_mean": float(np.mean(active_in_counts) / d_in),
            "active_in_ratio_std": float(np.std(active_in_counts) / d_in),
            "active_out_ratio_mean": float(np.mean(active_out_counts) / d_out),
            "active_out_ratio_std": float(np.std(active_out_counts) / d_out),
            "spectral_norm_mean": float(np.mean(spectral_norms)),
            "spectral_norm_std": float(np.std(spectral_norms)),
            "gershgorin_radius_mean": float(np.mean(gershgorin_radii)),
            "gershgorin_radius_std": float(np.std(gershgorin_radii)),
        }

    for hook in hooks.values():
        hook.remove()
    return results


@torch.no_grad()
def measure_jacobian_spectrum(model: DA_SNN, val_loader: DataLoader) -> dict:
    """Aggregate Jacobian metrics across all batches in val_loader."""
    batch_results = []
    for features, _ in val_loader:
        features = features.to(next(model.parameters()).device)
        batch_results.append(measure_one_batch(model, features))

    if not batch_results:
        return {}

    keys = batch_results[0].keys()
    aggregated = {}
    for key in keys:
        layer_metrics = {}
        for mk in batch_results[0][key]:
            vals = [br[key][mk] for br in batch_results]
            layer_metrics[mk] = float(np.mean(vals))
        aggregated[key] = layer_metrics
    return aggregated


def calibrate_encoder(model: DA_SNN, train_loader: DataLoader, device: torch.device, n_batches: int = 3) -> None:
    """Run a few training-mode forward passes to initialize DF_TTFS_Encoder running stats."""
    model.train()
    with torch.no_grad():
        for i, (features, _) in enumerate(train_loader):
            if i >= n_batches:
                break
            features = features.to(device)
            _ = model(features)


def main() -> None:
    args = parse_args()
    device = torch.device(args.device)
    print(f"Device: {device}")
    print(f"Dataset: {args.dataset}, Protocol: {args.protocol}, Fixed_window: {args.fixed_window}")
    print(f"Measure at epochs: {args.measure_at}")

    set_seed(args.seeds[0])
    feature_path = resolve_feature_file(args.dataset, args.feature_file)
    bundle = load_feature_bundle(feature_path, dataset=args.dataset, require_metadata=False)

    splits = build_splits(
        args.protocol, bundle, seed=args.seeds[0],
        dataset=args.dataset, split_dir=args.split_dir,
    )
    split = splits[0]

    model = build_model(
        "da_snn", args.dataset, device,
        da_snn_options={
            "use_depthwise_separable": True,
            "use_dsgm": True,
            "use_ttfs_encoder": True,
            "use_dynamic_window": not args.fixed_window,
        },
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=5e-4, weight_decay=0.0)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(args.max_epochs, 1), eta_min=1e-6
    )

    features = bundle.features
    train_indices, val_indices = _make_train_val_indices(
        bundle.labels, split.train_indices, seed=args.seeds[0], val_size=0.1,
    )
    train_dataset = EEGTensorDataset(features, bundle.labels, train_indices)
    val_dataset = EEGTensorDataset(features, bundle.labels, val_indices)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    measure_epochs = set(args.measure_at)
    max_epoch = max(args.measure_at)
    window_label = "fixed_window" if args.fixed_window else "adaptive_window"
    output_root = Path(args.output_dir) / args.dataset / args.protocol
    output_root.mkdir(parents=True, exist_ok=True)

    measurements = {}

    for epoch in range(0, max_epoch + 1):
        if epoch in measure_epochs and epoch == 0:
            calibrate_encoder(model, train_loader, device, n_batches=3)

        if epoch in measure_epochs:
            print(f"\n=== Measuring Jacobian at epoch {epoch} ===", flush=True)
            result = measure_jacobian_spectrum(model, val_loader)
            measurements[epoch] = result
            save_path = output_root / f"jacobian_{window_label}_epoch_{epoch:03d}.json"
            with open(save_path, "w") as f:
                json.dump(result, f, indent=2, default=str)
            print(f"  Saved: {save_path}", flush=True)

        if epoch == 0:
            print(f"\n--- Training from epoch 1 to {max_epoch} ---\n", flush=True)
            continue

        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device,
            gamma_ttfs=10.0, noise_type=None, noise_level=0.0,
        )
        val_loss, val_metrics = evaluate(model, val_loader, criterion, device)
        scheduler.step()

        if epoch == 1 or epoch % 20 == 0:
            print(f"  [{epoch}/{max_epoch}] train_acc={train_acc:.4f} val_acc={val_metrics['accuracy']:.4f}", flush=True)

    summary = {
        "config": {
            "dataset": args.dataset,
            "protocol": args.protocol,
            "fixed_window": args.fixed_window,
            "seed": args.seeds[0],
            "max_epochs": args.max_epochs,
            "batch_size": args.batch_size,
            "measure_at": args.measure_at,
        },
        "window_type": window_label,
        "measurements": measurements,
    }
    summary_path = output_root / f"jacobian_summary_{window_label}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nSummary saved: {summary_path}", flush=True)


if __name__ == "__main__":
    main()
