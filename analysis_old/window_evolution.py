import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from scipy.io import loadmat

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DA_SNN_DIR = Path(__file__).resolve().parent.parent / "DA-SNN"
sys.path.insert(0, str(DA_SNN_DIR))

from model.TTFS import DA_SNN, DF_TTFS_Encoder, SpikingDense, build_da_snn


class NumpyDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.as_tensor(features, dtype=torch.float32)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


def train_and_record(
    seed=42,
    max_epochs=200,
    batch_size=8,
    gamma_ttfs=10.0,
    learning_rate=5e-4,
    patience=30,
    min_delta=1e-4,
):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    torch.manual_seed(seed)
    np.random.seed(seed)

    base = Path(__file__).resolve().parent.parent
    mat_path = (
        base
        / "Complete DA-SNN Experiment Code"
        / "Preprocessing"
        / "SEED"
        / "Feature_PowerSpectrumEntropy_LDS_Smoothed_SEED"
        / "all_features_lds_smoothed.mat"
    )
    mat = loadmat(str(mat_path))
    features = np.asarray(mat["features"], dtype=np.float32)
    raw_labels = np.asarray(mat["labels"]).reshape(-1)
    mapping = {-1: 0, 0: 1, 1: 2}
    labels = np.array([mapping[int(v)] for v in raw_labels], dtype=np.int64)

    model = build_da_snn(
        input_shape=(4, 8, 9),
        conv_channels=[8, 8],
        conv_kernel_size=3,
        hidden_units_1=64,
        hidden_units_2=32,
        output_size=3,
        t_min=0.0,
        t_max=1.0,
        dropout_rate=0.0,
    )

    def custom_weight_init(m):
        if isinstance(m, SpikingDense) and m.kernel is not None:
            input_dim = m.kernel.shape[0]
            if input_dim > 0:
                m.kernel.data.normal_(mean=0.0, std=1.0 / (input_dim ** 0.5))
        elif isinstance(m, nn.Conv2d):
            nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)

    model.apply(custom_weight_init)
    model.to(device)

    indices = np.arange(features.shape[0])
    train_idx, test_idx = train_test_split(
        indices, test_size=0.2, random_state=seed, shuffle=True, stratify=labels
    )
    train_idx, val_idx = train_test_split(
        train_idx,
        test_size=0.1 / 0.8,
        random_state=seed,
        shuffle=True,
        stratify=labels[train_idx],
    )

    train_ds = NumpyDataset(features, labels)
    train_sampler = torch.utils.data.SubsetRandomSampler(train_idx)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, sampler=train_sampler, drop_last=True
    )
    val_loader = DataLoader(
        NumpyDataset(features[train_idx], labels[train_idx]), batch_size=batch_size, shuffle=False
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max_epochs, eta_min=1e-6
    )

    snn_hidden = [
        layer
        for layer in model.layers_list
        if isinstance(layer, SpikingDense) and not layer.outputLayer
    ]

    window_history = []
    best_acc = 0.0
    stale = 0
    next_time_params = []

    print(f"Device: {device}  |  Gamma: {gamma_ttfs}  |  Epochs: {max_epochs}")
    print(f"Hidden SpikingDense layers: {[l.name for l in snn_hidden]}")

    for epoch in range(max_epochs):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for features_batch, labels_batch in train_loader:
            if next_time_params:
                for lay, tmin_prev, tmin, tmax in next_time_params:
                    lay.set_time_params(
                        torch.as_tensor(tmin_prev, device=device),
                        torch.as_tensor(tmin, device=device),
                        torch.as_tensor(tmax, device=device),
                    )
                next_time_params.clear()

            features_batch = features_batch.to(device, non_blocking=True)
            labels_batch = labels_batch.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)
            outputs, min_ti_list = model(features_batch)
            loss = criterion(outputs, labels_batch)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * labels_batch.size(0)
            _, predicted = outputs.max(1)
            total += labels_batch.size(0)
            correct += predicted.eq(labels_batch).sum().item()

            with torch.no_grad():
                t_min_input = 0.0
                t_max_input = 1.0
                next_time_params = []
                prev_boundary = t_max_input
                prev_prev_boundary = t_min_input

                for lay, min_ti in zip(snn_hidden, min_ti_list):
                    if min_ti is None:
                        continue

                    curr_t_min = float(lay.t_min)
                    curr_t_max = float(lay.t_max)
                    new_t_max = curr_t_max

                    if min_ti.numel() > 0:
                        t_e = float(torch.min(min_ti))
                        if t_e < curr_t_max:
                            midpoint = (curr_t_max + curr_t_min) / 2.0
                            new_t_max = curr_t_max + gamma_ttfs * (t_e - midpoint)
                            new_t_max = max(new_t_max, curr_t_min + 1e-4)

                    next_time_params.append(
                        (lay, prev_prev_boundary, prev_boundary, new_t_max)
                    )
                    prev_prev_boundary = prev_boundary
                    prev_boundary = new_t_max

        train_acc = correct / total

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for features_batch, labels_batch in val_loader:
                features_batch = features_batch.to(device)
                labels_batch = labels_batch.to(device)
                outputs, _ = model(features_batch)
                _, predicted = outputs.max(1)
                val_total += labels_batch.size(0)
                val_correct += predicted.eq(labels_batch).sum().item()
        val_acc = val_correct / val_total

        scheduler.step()

        rec = {"epoch": epoch + 1}
        for lay in snn_hidden:
            rec[f"{lay.name}_t_min"] = float(lay.t_min.cpu())
            rec[f"{lay.name}_t_max"] = float(lay.t_max.cpu())
        for lay in model.layers_list:
            if isinstance(lay, DF_TTFS_Encoder):
                rec["encoder_t_max"] = float(lay.t_max)
                break
        window_history.append(rec)

        if (epoch + 1) % 10 == 0 or epoch == 0:
            parts = [f"E{epoch+1:3d}  acc={train_acc:.4f}/{val_acc:.4f}"]
            for lay in snn_hidden:
                parts.append(
                    f"  {lay.name}=[{rec[f'{lay.name}_t_min']:.2f},{rec[f'{lay.name}_t_max']:.2f}]"
                )
            print("".join(parts))

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
    np.save(out_dir / "window_history_old.npy", np.array(window_history, dtype=object))
    for lay in snn_hidden:
        arr = np.array(
            [(r[f"{lay.name}_t_min"], r[f"{lay.name}_t_max"]) for r in window_history]
        )
        np.save(out_dir / f"{lay.name}_window_old.npy", arr)

    print(f"Saved {len(window_history)} records to {out_dir}")
    return window_history, snn_hidden


