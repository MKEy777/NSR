"""
Jacobian Spectrum Analysis for DA-SNN
======================================
Computes layer-wise spike-time Jacobian J^(n) = dT^(n)/dT^(n-1) for each
SpikingDense layer and compares eigenvalue magnitude distributions between
fixed time-window and adaptive time-window conditions at three training stages:
  1. Random initialization
  2. Early training (a few epochs)
  3. Converged model (after full training)

Usage:
    python experiments/jacobian_spectrum.py [--dataset seed] [--protocol random_80_20]
        [--seed 42] [--output-dir experiment_outputs/jacobian_spectrum]
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import DATASET_CONFIGS, resolve_feature_file
from common.data_loader import load_feature_bundle, EEGTensorDataset
from common.model_builder import build_model
from common.trainer import set_seed, train_one_epoch, evaluate, _update_time_windows
from common.noise_injector import inject_noise
from model.TTFS import DA_SNN, SpikingDense, DF_TTFS_Encoder


# ---------------------------------------------------------------------------
# Jacobian computation
# ---------------------------------------------------------------------------

def _collect_spike_times_per_layer(model, x):
    """Forward pass and collect spike-time tensors for each hidden SpikingDense layer.

    Returns a list of (spike_output, spike_mask) for each hidden SpikingDense layer.
    spike_output: tensor of shape (batch, units) with spike times, requires_grad=True
    spike_mask:   boolean tensor of shape (batch, units) indicating active neurons
    """
    layer_spike_info = []
    current_input = x

    for layer in model.layers_list:
        if isinstance(layer, SpikingDense):
            if not layer.built:
                layer.build(current_input.shape)
            if layer.outputLayer:
                break  # skip output layer
            # Recompute forward for this layer with grad tracking
            current_input_det = current_input.detach().requires_grad_(True)
            tj = current_input_det
            threshold = layer.t_max - layer.t_min - layer.D_i
            output = torch.matmul(tj - layer.t_min, layer.kernel) + threshold + layer.t_min
            output = torch.where(torch.isfinite(output), output, layer.t_max)
            output = torch.where(output < layer.t_max, output, layer.t_max)

            with torch.no_grad():
                mask = torch.isfinite(output) & (output < layer.t_max)

            layer_spike_info.append((output, mask, current_input_det))
            # For next layer, use detached output
            current_input = output.detach()
        elif isinstance(layer, DF_TTFS_Encoder):
            current_input, _ = layer(current_input)
        elif hasattr(layer, 'outputLayer'):
            current_input, _ = layer(current_input)
        else:
            current_input = layer(current_input)

    return layer_spike_info


def compute_layer_jacobian(model, x, layer_idx, layer_spike_info):
    """Compute the Jacobian J^(n) = dT^(n)/dT^(n-1) for a specific hidden layer.

    Returns eigenvalues of the Jacobian matrix (averaged over batch dimension
    for active neurons only).
    """
    output, mask, input_tensor = layer_spike_info[layer_idx]
    batch_size, n_units = output.shape

    # Only consider active neurons
    active_mask = mask.bool()  # (batch, units)

    if active_mask.sum().item() == 0:
        return np.array([])

    # We compute the Jacobian column-by-column using autograd
    # J[i,j] = d output_i / d input_j  for active neurons
    # Average over batch to get a (n_units x n_input_dim) matrix
    # But we want square matrix: dT^(n)_i / dT^(n-1)_i — same-layer mapping
    # Actually the Jacobian is (n_units_out x n_units_in) where n_units_in = input dim
    # For eigenvalue analysis, we need square matrix, so we use the effective
    # Jacobian restricted to active neurons.

    # Compute full Jacobian for active neurons
    jacobian_rows = []
    n_input = input_tensor.shape[-1]

    # Sample a subset of active neurons to compute Jacobian for efficiency
    active_indices = torch.nonzero(active_mask)  # (n_active, 2) -> (batch_idx, unit_idx)
    n_active = active_indices.shape[0]

    # Limit to manageable number
    max_active = min(n_active, 64)
    if max_active == 0:
        return np.array([])

    # Pick random active neurons
    perm = torch.randperm(n_active)[:max_active]
    selected = active_indices[perm]

    # For each selected active neuron, compute gradient of its spike time
    # w.r.t. the input spike times
    jac_accum = torch.zeros(max_active, n_input, device=output.device)

    for i in range(max_active):
        b_idx, u_idx = selected[i]
        grad_outputs = torch.zeros_like(output)
        grad_outputs[b_idx, u_idx] = 1.0
        grad = torch.autograd.grad(
            output, input_tensor,
            grad_outputs=grad_outputs,
            retain_graph=(i < max_active - 1),
            allow_unused=True,
        )[0]
        if grad is not None:
            jac_accum[i] = grad[b_idx].detach()

    # jac_accum is (max_active, n_input)
    # To get a square matrix for eigenvalue analysis, we project onto the
    # input dimensions that correspond to the same layer's output neurons.
    # If n_input == n_units, the Jacobian is already square.
    # Otherwise, we compute J^T J or take the relevant sub-block.

    n_out = n_units
    if jac_accum.shape[1] == n_out:
        # Square Jacobian — average over selected neurons to get representative matrix
        J = jac_accum.numpy()
    elif jac_accum.shape[1] > n_out:
        # Input dim > output dim: take the first n_out columns corresponding to
        # the same neuron indices (diagonal-dominant approximation)
        J = jac_accum[:, :n_out].numpy()
    else:
        # Input dim < output dim: pad
        J = np.zeros((max_active, n_out))
        J[:, :jac_accum.shape[1]] = jac_accum.numpy()

    # Average row to get representative Jacobian row pattern
    # For eigenvalue spectrum, compute SVD-based singular values as proxy
    # since J may not be square
    if J.shape[0] > 0:
        # Compute the effective square Jacobian by averaging
        J_mean = J.mean(axis=0, keepdims=True)  # (1, n_out)
        # Build square matrix: use J^T @ J / n_samples approximation
        J_sq = J.T @ J / J.shape[0]  # (n_out, n_out)
        eigenvalues = np.linalg.eigvals(J_sq)
    else:
        eigenvalues = np.array([])

    return eigenvalues


def compute_all_layer_jacobians(model, x):
    """Compute Jacobian eigenvalues for all hidden SpikingDense layers."""
    layer_spike_info = _collect_spike_times_per_layer(model, x)
    all_eigenvalues = []
    for idx in range(len(layer_spike_info)):
        eigs = compute_layer_jacobian(model, x, idx, layer_spike_info)
        all_eigenvalues.append(eigs)
    return all_eigenvalues


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------

def _build_model_and_data(args, use_dynamic_window, seed):
    """Build model and data loaders for a given dynamic-window setting."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(seed)

    base = Path(__file__).resolve().parent.parent
    feature_path = resolve_feature_file(args.dataset, args.feature_file)
    if not feature_path.is_absolute():
        feature_path = base / feature_path

    bundle = load_feature_bundle(feature_path, dataset=args.dataset, require_metadata=False)

    model = build_model(
        "da_snn", args.dataset, device,
        da_snn_options={
            "use_depthwise_separable": True,
            "use_dsgm": True,
            "use_ttfs_encoder": True,
            "use_dynamic_window": use_dynamic_window,
        },
    )

    indices = np.arange(bundle.labels.shape[0])
    train_idx, test_idx = train_test_split(
        indices, test_size=0.2, random_state=seed, shuffle=True,
        stratify=bundle.labels,
    )
    train_idx, val_idx = train_test_split(
        train_idx, test_size=0.1 / 0.8, random_state=seed, shuffle=True,
        stratify=bundle.labels[train_idx],
    )

    train_ds = EEGTensorDataset(bundle.features, bundle.labels, train_idx)
    val_ds = EEGTensorDataset(bundle.features, bundle.labels, val_idx)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False)

    return model, train_loader, val_loader, device


