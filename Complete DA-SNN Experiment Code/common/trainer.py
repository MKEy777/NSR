from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader
from sklearn.model_selection import train_test_split

from common.config import DATASET_CONFIGS
from common.data_loader import DatasetBundle, EEGTensorDataset, Split
from common.metrics import compute_metrics, summarize_runs, write_csv, write_json
from common.model_builder import build_model
from common.noise_injector import StandardMinMaxEncoder, inject_noise
from model.TTFS import SpikingDense


@dataclass(frozen=True)
class ExperimentConfig:
    dataset: str
    model_name: str
    protocol: str
    seed: int
    output_dir: Path
    max_epochs: int = 200
    max_splits: int | None = None
    batch_size: int = 8
    learning_rate: float = 5e-4
    weight_decay: float = 0.0
    patience: int = 30
    min_delta: float = 1e-4
    gamma_ttfs: float = 10.0
    val_size: float = 0.1
    standard_minmax: bool = False
    noise_type: str | None = None
    noise_level: float = 0.0
    use_depthwise_separable: bool = True
    use_dsgm: bool = True
    use_ttfs_encoder: bool = True
    use_dynamic_window: bool = True
    dry_run: bool = False


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _forward_logits(model: nn.Module, features: torch.Tensor):
    outputs = model(features)
    return outputs[0] if isinstance(outputs, tuple) else outputs


def _update_time_windows(model: nn.Module, min_ti_list, gamma_ttfs: float) -> None:
    if not hasattr(model, "layers_list"):
        return
    snn_layers = [layer for layer in model.layers_list if isinstance(layer, SpikingDense) and not layer.outputLayer]
    t_min_prev = 0.0
    current_t_min = 1.0
    for layer, min_ti in zip(snn_layers, min_ti_list):
        if min_ti is None:
            layer.set_time_params(t_min_prev, current_t_min, current_t_min + 1.0)
            t_min_prev = current_t_min
            current_t_min = current_t_min + 1.0
            continue
        layer_t_max_val = float(layer.t_max)
        if isinstance(min_ti, tuple):
            spike_times, spike_mask = min_ti
            finite_min_ti = spike_times.detach().cpu()
            valid_mask = spike_mask.detach().cpu().bool() & torch.isfinite(finite_min_ti)
            positive_spikes = finite_min_ti[valid_mask & (finite_min_ti < layer_t_max_val)]
        else:
            finite_min_ti = min_ti.detach().cpu()
            positive_spikes = finite_min_ti[torch.isfinite(finite_min_ti) & (finite_min_ti < layer_t_max_val)]
        base_interval = 1.0
        new_t_max = current_t_min + base_interval
        if positive_spikes.numel() > 0:
            earliest_spike = float(torch.min(positive_spikes))
            if layer_t_max_val > earliest_spike:
                dynamic_term = gamma_ttfs * (layer_t_max_val - earliest_spike)
                new_t_max = min(current_t_min + max(base_interval, dynamic_term), current_t_min + 100.0)
        layer.set_time_params(t_min_prev, current_t_min, new_t_max)
        t_min_prev = current_t_min
        current_t_min = new_t_max


def train_one_epoch(
    model,
    loader,
    criterion,
    optimizer,
    device,
    gamma_ttfs: float,
    noise_type: str | None = None,
    noise_level: float = 0.0,
) -> tuple[float, float]:
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    for batch_idx, (features, labels) in enumerate(loader):
        features = features.to(device)
        labels = labels.to(device)
        features = inject_noise(features, noise_type, noise_level)
        optimizer.zero_grad(set_to_none=True)
        outputs = model(features)
        logits = outputs[0] if isinstance(outputs, tuple) else outputs
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        if isinstance(outputs, tuple):
            _update_time_windows(model, outputs[1], gamma_ttfs)
        running_loss += loss.item() * labels.size(0)
        correct += (logits.argmax(dim=1) == labels).sum().item()
        total += labels.size(0)
    return running_loss / max(total, 1), correct / max(total, 1)


def _make_train_val_indices(
    labels: np.ndarray,
    train_indices: np.ndarray,
    *,
    seed: int,
    val_size: float,
) -> tuple[np.ndarray, np.ndarray]:
    train_indices = np.asarray(train_indices, dtype=np.int64)
    if train_indices.size < 2:
        return train_indices, train_indices
    y = labels[train_indices]
    val_count = max(1, int(round(train_indices.size * val_size)))
    if train_indices.size - val_count < 1:
        val_count = train_indices.size - 1
    stratify = None
    if len(np.unique(y)) > 1:
        counts = np.bincount(y - y.min())
        if counts.min() >= 2 and val_count >= len(np.unique(y)):
            stratify = y
    train_part, val_part = train_test_split(
        train_indices,
        test_size=val_count,
        random_state=seed,
        shuffle=True,
        stratify=stratify,
    )
    return np.asarray(train_part, dtype=np.int64), np.asarray(val_part, dtype=np.int64)


