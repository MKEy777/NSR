import os
import time
import numpy as np
from scipy import signal
from scipy.io import loadmat, savemat
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple
from pykalman import KalmanFilter

MAX_WORKERS = 8
FS = 128
GRID_ROWS = 6
GRID_COLS = 7
TOTAL_FRAMES = 6
N_CHANNELS = 32

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "PerSubject_9sZScore_32x1152"
OUTPUT_DIR = BASE_DIR / "Feature_PowerSpectrumEntropy_LDS_Smoothed_DEAP"

DEAP32_CH_NAMES = [
    'Fp1','AF3','F7','F3','FC1','FC5','T7','C3','CP1','CP5','P7','P3','Pz','PO3','O1','Oz',
    'O2','PO4','P4','P8','CP6','CP2','C4','T8','FC6','FC2','F4','F8','AF4','Fp2','Fz','Cz'
]
DEAP_2D_MAP = {
    'Fp1': (0, 2), 'Fp2': (0, 3),
    'AF3': (1, 0), 'F3': (1, 1), 'F4': (1, 5), 'AF4': (1, 6),
    'F7': (2, 0), 'FC5': (2, 1), 'FC1': (2, 2), 'Fz': (2, 3),
    'FC2': (2, 4), 'FC6': (2, 5), 'F8': (2, 6),
    'T7': (3, 0), 'C3': (3, 1), 'CP1': (3, 2), 'Cz': (3, 3),
    'CP2': (3, 4), 'C4': (3, 5), 'T8': (3, 6),
    'P7': (4, 0), 'CP5': (4, 1), 'P3': (4, 2), 'Pz': (4, 3),
    'P4': (4, 4), 'CP6': (4, 5), 'P8': (4, 6),
    'PO3': (5, 1), 'O1': (5, 2), 'Oz': (5, 3), 'O2': (5, 4), 'PO4': (5, 5)
}

def calculate_power_spectrum_entropy(x, fs=FS):
    f, Pxx = signal.welch(x, fs=fs, nperseg=min(192, len(x)), detrend="linear")
    Pxx = Pxx[Pxx > 1e-10]
    if not len(Pxx):
        return 0.0
    p = Pxx / Pxx.sum()
    p = p[p > 1e-10]
    return -np.sum(p * np.log(p))

def reshape_to_6x7(feat_6x32):
    out = np.zeros((TOTAL_FRAMES, GRID_ROWS, GRID_COLS), dtype=np.float32)
    for ch_idx, ch_name in enumerate(DEAP32_CH_NAMES):
        if ch_name in DEAP_2D_MAP:
            r, c = DEAP_2D_MAP[ch_name]
            out[:, r, c] = feat_6x32[:, ch_idx]
    return out

def apply_lds_smoothing(trial_features, n_em_iter=5):
    original_shape = trial_features.shape
    num_segments = original_shape[0]
    if num_segments <= 1:
        return trial_features.astype(np.float32)
    features_reshaped = trial_features.reshape(num_segments, -1)
    kf = KalmanFilter(
        transition_matrices=[1], observation_matrices=[1],
        transition_covariance=5.0, observation_covariance=0.5,
        initial_state_mean=0, initial_state_covariance=1
    )
    smoothed = np.zeros_like(features_reshaped)
    for i in range(features_reshaped.shape[1]):
        obs = features_reshaped[:, i]
        try:
            kf_learned = kf.em(obs, n_iter=n_em_iter)
            smoothed_states, _ = kf_learned.smooth(obs)
            smoothed[:, i] = smoothed_states.flatten()
        except Exception:
            smoothed[:, i] = obs
    return smoothed.reshape(original_shape).astype(np.float32)

