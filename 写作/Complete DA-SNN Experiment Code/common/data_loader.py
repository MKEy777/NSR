from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from scipy.io import loadmat
from sklearn.model_selection import StratifiedShuffleSplit, train_test_split
from torch.utils.data import Dataset

from common.config import DATASET_CONFIGS


@dataclass(frozen=True)
class DatasetBundle:
    features: np.ndarray
    labels: np.ndarray
    subject_id: np.ndarray | None = None
    trial_id: np.ndarray | None = None
    session_id: np.ndarray | None = None


@dataclass(frozen=True)
class Split:
    name: str
    train_indices: np.ndarray
    test_indices: np.ndarray
    val_indices: np.ndarray | None = None


class SplitCacheMismatch(ValueError):
    pass


class EEGTensorDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray, indices: np.ndarray):
        self.features = torch.as_tensor(features[indices], dtype=torch.float32)
        self.labels = torch.as_tensor(labels[indices], dtype=torch.long)

    def __len__(self) -> int:
        return int(self.labels.shape[0])

    def __getitem__(self, idx: int):
        return self.features[idx], self.labels[idx]


def _flatten_vector(mat_data: dict, key: str) -> np.ndarray | None:
    if key not in mat_data:
        return None
    return np.asarray(mat_data[key]).reshape(-1)


def load_feature_bundle(
    feature_file: str | Path,
    *,
    dataset: str | None = None,
    require_metadata: bool = True,
) -> DatasetBundle:
    mat_data = loadmat(feature_file)
    if "features" not in mat_data or "labels" not in mat_data:
        raise ValueError(f"{feature_file} must contain 'features' and 'labels'.")

    features = np.asarray(mat_data["features"], dtype=np.float32)
    labels = np.asarray(mat_data["labels"]).reshape(-1)
    if dataset and DATASET_CONFIGS[dataset].label_mapper is not None:
        labels = DATASET_CONFIGS[dataset].label_mapper(labels)
    labels = labels.astype(np.int64)

    subject_id = _flatten_vector(mat_data, "subject_id")
    trial_id = _flatten_vector(mat_data, "trial_id")
    session_id = _flatten_vector(mat_data, "session_id")
    missing = [name for name, value in (("subject_id", subject_id), ("trial_id", trial_id)) if value is None]
    if require_metadata and missing:
        raise ValueError(
            f"{feature_file} is missing {', '.join(missing)}. "
            "Re-run the corresponding Preprocessing/*/extraction.py script to regenerate features with metadata."
        )

    n_samples = features.shape[0]
    for key, value in (("labels", labels), ("subject_id", subject_id), ("trial_id", trial_id), ("session_id", session_id)):
        if value is not None and len(value) != n_samples:
            raise ValueError(f"{key} length {len(value)} does not match feature count {n_samples}.")

    return DatasetBundle(
        features=features,
        labels=labels,
        subject_id=None if subject_id is None else subject_id.astype(np.int64),
        trial_id=None if trial_id is None else trial_id.astype(np.int64),
        session_id=None if session_id is None else session_id.astype(np.int64),
    )


def _normalize_indices(indices: np.ndarray) -> np.ndarray:
    return np.asarray(indices, dtype=np.int64).reshape(-1)


def _save_splits(path: Path, splits: list[Split], n_samples: int, metadata: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, np.ndarray] = {
        "names": np.array([split.name for split in splits], dtype=object),
        "n_samples": np.array([n_samples], dtype=np.int64),
        "metadata_json": np.array([json.dumps(metadata, sort_keys=True)], dtype=object),
    }
    for idx, split in enumerate(splits):
        payload[f"train_indices_{idx}"] = _normalize_indices(split.train_indices)
        payload[f"test_indices_{idx}"] = _normalize_indices(split.test_indices)
        if split.val_indices is not None:
            payload[f"val_indices_{idx}"] = _normalize_indices(split.val_indices)
    np.savez(path, **payload)


def _validate_split_indices(path: Path, splits: list[Split], n_samples: int) -> None:
    for split in splits:
        arrays = [split.train_indices, split.test_indices]
        if split.val_indices is not None:
            arrays.append(split.val_indices)
        for indices in arrays:
            if indices.size and (indices.min() < 0 or indices.max() >= n_samples):
                raise ValueError(f"Saved split {path} contains indices outside current feature count {n_samples}.")