def evaluate(model, loader, criterion, device, noise_type: str | None = None, noise_level: float = 0.0) -> tuple[float, dict[str, float]]:
    model.eval()
    cfg_num_classes = None
    all_labels = []
    all_preds = []
    running_loss = 0.0
    total = 0
    with torch.no_grad():
        for features, labels in loader:
            features = features.to(device)
            labels = labels.to(device)
            features = inject_noise(features, noise_type, noise_level)
            logits = _forward_logits(model, features)
            loss = criterion(logits, labels)
            running_loss += loss.item() * labels.size(0)
            total += labels.size(0)
            all_labels.extend(labels.cpu().numpy().tolist())
            all_preds.extend(logits.argmax(dim=1).cpu().numpy().tolist())
            cfg_num_classes = logits.shape[1]
    metrics = compute_metrics(np.array(all_labels), np.array(all_preds), int(cfg_num_classes or 1))
    return running_loss / max(total, 1), metrics


def _subjects_for_indices(bundle: DatasetBundle, indices: np.ndarray) -> list[int]:
    if bundle.subject_id is None:
        return []
    subjects = np.unique(bundle.subject_id[np.asarray(indices, dtype=np.int64)])
    return [int(subject) for subject in subjects.tolist()]


def run_single_split(bundle: DatasetBundle, split: Split, config: ExperimentConfig, device: torch.device) -> dict[str, float]:
    if split.val_indices is None:
        train_indices, val_indices = _make_train_val_indices(
            bundle.labels,
            split.train_indices,
            seed=config.seed,
            val_size=config.val_size,
        )
    else:
        train_indices = split.train_indices
        val_indices = split.val_indices
    features = bundle.features
    if config.standard_minmax:
        encoder = StandardMinMaxEncoder().fit(features[train_indices])
        features = encoder.transform(features)
    train_dataset = EEGTensorDataset(features, bundle.labels, train_indices)
    val_dataset = EEGTensorDataset(features, bundle.labels, val_indices)
    test_dataset = EEGTensorDataset(features, bundle.labels, split.test_indices)
    train_loader = DataLoader(train_dataset, batch_size=config.batch_size, shuffle=True, num_workers=0, drop_last=True)
    val_loader = DataLoader(val_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, shuffle=False, num_workers=0)
    model = build_model(
        config.model_name,
        config.dataset,
        device,
        da_snn_options={
            "use_depthwise_separable": config.use_depthwise_separable,
            "use_dsgm": config.use_dsgm,
            "use_ttfs_encoder": config.use_ttfs_encoder,
            "use_dynamic_window": config.use_dynamic_window,
        },
    )
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    scheduler = CosineAnnealingLR(optimizer, T_max=max(config.max_epochs, 1), eta_min=1e-6)
    best_metrics = None
    best_score = -1.0
    best_state = None
    best_epoch = None
    epochs_ran = 0
    early_stopped = False
    stale_epochs = 0
    for _epoch in range(config.max_epochs):
        epochs_ran = _epoch + 1
        train_loss, train_acc = train_one_epoch(
            model,
            train_loader,
            criterion,
            optimizer,
            device,
            config.gamma_ttfs,
            config.noise_type,
            config.noise_level,
        )
        _val_loss, metrics = evaluate(model, val_loader, criterion, device, config.noise_type, config.noise_level)
        scheduler.step()
        if (_epoch + 1) % 20 == 0 or _epoch == 0:
            print(f"  [{_epoch+1}/{config.max_epochs}] train_acc={train_acc:.4f} val_acc={metrics['accuracy']:.4f}", flush=True)
        if metrics["accuracy"] > best_score + config.min_delta:
            best_score = metrics["accuracy"]
            best_metrics = metrics
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = _epoch + 1
            stale_epochs = 0
        else:
            stale_epochs += 1
            if stale_epochs >= config.patience:
                early_stopped = True
                print(f"  early stop at epoch {_epoch+1}", flush=True)
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    _loss, final_metrics = evaluate(model, test_loader, criterion, device, config.noise_type, config.noise_level)
    result = dict(final_metrics)
    if best_metrics is not None:
        result.update({f"best_val_{key}": value for key, value in best_metrics.items()})
    result.update(
        {
            "final_accuracy": final_metrics["accuracy"],
            "split": split.name,
            "seed": config.seed,
            "best_epoch": best_epoch,
            "stopped_epoch": epochs_ran,
            "epochs_ran": epochs_ran,
            "early_stopped": early_stopped,
            "train_subjects": _subjects_for_indices(bundle, train_indices),
            "val_subjects": _subjects_for_indices(bundle, val_indices),
            "test_subjects": _subjects_for_indices(bundle, split.test_indices),
            "train_count": int(len(train_indices)),
            "val_count": int(len(val_indices)),
            "test_count": int(len(split.test_indices)),
        }
    )
    return result


def run_experiment(bundle: DatasetBundle, splits: list[Split], config: ExperimentConfig) -> dict[str, float]:
    set_seed(config.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not config.dry_run else "cpu")
    max_splits = len(splits)
    if config.max_splits is not None:
        if config.max_splits < 1:
            raise ValueError("max_splits must be at least 1.")
        max_splits = min(max_splits, config.max_splits)
    if config.dry_run:
        max_splits = min(max_splits, 1)
    run_dir = config.output_dir / config.dataset / config.protocol / config.model_name / f"seed_{config.seed}"
    rows = []
    for split in splits[:max_splits]:
        result = run_single_split(bundle, split, config, device)
        rows.append(result)
        write_json(run_dir / f"{split.name}.json", result)
        summary = summarize_runs(rows)
        summary.update({"dataset": config.dataset, "model": config.model_name, "protocol": config.protocol, "seed": config.seed})
        write_json(run_dir / "summary.json", summary)
        write_csv(run_dir / "runs.csv", rows)
    return summary
