from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import train_test_split

from common.config import resolve_feature_file
from common.data_loader import EEGTensorDataset, load_feature_bundle
from common.model_builder import build_model
from experiments.jacobian_spectrum import (
    _select_analysis_indices,
    collect_square_jacobian_eigenvalues,
    train_one_epoch_instrumented,
)


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Train one DA-SNN window condition and collect square Jacobians.")
    parser.add_argument("--dataset", choices=("seed", "seediv", "seedv", "deap", "dreamer"), default="seed")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--gamma-ttfs", type=float, default=10.0)
    parser.add_argument("--jacobian-samples", type=int, default=32)
    parser.add_argument("--hidden-width", type=int, default=170)
    parser.add_argument("--hidden-depth", type=int, default=4)
    parser.add_argument("--feature-file", type=str, default=None)
    parser.add_argument("--output-dir", type=str, required=True)
    parser.add_argument("--no-dynamic-window", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    return parser.parse_args(argv)


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


def _train_model(args, bundle, train_idx, val_idx, device):
    model = build_model(
        "da_snn",
        args.dataset,
        device,
        da_snn_options={
            "use_depthwise_separable": True,
            "use_dsgm": True,
            "use_ttfs_encoder": True,
            "use_dynamic_window": not args.no_dynamic_window,
            "spiking_hidden_dims": (args.hidden_width,) * args.hidden_depth,
        },
    )
    generator = torch.Generator()
    generator.manual_seed(args.seed)
    train_ds = EEGTensorDataset(bundle.features, bundle.labels, train_idx)
    val_ds = EEGTensorDataset(bundle.features, bundle.labels, val_idx)
    train_loader = torch.utils.data.DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=0,
        generator=generator,
    )
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    return model, train_loader, val_loader


def _collect_square_eigenvalues(model, bundle, selected_indices, device):
    layer_name = None
    values = []
    for sample_index in selected_indices:
        sample = torch.as_tensor(bundle.features[int(sample_index)], dtype=torch.float32, device=device)
        current_layer_name, eigenvalues = collect_square_jacobian_eigenvalues(model, sample)
        if eigenvalues is None:
            continue
        layer_name = current_layer_name
        values.append(np.asarray(eigenvalues))
    if not values or layer_name is None:
        raise RuntimeError("No square hidden layer was found for eigenvalue collection.")
    return layer_name, np.stack(values)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    device = _resolve_device(args.device)
    bundle, train_idx, val_idx = _load_bundle_and_split(args)
    selected_indices = _select_analysis_indices(val_idx, args.jacobian_samples, args.seed)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    model, train_loader, val_loader = _train_model(args, bundle, train_idx, val_idx, device)
    criterion = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    condition = "Fixed Window" if args.no_dynamic_window else "Adaptive Window"
    for epoch in range(1, args.max_epochs + 1):
        loss, accuracy, _ = train_one_epoch_instrumented(
            model,
            train_loader,
            criterion,
            optimizer,
            device,
            args.gamma_ttfs,
            condition=condition,
            seed=args.seed,
            epoch=epoch,
            gradient_log_every=1,
        )
        if epoch == 1 or epoch == args.max_epochs or epoch % 20 == 0:
            print(f"[{condition}] epoch {epoch}/{args.max_epochs}: loss={loss:.6f}, accuracy={accuracy:.4f}", flush=True)

    layer_name, eigenvalues = _collect_square_eigenvalues(model, bundle, selected_indices, device)
    np.savez_compressed(
        out_dir / "square_jacobian_eigenvalues.npz",
        eigenvalues=eigenvalues,
        selected_validation_indices=selected_indices,
        layer_name=np.array(layer_name),
        condition=np.array(condition),
    )
    payload = {
        "condition": condition,
        "dataset": args.dataset,
        "seed": args.seed,
        "hidden_width": args.hidden_width,
        "hidden_depth": args.hidden_depth,
        "jacobian_samples": int(args.jacobian_samples),
        "layer_name": layer_name,
        "sample_count": int(eigenvalues.shape[0]),
        "values_per_sample": int(eigenvalues.shape[1]),
        "max_modulus": float(np.max(np.abs(eigenvalues))),
        "median_modulus": float(np.median(np.abs(eigenvalues))),
    }
    (out_dir / "square_jacobian_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "run_manifest.json").write_text(json.dumps({"status": "completed", "condition": condition, "arguments": vars(args), "artifacts": ["square_jacobian_eigenvalues.npz", "square_jacobian_summary.json"]}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved square Jacobian spectra to {out_dir}")


if __name__ == "__main__":
    main()