def _load_splits(path: Path, n_samples: int, expected_metadata: dict[str, object]) -> list[Split]:
    data = np.load(path, allow_pickle=True)
    if "metadata_json" not in data:
        raise SplitCacheMismatch(f"Saved split {path} does not contain split metadata.")
    metadata = json.loads(str(data["metadata_json"][0]))
    for key, expected_value in expected_metadata.items():
        if metadata.get(key) != expected_value:
            raise SplitCacheMismatch(
                f"Saved split {path} has {key}={metadata.get(key)!r}, expected {expected_value!r}."
            )
    if "n_samples" in data and int(data["n_samples"][0]) != n_samples:
        raise ValueError(f"Saved split {path} was built for {int(data['n_samples'][0])} samples, not {n_samples}.")
    names = [str(name) for name in data["names"].tolist()]
    splits = []
    for idx, name in enumerate(names):
        val_key = f"val_indices_{idx}"
        splits.append(
            Split(
                name=name,
                train_indices=_normalize_indices(data[f"train_indices_{idx}"]),
                test_indices=_normalize_indices(data[f"test_indices_{idx}"]),
                val_indices=_normalize_indices(data[val_key]) if val_key in data else None,
            )
        )
    _validate_split_indices(path, splits, n_samples)
    return splits


def _persist_or_create_splits(
    path: Path | None,
    n_samples: int,
    metadata: dict[str, object],
    factory,
) -> list[Split]:
    if path is not None and path.exists():
        try:
            return _load_splits(path, n_samples, metadata)
        except SplitCacheMismatch:
            pass
    splits = factory()
    if path is not None:
        _save_splits(path, splits, n_samples, metadata)
    return splits


def _split_file(split_dir: str | Path | None, dataset: str | None, protocol: str, seed: int) -> Path | None:
    if split_dir is None:
        return None
    if dataset is None:
        raise ValueError("dataset must be provided when split_dir is used.")
    return Path(split_dir) / dataset / protocol / f"seed_{seed}.npz"


def make_loso_splits(bundle: DatasetBundle) -> list[Split]:
    if bundle.subject_id is None:
        raise ValueError("LOSO requires subject_id metadata.")
    splits: list[Split] = []
    all_indices = np.arange(bundle.labels.shape[0])
    for subject in np.unique(bundle.subject_id):
        test_indices = all_indices[bundle.subject_id == subject]
        train_indices = all_indices[bundle.subject_id != subject]
        splits.append(
            Split(
                name=f"subject_{int(subject):02d}",
                train_indices=train_indices,
                test_indices=test_indices,
                val_indices=test_indices,
            )
        )
    return splits


def _requested_test_count(n_items: int, test_size: float) -> int:
    if isinstance(test_size, float):
        return int(np.ceil(n_items * test_size))
    return int(test_size)


def _format_class_counts(labels: np.ndarray) -> str:
    values, counts = np.unique(labels, return_counts=True)
    return "{" + ", ".join(f"{int(value)}: {int(count)}" for value, count in zip(values, counts)) + "}"


def make_subject_stratified_splits(
    bundle: DatasetBundle,
    *,
    test_size: float,
    seed: int,
    strict_stratified: bool = True,
) -> list[Split]:
    if bundle.subject_id is None or bundle.trial_id is None:
        raise ValueError("subject_80_20 requires subject_id and trial_id metadata.")
    splits: list[Split] = []
    rng_seed = int(seed)
    for subject in np.unique(bundle.subject_id):
        subject_indices = np.flatnonzero(bundle.subject_id == subject)
        session = np.zeros_like(bundle.trial_id) if bundle.session_id is None else bundle.session_id
        trial_keys = np.array([f"{int(s)}_{int(t)}" for s, t in zip(session[subject_indices], bundle.trial_id[subject_indices])])
        unique_trials = np.unique(trial_keys)
        trial_labels = np.array([bundle.labels[subject_indices][trial_keys == trial][0] for trial in unique_trials])
        n_classes = len(np.unique(trial_labels))
        n_test = _requested_test_count(len(unique_trials), test_size)
        n_train = len(unique_trials) - n_test
        class_counts = np.unique(trial_labels, return_counts=True)[1]
        can_stratify = (
            len(unique_trials) >= 2
            and n_classes > 1
            and class_counts.min() >= 2
            and n_train >= n_classes
            and n_test >= n_classes
        )
        if len(unique_trials) < 2:
            if strict_stratified:
                raise ValueError(
                    f"subject_{int(subject):02d} cannot be split: "
                    f"only {len(unique_trials)} unique trial is available."
                )
            train_indices = subject_indices
            test_indices = subject_indices
        elif can_stratify:
            splitter = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=rng_seed)
            train_trial_local, test_trial_local = next(splitter.split(unique_trials, trial_labels))
            train_trials = set(unique_trials[train_trial_local])
            test_trials = set(unique_trials[test_trial_local])
            train_indices = subject_indices[np.isin(trial_keys, list(train_trials))]
            test_indices = subject_indices[np.isin(trial_keys, list(test_trials))]
        else:
            if strict_stratified:
                raise ValueError(
                    f"subject_{int(subject):02d} cannot be stratified for subject_80_20: "
                    f"class trial counts={_format_class_counts(trial_labels)}, "
                    f"unique_trials={len(unique_trials)}, train_trials={n_train}, test_trials={n_test}."
                )
            train_trial_local, test_trial_local = train_test_split(
                np.arange(len(unique_trials)),
                test_size=test_size,
                random_state=rng_seed,
                shuffle=True,
            )
            train_trials = set(unique_trials[train_trial_local])
            test_trials = set(unique_trials[test_trial_local])
            train_indices = subject_indices[np.isin(trial_keys, list(train_trials))]
            test_indices = subject_indices[np.isin(trial_keys, list(test_trials))]
        splits.append(
            Split(
                name=f"subject_{int(subject):02d}",
                train_indices=_normalize_indices(train_indices),
                test_indices=_normalize_indices(test_indices),
            )
        )
    return splits