def _train_model(model, train_loader, val_loader, device, n_epochs, lr=5e-4, gamma_ttfs=10.0):
    """Train for n_epochs and return the model."""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    for epoch in range(n_epochs):
        train_one_epoch(model, train_loader, criterion, optimizer, device, gamma_ttfs)
    return model


def _get_sample_batch(train_loader, device):
    """Get one batch from the training loader."""
    for features, labels in train_loader:
        return features.to(device)
    raise RuntimeError("Empty train loader")


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_jacobian_experiment(args):
    """Run the Jacobian spectrum comparison experiment."""
    seed = args.seed
    base_out = Path(args.output_dir)
    base_out.mkdir(parents=True, exist_ok=True)

    stages = [
        ("Random Init", 0),       # 0 epochs = random initialization
        ("Early Training", 5),    # 5 epochs
        ("Converged", args.max_epochs),  # full training
    ]

    conditions = {
        "Fixed Window": False,    # use_dynamic_window=False
        "Adaptive Window": True,  # use_dynamic_window=True
    }

    # results: {stage_name: {condition_name: [eigenvalues_per_layer]}}
    results = {}

    for stage_name, n_epochs in stages:
        print(f"\n{'='*60}")
        print(f"Stage: {stage_name} ({n_epochs} epochs)")
        print(f"{'='*60}")
        results[stage_name] = {}

        for cond_name, use_dw in conditions.items():
            print(f"  Condition: {cond_name}")
            model, train_loader, val_loader, device = _build_model_and_data(args, use_dw, seed)

            if n_epochs > 0:
                model = _train_model(model, train_loader, val_loader, device, n_epochs, lr=args.lr)

            model.eval()
            sample = _get_sample_batch(train_loader, device)

            # Compute Jacobian eigenvalues for multiple batches for robustness
            all_eigs_per_layer = None
            n_batches = min(5, len(train_loader))
            batch_count = 0
            for features, _ in train_loader:
                if batch_count >= n_batches:
                    break
                features = features.to(device)
                eigs_list = compute_all_layer_jacobians(model, features)
                if all_eigs_per_layer is None:
                    all_eigs_per_layer = [[] for _ in eigs_list]
                for i, eigs in enumerate(eigs_list):
                    if len(eigs) > 0:
                        all_eigs_per_layer[i].append(np.abs(eigs))
                batch_count += 1

            # Aggregate eigenvalues across batches
            aggregated = []
            if all_eigs_per_layer is not None:
                for layer_eigs_list in all_eigs_per_layer:
                    if layer_eigs_list:
                        aggregated.append(np.concatenate(layer_eigs_list))
                    else:
                        aggregated.append(np.array([]))

            results[stage_name][cond_name] = aggregated
            n_layers = len(aggregated)
            for li in range(n_layers):
                n_eigs = len(aggregated[li])
                mean_mag = np.mean(aggregated[li]) if n_eigs > 0 else 0.0
                print(f"    Layer {li}: {n_eigs} eigenvalues, mean |λ|={mean_mag:.4f}")

    # Save raw results
    np.savez(
        base_out / "jacobian_results.npz",
        results={sn: {cn: vals for cn, vals in cv.items()} for sn, cv in results.items()},
    )
    # Also save as individual numpy files for easier post-processing
    for stage_name in results:
        for cond_name in results[stage_name]:
            eigs_list = results[stage_name][cond_name]
            safe_name = f"{stage_name.replace(' ', '_')}_{cond_name.replace(' ', '_')}"
            np.save(base_out / f"eigs_{safe_name}.npy", np.array(eigs_list, dtype=object))

    return results


