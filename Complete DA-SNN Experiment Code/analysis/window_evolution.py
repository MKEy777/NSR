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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import DATASET_CONFIGS
from common.data_loader import load_feature_bundle, EEGTensorDataset
from common.model_builder import build_model
from common.trainer import set_seed, _update_time_windows
from common.noise_injector import inject_noise
from model.TTFS import SpikingDense, DF_TTFS_Encoder


def train_and_record(
    dataset="seed",
    seed=42,
    max_epochs=200,
    batch_size=8,
    learning_rate=5e-4,
    patience=30,
    min_delta=1e-4,
    gamma_ttfs=10.0,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(seed)

    base = Path(__file__).resolve().parent.parent
    cfg = DATASET_CONFIGS[dataset]
    feature_path = base / cfg.default_feature_file
    bundle = load_feature_bundle(feature_path, dataset=dataset, require_metadata=False)

    model = build_model(
        "da_snn",
        dataset,
        device,
        da_snn_options={
            "use_depthwise_separable": True,
            "use_dsgm": True,
            "use_ttfs_encoder": True,
            "use_dynamic_window": True,
        },
    )

    indices = np.arange(bundle.labels.shape[0])
    train_idx, test_idx = train_test_split(
        indices, test_size=0.2, random_state=seed, shuffle=True, stratify=bundle.labels
    )
    train_idx, val_idx = train_test_split(
        train_idx,
        test_size=0.1 / 0.8,
        random_state=seed,
        shuffle=True,
        stratify=bundle.labels[train_idx],
    )

    train_ds = EEGTensorDataset(bundle.features, bundle.labels, train_idx)
    val_ds = EEGTensorDataset(bundle.features, bundle.labels, val_idx)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-6)

    spike_hidden = [
        layer
        for layer in model.layers_list
        if isinstance(layer, SpikingDense) and not layer.outputLayer
    ]
    encoder = next(
        (layer for layer in model.layers_list if isinstance(layer, DF_TTFS_Encoder)),
        None,
    )

    window_history = []
    best_acc = 0.0
    stale = 0

    print(f"Recording {len(spike_hidden)} hidden SpikingDense layers")
    print(f"Device: {device}  |  gamma_ttfs={gamma_ttfs}  |  Max epochs: {max_epochs}")

    for epoch in range(max_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            features = inject_noise(features, "none", 0.0)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(features)
            logits = outputs[0] if isinstance(outputs, tuple) else outputs
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            if isinstance(outputs, tuple):
                _update_time_windows(model, outputs[1], gamma_ttfs)

            running_loss += loss.item() * labels.size(0)
            correct += (logits.argmax(1) == labels).sum().item()
            total += labels.size(0)
        train_acc = correct / total

        rec = {"epoch": epoch + 1}
        for lay in spike_hidden:
            rec[f"{lay.name}_t_min"] = float(lay.t_min.cpu())
            rec[f"{lay.name}_t_max"] = float(lay.t_max.cpu())
        if encoder is not None:
            rec["encoder_t_max"] = float(encoder.t_max)
        window_history.append(rec)

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                logits = model(features)
                if isinstance(logits, tuple):
                    logits = logits[0]
                val_correct += (logits.argmax(1) == labels).sum().item()
                val_total += labels.size(0)
        val_acc = val_correct / val_total

        scheduler.step()

        if (epoch + 1) % 10 == 0 or epoch == 0:
            d1 = f"[{rec.get('dense_1_t_min', 0):.2f},{rec.get('dense_1_t_max', 0):.2f}]"
            d2 = f"[{rec.get('dense_2_t_min', 0):.2f},{rec.get('dense_2_t_max', 0):.2f}]"
            print(f"  E{epoch+1:3d}  acc={train_acc:.4f}/{val_acc:.4f}  d1={d1}  d2={d2}")

        if val_acc > best_acc + min_delta:
            best_acc = val_acc
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                print(f"  Early stop at epoch {epoch+1}")
                break

    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    for lay in spike_hidden:
        arr = np.array(
            [(r[f"{lay.name}_t_min"], r[f"{lay.name}_t_max"]) for r in window_history]
        )
        np.save(out_dir / f"{lay.name}_window.npy", arr)

    np.save(out_dir / "window_history.npy", np.array(window_history, dtype=object))
    print(f"Saved {len(window_history)} epoch records to {out_dir}")
    return window_history, spike_hidden


def plot_window_evolution(window_history, spike_hidden, save_dir=None):
    if save_dir is None:
        save_dir = Path(__file__).resolve().parent / "outputs"
    else:
        save_dir = Path(save_dir)
    save_dir.mkdir(exist_ok=True)

    epochs = np.array([r["epoch"] for r in window_history])
    n_layers = len(spike_hidden)

    fig, axes = plt.subplots(
        1, n_layers, figsize=(6 * n_layers + 1, 4.5), squeeze=False
    )
    axes = axes[0]
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, n_layers))

    for idx, layer in enumerate(spike_hidden):
        ax = axes[idx]
        name = layer.name
        t_min = np.array([r[f"{name}_t_min"] for r in window_history])
        t_max = np.array([r[f"{name}_t_max"] for r in window_history])

        ax.fill_between(epochs, t_min, t_max, alpha=0.25, color=colors[idx])
        ax.plot(epochs, t_min, "--", color=colors[idx], lw=1, label=r"$T_{\min}$")
        ax.plot(epochs, t_max, "-", color=colors[idx], lw=1.5, label=r"$T_{\max}$")

        width = t_max - t_min
        ax_twin = ax.twinx()
        ax_twin.plot(epochs, width, ":", color="crimson", lw=1, alpha=0.7, label="Width")
        ax_twin.set_ylabel("Window width", fontsize=10)
        ax_twin.tick_params(axis="y", labelsize=8)

        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel("Time", fontsize=11)
        ax.set_title(f"{name}", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)
        ax.tick_params(labelsize=9)
        ax.set_xlim(1, int(epochs[-1]))

        if "encoder_t_max" in window_history[0]:
            enc = window_history[0]["encoder_t_max"]
            ax.axhline(y=enc, color="gray", ls="--", alpha=0.35, lw=0.8)

    fig.suptitle(
        "Adaptive Time Window Evolution During Training (SEED)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    fig.savefig(save_dir / "window_evolution.png", dpi=150, bbox_inches="tight")
    fig.savefig(save_dir / "window_evolution.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figures to {save_dir}")


if __name__ == "__main__":
    history, layers = train_and_record()
    plot_window_evolution(history, layers)