def make_fixed_subject_holdout_splits(
    bundle: DatasetBundle,
    *,
    test_size: float,
    seed: int,
    n_folds: int = 5,
) -> list[Split]:
    if bundle.subject_id is None:
        raise ValueError("subject_80_20 requires subject_id metadata.")
    subjects = np.unique(bundle.subject_id)
    if subjects.size < n_folds:
        raise ValueError(f"subject_80_20 requires at least {n_folds} subjects, got {subjects.size}.")
    test_subject_count = max(1, int(np.floor(subjects.size * test_size)))
    required_test_subjects = n_folds * test_subject_count
    if required_test_subjects > subjects.size:
        raise ValueError(
            f"subject_80_20 cannot build {n_folds} folds with {test_subject_count} test subjects each "
            f"from {subjects.size} subjects."
        )
    rng = np.random.default_rng(int(seed))
    shuffled_subjects = subjects.copy()
    rng.shuffle(shuffled_subjects)
    all_indices = np.arange(bundle.labels.shape[0])
    splits: list[Split] = []
    for fold_idx in range(n_folds):
        start = fold_idx * test_subject_count
        stop = start + test_subject_count
        test_subjects = shuffled_subjects[start:stop]
        test_mask = np.isin(bundle.subject_id, test_subjects)
        test_indices = all_indices[test_mask]
        train_indices = all_indices[~test_mask]
        splits.append(
            Split(
                name=f"subject_group_{fold_idx:02d}",
                train_indices=_normalize_indices(train_indices),
                test_indices=_normalize_indices(test_indices),
                val_indices=_normalize_indices(test_indices),
            )
        )
    return splits


def make_random_splits(bundle: DatasetBundle, *, test_size: float, seed: int) -> list[Split]:
    indices = np.arange(bundle.labels.shape[0])
    stratify = bundle.labels if len(np.unique(bundle.labels)) > 1 else None
    train_indices, test_indices = train_test_split(
        indices,
        test_size=test_size,
        random_state=seed,
        shuffle=True,
        stratify=stratify,
    )
    return [
        Split(
            name=f"seed_{seed}",
            train_indices=train_indices,
            test_indices=test_indices,
            val_indices=test_indices,
        )
    ]


def build_splits(
    protocol: str,
    bundle: DatasetBundle,
    *,
    seed: int,
    test_size: float = 0.2,
    dataset: str | None = None,
    split_dir: str | Path | None = None,
    strict_stratified: bool = True,
) -> list[Split]:
    split_file = _split_file(split_dir, dataset, protocol, seed)
    n_samples = int(bundle.labels.shape[0])
    metadata: dict[str, object] = {
        "schema_version": 2,
        "dataset": "" if dataset is None else str(dataset),
        "protocol": str(protocol),
        "seed": int(seed),
        "test_size": float(test_size),
        "strict_stratified": bool(strict_stratified),
    }
    if protocol == "loso":
        metadata["loso_val_policy"] = "val_equals_test_subject"
        return _persist_or_create_splits(split_file, n_samples, metadata, lambda: make_loso_splits(bundle))
    if protocol == "subject_80_20":
        metadata["subject_80_20_policy"] = "fixed_5fold_subject_val_equals_test"
        return _persist_or_create_splits(
            split_file,
            n_samples,
            metadata,
            lambda: make_fixed_subject_holdout_splits(
                bundle,
                test_size=test_size,
                seed=seed,
            ),
        )
    if protocol == "random_80_20":
        metadata["random_80_20_policy"] = "val_equals_test"
        return _persist_or_create_splits(
            split_file,
            n_samples,
            metadata,
            lambda: make_random_splits(bundle, test_size=test_size, seed=seed),
        )
    raise ValueError(f"Unknown protocol: {protocol}")
