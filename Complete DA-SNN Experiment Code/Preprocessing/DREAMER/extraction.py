import os
import time
import numpy as np
from scipy import signal
from scipy.io import loadmat, savemat
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pykalman import KalmanFilter

MAX_WORKERS = 12
FS = 128
GRID_ROWS = 4
GRID_COLS = 5
TOTAL_FRAMES = 9
N_CHANNELS = 14

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "PerSubject_9sZScore_14x1152"
OUTPUT_DIR = BASE_DIR / "Feature_PowerSpectrumEntropy_LDS_Smoothed_DREAMER"

DREAMER14_CH_NAMES = [
    "AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
    "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"
]

DREAMER_2D_MAP = {
    "AF3": (0, 1), "AF4": (0, 3),
    "F7": (1, 0), "F3": (1, 1),
    "F4": (1, 3), "F8": (1, 4),
    "T7": (2, 0), "FC5": (2, 1),
    "FC6": (2, 3), "T8": (2, 4),
    "P7": (3, 0), "O1": (3, 1),
    "O2": (3, 3), "P8": (3, 4),
}

def calculate_power_spectrum_entropy(x, fs=FS):
    f, Pxx = signal.welch(x, fs=fs, nperseg=min(128, len(x)), detrend="linear")
    Pxx = Pxx[Pxx > 1e-10]
    if len(Pxx) == 0:
        return 0.0
    p = Pxx / Pxx.sum()
    p = p[p > 1e-10]
    return -np.sum(p * np.log(p))

def reshape_to_9x4x5(x):
    out = np.zeros((TOTAL_FRAMES, GRID_ROWS, GRID_COLS), dtype=np.float32)
    for i, ch in enumerate(DREAMER14_CH_NAMES):
        r, c = DREAMER_2D_MAP[ch]
        out[:, r, c] = x[:, i]
    return out

def apply_lds(x, n_iter=3):
    n = x.shape[0]
    if n <= 1:
        return x.astype(np.float32)
    x2 = x.reshape(n, -1)
    kf = KalmanFilter(
        transition_matrices=[1],
        observation_matrices=[1],
        transition_covariance=5.0,
        observation_covariance=0.5,
        initial_state_mean=0,
        initial_state_covariance=1
    )
    y = np.zeros_like(x2)
    for i in range(x2.shape[1]):
        obs = x2[:, i]
        try:
            model = kf.em(obs, n_iter=n_iter)
            s, _ = model.smooth(obs)
            y[:, i] = s[:, 0]
        except:
            y[:, i] = obs
    return y.reshape(x.shape).astype(np.float32)

def process_file(fp):
    mat = loadmat(fp)
    X = mat["seg_X"]
    y = mat["seg_y"].flatten()
    segs_per_trial = mat["segs_per_trial"].flatten()

    import re
    subject_match = re.search(r'(\d+)', os.path.basename(fp))
    subject_value = int(subject_match.group(1)) if subject_match else 0
    boundaries = np.concatenate(([0], np.cumsum(segs_per_trial)))
    feats, labels, trial_ids = [], [], []

    for trial_idx, (start_idx, end_idx) in enumerate(zip(boundaries[:-1], boundaries[1:]), start=1):
        start_idx, end_idx = int(start_idx), int(end_idx)
        if start_idx >= end_idx:
            continue

        trial_features = []
        for seg in X[start_idx:end_idx]:
            if seg.shape[1] != N_CHANNELS:
                raise ValueError(seg.shape)

            f9x14 = np.zeros((TOTAL_FRAMES, N_CHANNELS), dtype=np.float32)

            for t in range(TOTAL_FRAMES):
                for c in range(N_CHANNELS):
                    f9x14[t, c] = calculate_power_spectrum_entropy(seg[t, c, :])

            trial_features.append(reshape_to_9x4x5(f9x14))

        if not trial_features:
            continue

        trial_features = apply_lds(np.stack(trial_features))
        feats.append(trial_features)
        labels.append(y[start_idx:end_idx].astype(np.int64))
        trial_ids.append(np.full(trial_features.shape[0], trial_idx, dtype=np.int64))

    if not feats:
        empty = np.array([])
        return empty, empty, empty, empty, empty

    feats = np.vstack(feats).astype(np.float32)
    labels = np.concatenate(labels).astype(np.int64)
    subject_ids = np.full(len(feats), subject_value, dtype=np.int64)
    session_ids = np.zeros(len(feats), dtype=np.int64)
    return feats, labels, subject_ids, np.concatenate(trial_ids).astype(np.int64), session_ids

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [
        os.path.join(INPUT_DIR, f)
        for f in sorted(os.listdir(INPUT_DIR))
        if f.endswith(".mat")
    ]
    if not files:
        print(f"No input files found in {INPUT_DIR}.")
        return

    all_x, all_y = [], []
    all_subject_ids, all_trial_ids, all_session_ids = [], [], []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(process_file, f) for f in files]
        for fut in as_completed(futs):
            x, y, subject_ids, trial_ids, session_ids = fut.result()
            if len(x) > 0:
                all_x.append(x)
                all_y.append(y)
                all_subject_ids.append(subject_ids)
                all_trial_ids.append(trial_ids)
                all_session_ids.append(session_ids)

    X = np.vstack(all_x)
    y = np.concatenate(all_y).astype(np.int64)
    subject_all = np.concatenate(all_subject_ids).astype(np.int64)
    trial_all = np.concatenate(all_trial_ids).astype(np.int64)
    session_all = np.concatenate(all_session_ids).astype(np.int64)

    savemat(
        os.path.join(OUTPUT_DIR, "all_features_pse_lds_smoothed.mat"),
        {"features": X, "labels": y, "subject_id": subject_all, "trial_id": trial_all, "session_id": session_all},
        do_compression=True
    )

if __name__ == "__main__":
    main()