def plot_window_evolution(window_history, snn_hidden, save_dir=None):
    if save_dir is None:
        save_dir = Path(__file__).resolve().parent / "outputs"
    else:
        save_dir = Path(save_dir)
    save_dir.mkdir(exist_ok=True)

    epochs = np.array([r["epoch"] for r in window_history])
    n_layers = len(snn_hidden)

    fig, axes = plt.subplots(
        1, n_layers, figsize=(6 * n_layers + 1, 4.5), squeeze=False
    )
    axes = axes[0]
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, n_layers))

    for idx, layer in enumerate(snn_hidden):
        ax = axes[idx]
        name = layer.name
        t_min = np.array([r[f"{name}_t_min"] for r in window_history])
        t_max = np.array([r[f"{name}_t_max"] for r in window_history])

        ax.fill_between(epochs, t_min, t_max, alpha=0.25, color=colors[idx])
        ax.plot(epochs, t_min, "--", color=colors[idx], lw=1, label=r"$T_{\min}$")
        ax.plot(epochs, t_max, "-", color=colors[idx], lw=1.5, label=r"$T_{\max}$")

        width = t_max - t_min
        ax_twin = ax.twinx()
        ax_twin.plot(
            epochs, width, ":", color="crimson", lw=1, alpha=0.7, label="Width"
        )
        ax_twin.set_ylabel("Window width", fontsize=10)
        ax_twin.tick_params(axis="y", labelsize=8)

        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel("Time", fontsize=11)
        ax.set_title(f"{name}", fontsize=12, fontweight="bold")
        ax.legend(loc="upper left", fontsize=8)
        ax.tick_params(labelsize=9)
        ax.set_xlim(1, int(epochs[-1]))

        if "encoder_t_max" in window_history[0]:
            ax.axhline(
                y=window_history[0]["encoder_t_max"],
                color="gray",
                ls="--",
                alpha=0.35,
                lw=0.8,
            )

    fig.suptitle(
        "Adaptive Time Window Evolution (old DA-SNN logic)",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )
    plt.tight_layout()
    fig.savefig(save_dir / "window_evolution_old.png", dpi=150, bbox_inches="tight")
    fig.savefig(save_dir / "window_evolution_old.pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved figures to {save_dir}")


if __name__ == "__main__":
    history, layers = train_and_record()
    plot_window_evolution(history, layers)
