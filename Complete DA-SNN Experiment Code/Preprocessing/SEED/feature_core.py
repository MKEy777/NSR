"""Shared feature-extraction primitives for SEED preprocessing.

This module centralizes the PSE + spatial-mapping + LDS smoothing helpers so
that both the clean pipeline (``extract_features.py``) and the noise-injection
pipeline (``extract_features_noise.py``) share exactly the same numerical
implementation. Extracting them here does **not** change the clean behaviour;
``extract_features.py`` simply imports these symbols.
"""

from __future__ import annotations

import numpy as np
from scipy import signal
from pykalman import KalmanFilter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FS: int = 200
GRID_ROWS: int = 8
GRID_COLS: int = 9
TOTAL_FRAMES: int = 4
N_CHANNELS: int = 62

SEED62_CH_NAMES = [
    'FP1', 'FPZ', 'FP2', 'AF3', 'AF4', 'F7', 'F5', 'F3', 'F1', 'FZ', 'F2', 'F4', 'F6', 'F8', 'FT7', 'FC5',
    'FC3', 'FC1', 'FCZ', 'FC2', 'FC4', 'FC6', 'FT8', 'T7', 'C5', 'C3', 'C1', 'CZ', 'C2', 'C4', 'C6', 'T8',
    'TP7', 'CP5', 'CP3', 'CP1', 'CPZ', 'CP2', 'CP4', 'CP6', 'TP8', 'P7', 'P5', 'P3', 'P1', 'PZ', 'P2', 'P4',
    'P6', 'P8', 'PO7', 'PO5', 'PO3', 'POZ', 'PO4', 'PO6', 'PO8', 'CB1', 'O1', 'OZ', 'O2', 'CB2'
]

CHANNEL_2D_MAP = {
    'AF3': (0, 2), 'FP1': (0, 3), 'FPZ': (0, 4), 'FP2': (0, 5), 'AF4': (0, 6), 'F7': (1, 0), 'F5': (1, 1),
    'F3': (1, 2), 'F1': (1, 3), 'FZ': (1, 4), 'F2': (1, 5), 'F4': (1, 6), 'F6': (1, 7), 'F8': (1, 8),
    'FT7': (2, 0), 'FC5': (2, 1), 'FC3': (2, 2), 'FC1': (2, 3), 'FCZ': (2, 4), 'FC2': (2, 5), 'FC4': (2, 6),
    'FC6': (2, 7), 'FT8': (2, 8), 'T7': (3, 0), 'C5': (3, 1), 'C3': (3, 2), 'C1': (3, 3), 'CZ': (3, 4),
    'C2': (3, 5), 'C4': (3, 6), 'C6': (3, 7), 'T8': (3, 8), 'TP7': (4, 0), 'CP5': (4, 1), 'CP3': (4, 2),
    'CP1': (4, 3), 'CPZ': (4, 4), 'CP2': (4, 5), 'CP4': (4, 6), 'CP6': (4, 7), 'TP8': (4, 8), 'P7': (5, 0),
    'P5': (5, 1), 'P3': (5, 2), 'P1': (5, 3), 'PZ': (5, 4), 'P2': (5, 5), 'P4': (5, 6), 'P6': (5, 7), 'P8': (5, 8),
    'PO7': (6, 1), 'PO5': (6, 2), 'PO3': (6, 3), 'POZ': (6, 4), 'PO4': (6, 5), 'PO6': (6, 6), 'PO8': (6, 7),
    'CB1': (7, 2), 'O1': (7, 3), 'OZ': (7, 4), 'O2': (7, 5), 'CB2': (7, 6)
}


# ---------------------------------------------------------------------------
# PSE
# ---------------------------------------------------------------------------

def calculate_power_spectrum_entropy(x,fs: int = FS) -> float:
    """Shannon entropy of the Welch power spectrum of a 1-D signal."""
    f, Pxx = signal.welch(x, fs=fs, nperseg=min(256, len(x)), detrend='linear')
    Pxx = Pxx[Pxx > 1e-10]
    if not len(Pxx):
        return 0.0
    p = Pxx / Pxx.sum()
    p = p[p > 1e-10]
    return float(-np.sum(p * np.log(p)))


# ---------------------------------------------------------------------------
# Channel -> 8x9 spatial grid
# ---------------------------------------------------------------------------

def reshape_to_4x8x9(feat_4x62: np.ndarray) -> np.ndarray:
    out = np.zeros((TOTAL_FRAMES, GRID_ROWS, GRID_COLS), dtype=np.float32)
    for ch_idx, ch_name in enumerate(SEED62_CH_NAMES):
        if ch_name in CHANNEL_2D_MAP:
            r, c = CHANNEL_2D_MAP[ch_name]
            out[:, r, c] = feat_4x62[:, ch_idx]
    return out


# ---------------------------------------------------------------------------
# LDS (Kalman) smoothing along the window axis
# ---------------------------------------------------------------------------

def apply_lds_smoothing(trial_features: np.ndarray, n_em_iter: int = 5) -> np.ndarray:
    original_shape = trial_features.shape
    num_segments = original_shape[0]
    if num_segments <= 1:
      return trial_features

    features_reshaped = trial_features.reshape(num_segments, -1)

    kf = KalmanFilter(
        transition_matrices=[1], observation_matrices=[1],
        transition_covariance=5.0, observation_covariance=0.5,
        initial_state_mean=0, initial_state_covariance=1
    )

    smoothed = np.zeros_like(features_reshaped)
    for i in range(features_reshaped.shape[1]):
        observations = features_reshaped[:, i]
        try:
            kf_learned = kf.em(observations, n_iter=n_em_iter)
            smoothed_states_means, _ = kf_learned.smooth(observations)
            smoothed[:, i] = smoothed_states_means.flatten()
        except Exception as e:  # pragma: no cover - defensive fallback
            print(f"     [Warning] LDS-EM failed for a feature stream: {e}. Using original data for this stream.")
            smoothed[:, i] = observations

    return smoothed.reshape(original_shape).astype(np.float32)