def plot_jacobian_spectrum(results, save_dir):
    """Plot eigenvalue magnitude distribution as KDE, comparing fixed vs adaptive."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    stages = list(results.keys())
    n_stages = len(stages)
    conditions = ["Fixed Window", "Adaptive Window"]
    colors = {"Fixed Window": "#2196F3", "Adaptive Window": "#FF5722"}

    # Determine max number of layers across all stages/conditions
    max_layers = 0
    for stage in stages:
        for cond in conditions:
            max_layers = max(max_layers, len(results[stage][cond]))

    fig, axes = plt.subplots(
        n_stages, max_layers,
        figsize=(5 * max_layers, 4 * n_stages),
        squeeze=False,
    )

    for si, stage_name in enumerate(stages):
        for li in range(max_layers):
            ax = axes[si, li]
            for cond_name in conditions:
                eigs_list = results[stage_name][cond_name]
                if li >= len(eigs_list) or len(eigs_list[li]) == 0:
                    continue
                magnitudes = np.abs(eigs_list[li])
                # Remove zeros and very small values for log-scale KDE
                magnitudes = magnitudes[magnitudes > 1e-10]
                if len(magnitudes) < 3:
                    continue

                # KDE plot
                if np.std(magnitudes) > 1e-10:
                    kde = gaussian_kde(magnitudes, bw_method="silverman")
                    x_range = np.linspace(
                        max(magnitudes.min() * 0.5, 1e-8),
                        magnitudes.max() * 1.5,
                        200,
                    )
                    ax.plot(x_range, kde(x_range), lw=1.8, label=cond_name,
                            color=colors[cond_name], alpha=0.85)
                    ax.fill_between(x_range, kde(x_range), alpha=0.15, color=colors[cond_name])
                else:
                    ax.axvline(magnitudes.mean(), color=colors[cond_name], lw=2,
                               label=f"{cond_name} (mean={magnitudes.mean():.3f})")

            ax.set_xlabel("|λ|", fontsize=10)
            ax.set_ylabel("Density", fontsize=10)
            layer_title = f"Layer {li+1}" if li < max_layers else ""
            ax.set_title(layer_title, fontsize=11, fontweight="bold")
            ax.legend(fontsize=8, loc="upper right")
            ax.set_xscale("log")
            ax.tick_params(labelsize=8)

        # Stage label on the left
        axes[si, 0].set_ylabel(f"{stages[si]}\n\nDensity", fontsize=10)

    fig.suptitle(
        "Jacobian Eigenvalue Magnitude Spectrum: Fixed vs Adaptive Time Window",
        fontsize=14, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    fig.savefig(save_dir / "jacobian_spectrum_comparison.png", dpi=300, bbox_inches="tight")
    fig.savefig(save_dir / "jacobian_spectrum_comparison.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved Jacobian spectrum plot to {save_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Jacobian spectrum analysis for DA-SNN: compare fixed vs adaptive time windows",
    )
    parser.add_argument("--dataset", type=str, default="seed", choices=["seed", "seediv", "seedv", "deap", "dreamer"])
    parser.add_argument("--protocol", type=str, default="random_80_20")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--max-epochs", type=int, default=200, help="Number of epochs for 'Converged' stage")
    parser.add_argument("--feature-file", type=str, default=None, help="Override feature .mat path")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: experiment_outputs/jacobian_spectrum)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.output_dir is None:
        base = Path(__file__).resolve().parent.parent
        args.output_dir = str(base / "experiment_outputs" / "jacobian_spectrum")

    print(f"Jacobian Spectrum Analysis")
    print(f"  Dataset:    {args.dataset}")
    print(f"  Protocol:   {args.protocol}")
    print(f"  Seed:       {args.seed}")
    print(f"  Output:     {args.output_dir}")
    print(f"  Max epochs: {args.max_epochs}")

    results = run_jacobian_experiment(args)
    plot_jacobian_spectrum(results, args.output_dir)
    print("Done.")
