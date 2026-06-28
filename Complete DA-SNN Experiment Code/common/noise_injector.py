from __future__ import annotations

import numpy as np
import torch


class StandardMinMaxEncoder:
    def __init__(self, eps: float = 1e-8):
        self.eps = eps
        self.data_min: np.ndarray | None = None
        self.data_max: np.ndarray | None = None

    def fit(self, features: np.ndarray) -> "StandardMinMaxEncoder":
        self.data_min = np.min(features, axis=0, keepdims=True)
        self.data_max = np.max(features, axis=0, keepdims=True)
        return self

    def transform(self, features: np.ndarray) -> np.ndarray:
        if self.data_min is None or self.data_max is None:
            raise RuntimeError("StandardMinMaxEncoder must be fitted before transform.")
        denom = np.maximum(self.data_max - self.data_min, self.eps)
        return ((features - self.data_min) / denom).astype(np.float32)

    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        return self.fit(features).transform(features)


def inject_noise(features: torch.Tensor, noise_type: str | None, noise_level: float) -> torch.Tensor:
    if noise_type in (None, "none") or noise_level <= 0:
        return features
    if noise_type == "gaussian":
        return features + torch.randn_like(features) * noise_level
    if noise_type == "uniform":
        return features + (torch.rand_like(features) * 2.0 - 1.0) * noise_level
    if noise_type == "mask":
        keep_mask = (torch.rand_like(features) > noise_level).to(features.dtype)
        return features * keep_mask
    raise ValueError(f"Unknown noise_type: {noise_type}")
