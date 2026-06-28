from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    input_shape: tuple[int, int, int]
    num_classes: int
    default_feature_file: str
    target_names: tuple[str, ...]
    label_mapper: Callable[[np.ndarray], np.ndarray] | None = None


def map_seed_labels(labels: np.ndarray) -> np.ndarray:
    mapping = {-1: 0, 0: 1, 1: 2}
    return np.array([mapping[int(v)] for v in labels], dtype=np.int64)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET_CONFIGS: dict[str, DatasetConfig] = {
    "seed": DatasetConfig(
        name="seed",
        input_shape=(4, 8, 9),
        num_classes=3,
        default_feature_file="Preprocessing/SEED/Feature_PowerSpectrumEntropy_LDS_Smoothed_SEED/all_features_pse_lds_smoothed.mat",
        target_names=("Negative", "Neutral", "Positive"),
        label_mapper=map_seed_labels,
    ),
    "seediv": DatasetConfig(
        name="seediv",
        input_shape=(4, 8, 9),
        num_classes=4,
        default_feature_file="Preprocessing/SEEDIV/Feature_PowerSpectrumEntropy_LDS_Smoothed_SEEDIV/all_features_pse_lds_smoothed.mat",
        target_names=("Happy", "Sad", "Fear", "Neutral"),
    ),
    "seedv": DatasetConfig(
        name="seedv",
        input_shape=(4, 8, 9),
        num_classes=5,
        default_feature_file="Preprocessing/SEEDV/Feature_PowerSpectrumEntropy_LDS_Smoothed_SEEDV_Independent/all_features_pse_lds_smoothed.mat",
        target_names=("Happy", "Sad", "Fear", "Disgust", "Neutral"),
    ),
    "deap": DatasetConfig(
        name="deap",
        input_shape=(6, 6, 7),
        num_classes=4,
        default_feature_file="Preprocessing/DEAP/Feature_PowerSpectrumEntropy_LDS_Smoothed_DEAP/all_features_pse_lds_smoothed.mat",
        target_names=("LVLA", "LVHA", "HVLA", "HVHA"),
    ),
    "dreamer": DatasetConfig(
        name="dreamer",
        input_shape=(9, 4, 5),
        num_classes=4,
        default_feature_file="Preprocessing/DREAMER/Feature_PowerSpectrumEntropy_LDS_Smoothed_DREAMER/all_features_pse_lds_smoothed.mat",
        target_names=("LVLA", "LVHA", "HVLA", "HVHA"),
    ),
}


def resolve_feature_file(dataset: str, feature_file: str | None = None) -> Path:
    if feature_file:
        return Path(feature_file)
    return PROJECT_ROOT / DATASET_CONFIGS[dataset].default_feature_file
