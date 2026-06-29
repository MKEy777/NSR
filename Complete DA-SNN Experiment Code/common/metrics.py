from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


def compute_metrics(labels: np.ndarray, preds: np.ndarray, num_classes: int) -> dict[str, float]:
    labels = np.asarray(labels)
    preds = np.asarray(preds)
    cm = confusion_matrix(labels, preds, labels=np.arange(num_classes))
    total = cm.sum()
    per_class_acc = []
    specificity = []
    for i in range(num_classes):
        tp = cm[i, i]
        fn = cm[i, :].sum() - tp
        fp = cm[:, i].sum() - tp
        tn = total - tp - fn - fp
        per_class_acc.append((tp + tn) / total if total else 0.0)
        specificity.append(tn / (tn + fp) if (tn + fp) else 0.0)
    return {
        "accuracy": float(np.mean(labels == preds)) if labels.size else 0.0,
        "f1": float(f1_score(labels, preds, average="macro", zero_division=0)),
        "precision": float(precision_score(labels, preds, average="macro", zero_division=0)),
        "sensitivity": float(recall_score(labels, preds, average="macro", zero_division=0)),
        "specificity": float(np.mean(specificity)),
        "class_accuracy": float(np.mean(per_class_acc)),
    }


def summarize_runs(runs: list[dict[str, float]]) -> dict[str, float]:
    metric_keys = [k for k in runs[0].keys() if isinstance(runs[0][k], (int, float))]
    summary: dict[str, float] = {"count": len(runs)}
    for key in metric_keys:
        values = np.array([float(run[key]) for run in runs], dtype=np.float64)
        summary[f"{key}_mean"] = float(values.mean())
        summary[f"{key}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return summary


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _serialize_csv_value(value):
    if isinstance(value, (list, tuple)):
        return ",".join(str(item) for item in value)
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: _serialize_csv_value(value) for key, value in row.items()} for row in rows)