def process_file(file_path):
    print(f"Processing: {os.path.basename(file_path)}")
    mat = loadmat(file_path)
    X_raw = mat["seg_X"]
    y_raw = mat["seg_y"].flatten()
    segs_per_trial = mat["segs_per_trial"].flatten()

    boundaries = np.cumsum(segs_per_trial)
    full_boundaries = np.concatenate(([0], boundaries))

    num_trials = len(segs_per_trial)

    import re
    subject_match = re.search(r'(\d+)', os.path.basename(file_path))
    subject_value = int(subject_match.group(1)) if subject_match else 0
    all_trial_features = []
    all_trial_labels = []
    all_subject_ids = []
    all_trial_ids = []
    all_session_ids = []

    for i in range(num_trials):
        start_idx = int(full_boundaries[i])
        end_idx = int(full_boundaries[i + 1])

        if start_idx >= end_idx:
            continue

        trial_segs = X_raw[start_idx:end_idx]

        trial_feat_list = []

        for j in range(trial_segs.shape[0]):
            seg = trial_segs[j]

            feats_6x32 = np.zeros((TOTAL_FRAMES, N_CHANNELS), dtype=np.float32)

            for t in range(TOTAL_FRAMES):
                for ch in range(N_CHANNELS):
                    feats_6x32[t, ch] = calculate_power_spectrum_entropy(
                        seg[t, ch, :]
                    )

            feat_map = reshape_to_6x7(feats_6x32)
            trial_feat_list.append(feat_map)

        if not trial_feat_list:
            continue

        trial_features = np.stack(trial_feat_list)

        smoothed = apply_lds_smoothing(trial_features)

        label = int(np.bincount(y_raw[start_idx:end_idx]).argmax())

        all_trial_features.append(smoothed)
        all_trial_labels.append(np.full(smoothed.shape[0], label, dtype=np.int64))
        all_subject_ids.append(np.full(smoothed.shape[0], subject_value, dtype=np.int64))
        all_trial_ids.append(np.full(smoothed.shape[0], i + 1, dtype=np.int64))
        all_session_ids.append(np.zeros(smoothed.shape[0], dtype=np.int64))

    if not all_trial_features:
        return np.array([]), np.array([])

    final = np.vstack(all_trial_features)
    labels = np.concatenate(all_trial_labels).astype(np.int64)
    subject_ids = np.concatenate(all_subject_ids).astype(np.int64)
    trial_ids = np.concatenate(all_trial_ids).astype(np.int64)
    session_ids = np.concatenate(all_session_ids).astype(np.int64)

    return final, labels, subject_ids, trial_ids, session_ids

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_features, all_labels = [], []
    all_subject_ids, all_trial_ids, all_session_ids = [], [], []
    file_paths = [
        os.path.join(INPUT_DIR, f)
        for f in sorted(os.listdir(INPUT_DIR))
        if f.endswith(".mat")
    ]
    start_time = time.time()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_path = {executor.submit(process_file, p): p for p in file_paths}
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                features, labels, subject_ids, trial_ids, session_ids = future.result()
                if features.size > 0:
                    all_features.append(features)
                    all_labels.append(labels)
                    all_subject_ids.append(subject_ids)
                    all_trial_ids.append(trial_ids)
                    all_session_ids.append(session_ids)
                print(f"   ok Completed: {os.path.basename(path)}")
            except Exception as exc:
                print(f"   fail {os.path.basename(path)}: {exc}")
    print(f"Done in {time.time() - start_time:.2f}s.")
    if not all_features:
        print("No features generated.")
        return
    X_all = np.vstack(all_features)
    y_all = np.concatenate(all_labels).astype(np.int64)
    subject_all = np.concatenate(all_subject_ids).astype(np.int64)
    trial_all = np.concatenate(all_trial_ids).astype(np.int64)
    session_all = np.concatenate(all_session_ids).astype(np.int64)
    output_path = os.path.join(OUTPUT_DIR, "all_features_pse_lds_smoothed.mat")
    savemat(output_path, {"features": X_all, "labels": y_all, "subject_id": subject_all, "trial_id": trial_all, "session_id": session_all}, do_compression=True)
    print(f"Saved: {output_path}, shape: {X_all.shape}")

if __name__ == "__main__":
    main()
