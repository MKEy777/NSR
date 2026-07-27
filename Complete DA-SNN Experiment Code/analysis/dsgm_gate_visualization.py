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
from common.trainer import set_seed
from model.TTFS import DSGM


@torch.no_grad()
def collect_gate_activations(model, data_loader, device):
    channel_gates = []
    spatial_gates = []
    dsgm_module = None

    for module in model.modules():
        if isinstance(module, DSGM):
            dsgm_module = module
            break

    if dsgm_module is None:
        raise RuntimeError("No DSGM module found in the model.")

    model.eval()
    for features, _ in data_loader:
        features = features.to(device)
        _ = model(features)

        channel_gate = dsgm_module.channel_gate_path(
            dsgm_module.channel_gate_path[0](features)
        )
        spatial_in = torch.mean(features, dim=1, keepdim=True)
        spatial_gate = dsgm_module.spatial_gate_path(spatial_in)

        channel_gates.append(channel_gate.detach().cpu())
        spatial_gates.append(spatial_gate.detach().cpu())

    channel_all = torch.cat(channel_gates, dim=0)
    spatial_all = torch.cat(spatial_gates, dim=0)

    return {
        "channel_gate": channel_all,
        "spatial_gate": spatial_all,
    }


def plot_gate_heatmaps(gate_data, save_dir):
    save_dir = Path(save_dir)
    save_dir.mkdir(exist_ok=True)

    ch_gate = gate_data["channel_gate"]
    sp_gate = gate_data["spatial_gate"]

    ch_mean = ch_gate.mean(dim=0).squeeze().numpy()
    ch_std = ch_gate.std(dim=0).squeeze().numpy()
    sp_mean = sp_gate.mean(dim=0).squeeze().numpy()
    sp_std = sp_gate.std(dim=0).squeeze().numpy()

    fig, axes = plt.subplots(2, 2, figsize=(10, 8))

    im0 = axes[0, 0].imshow(ch_mean[np.newaxis, :], aspect="auto", cmap="viridis", vmin=0, vmax=1)
    axes[0, 0].set_title("Channel Gate Mean Activation")
    axes[0, 0].set_xlabel("Channel")
    axes[0, 0].set_yticks([])
    plt.colorbar(im0, ax=axes[0, 0])

    axes[0, 1].bar(range(len(ch_mean)), ch_mean, yerr=ch_std, capsize=2, color="steelblue")
    axes[0, 1].axhline(y=0.5, color="gray", ls="--", alpha=0.5)
    axes[0, 1].set_title("Channel Gate Mean ± Std")
    axes[0, 1].set_xlabel("Channel")
    axes[0, 1].set_ylabel("Activation")

    im2 = axes[1, 0].imshow(sp_mean, cmap="viridis", vmin=0, vmax=1)
    axes[1, 0].set_title("Spatial Gate Mean Activation")
    axes[1, 0].set_xlabel("Width")
    axes[1, 0].set_ylabel("Height")
    plt.colorbar(im2, ax=axes[1, 0])

    im3 = axes[1, 1].imshow(sp_std, cmap="plasma", vmin=0, vmax=0.5)
    axes[1, 1].set_title("Spatial Gate Std Activation")
    axes[1, 1].set_xlabel("Width")
    axes[1, 1].set_ylabel("Height")
    plt.colorbar(im3, ax=axes[1, 1])

    plt.tight_layout()
    fig.savefig(save_dir / "dsgm_gate_heatmaps.png", dpi=150, bbox_inches="tight")
    fig.savefig(save_dir / "dsgm_gate_heatmaps.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved gate heatmaps to {save_dir}")

    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 4))
    axes2[0].hist(ch_gate.flatten().numpy(), bins=50, color="steelblue", alpha=0.7, density=True)
    axes2[0].set_title("Channel Gate Value Distribution")
    axes2[0].set_xlabel("Gate value")
    axes2[0].set_ylabel("Density")

    axes2[1].hist(sp_gate.flatten().numpy(), bins=50, color="coral", alpha=0.7, density=True)
    axes2[1].set_title("Spatial Gate Value Distribution")
    axes2[1].set_xlabel("Gate value")
    axes2[1].set_ylabel("Density")

    plt.tight_layout()
    fig2.savefig(save_dir / "dsgm_gate_histograms.png", dpi=150, bbox_inches="tight")
    fig2.savefig(save_dir / "dsgm_gate_histograms.pdf", bbox_inches="tight")
    plt.close(fig2)
    print(f"Saved gate histograms to {save_dir}")


def main():
    dataset = "seed"
    seed = 42
    max_epochs = 200
    batch_size = 8
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    set_seed(seed)

    base = Path(__file__).resolve().parent.parent
    cfg = DATASET_CONFIGS[dataset]
    feature_path = base / cfg.default_feature_file
    bundle = load_feature_bundle(feature_path, dataset=dataset, require_metadata=False)

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

    train_ds = EEGTensorDataset(bundle.features, bundle.labels, train_idx)
    val_ds = EEGTensorDataset(bundle.features, bundle.labels, val_idx)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=5e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max_epochs, eta_min=1e-6)

    print(f"Training DA-SNN on {dataset.upper()} for {max_epochs} epochs ...")
    best_acc = 0.0
    stale = 0
    for epoch in range(max_epochs):
        model.train()
        correct = 0
        total = 0
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(features)
            logits = outputs[0] if isinstance(outputs, tuple) else outputs
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            correct += (logits.argmax(1) == labels).sum().item()
            total += labels.size(0)
        train_acc = correct / total

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

        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"  E{epoch+1:3d}  train={train_acc:.4f}  val={val_acc:.4f}")

        if val_acc > best_acc + 1e-4:
            best_acc = val_acc
            stale = 0
        else:
            stale += 1
            if stale >= 30:
                print(f"  Early stop at epoch {epoch+1}")
                break

    print(f"\nTraining done. Best val acc: {best_acc:.4f}")
    print("Collecting DSGM gate activations on validation set...")
    gate_data = collect_gate_activations(model, val_loader, device)

    save_dir = Path(__file__).resolve().parent / "outputs"
    save_dir.mkdir(exist_ok=True)

    ch_mean = gate_data["channel_gate"].mean(dim=0).squeeze().numpy()
    sp_mean = gate_data["spatial_gate"].mean(dim=0).squeeze().numpy()
    np.save(save_dir / "channel_gate_mean.npy", ch_mean)
    np.save(save_dir / "spatial_gate_mean.npy", sp_mean)

    plot_gate_heatmaps(gate_data, save_dir)
    print("Done. All figures and data saved to", save_dir)


if __name__ == "__main__":
    main()
