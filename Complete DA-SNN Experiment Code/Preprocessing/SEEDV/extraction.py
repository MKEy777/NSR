import argparse
import os
import re
import time
import glob
import numpy as np
from scipy import signal
from scipy.io import loadmat, savemat
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple
import multiprocessing as mp
from pykalman import KalmanFilter

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "processed_data_all"
OUTPUT_DIR = BASE_DIR / "Feature_PowerSpectrumEntropy_LDS_Smoothed_SEEDV_Independent"

FS = 200
WINDOW_S = 4
STEP_S = 4

TOTAL_FRAMES = 4
N_CHANNELS = 62
GRID_ROWS = 8
GRID_COLS = 9

MAX_WORKERS = int(os.getenv("N_WORKERS", "16"))

SEED62_CH_NAMES = [
    'FP1','FPZ','FP2','AF3','AF4','F7','F5','F3','F1','FZ','F2','F4','F6','F8','FT7','FC5',
    'FC3','FC1','FCZ','FC2','FC4','FC6','FT8','T7','C5','C3','C1','CZ','C2','C4','C6','T8',
    'TP7','CP5','CP3','CP1','CPZ','CP2','CP4','CP6','TP8','P7','P5','P3','P1','PZ','P2','P4',
    'P6','P8','PO7','PO5','PO3','POZ','PO4','PO6','PO8','CB1','O1','OZ','O2','CB2'
]

CHANNEL_2D_MAP = {
    'AF3':(0,2),'FP1':(0,3),'FPZ':(0,4),'FP2':(0,5),'AF4':(0,6),
    'F7':(1,0),'F5':(1,1),'F3':(1,2),'F1':(1,3),'FZ':(1,4),'F2':(1,5),'F4':(1,6),'F6':(1,7),'F8':(1,8),
    'FT7':(2,0),'FC5':(2,1),'FC3':(2,2),'FC1':(2,3),'FCZ':(2,4),'FC2':(2,5),'FC4':(2,6),'FC6':(2,7),'FT8':(2,8),
    'T7':(3,0),'C5':(3,1),'C3':(3,2),'C1':(3,3),'CZ':(3,4),'C2':(3,5),'C4':(3,6),'C6':(3,7),'T8':(3,8),
    'TP7':(4,0),'CP5':(4,1),'CP3':(4,2),'CP1':(4,3),'CPZ':(4,4),'CP2':(4,5),'CP4':(4,6),'CP6':(4,7),'TP8':(4,8),
    'P7':(5,0),'P5':(5,1),'P3':(5,2),'P1':(5,3),'PZ':(5,4),'P2':(5,5),'P4':(5,6),'P6':(5,7),'P8':(5,8),
    'PO7':(6,1),'PO5':(6,2),'PO3':(6,3),'POZ':(6,4),'PO4':(6,5),'PO6':(6,6),'PO8':(6,7),
    'CB1':(7,2),'O1':(7,3),'OZ':(7,4),'O2':(7,5),'CB2':(7,6)
}

def segment_trial(trial_data, window_s=WINDOW_S, step_s=STEP_S, fs=FS):
    win_len = int(window_s * fs)
    step_len = int(step_s * fs)
    n_ch, T = trial_data.shape
    segments = []

    if T < win_len:
        return segments

    for start in range(0, T - win_len + 1, step_len):
        segment = trial_data[:, start:start + win_len]
        segments.append(segment)

    return segments

def zscore_trial(trial_data):
    trial_mean = np.mean(trial_data, axis=1, keepdims=True)
    trial_std = np.std(trial_data, axis=1, keepdims=True)
    normalized_trial = (trial_data - trial_mean) / (trial_std + 1e-8)
    normalized_trial = np.nan_to_num(normalized_trial.astype(np.float32))
    return normalized_trial

def calculate_power_spectrum_entropy(x, fs=FS):
    nseg = min(256, len(x))
    _, Pxx = signal.welch(x, fs=fs, nperseg=nseg, detrend="linear")

    Pxx = Pxx[Pxx > 1e-10]

    if Pxx.size == 0:
        return 0.0

    p = Pxx / Pxx.sum()
    p = p[p > 1e-10]

    return float(-np.sum(p * np.log(p)))

def reshape_to_4x8x9(feat_4x62):
    out = np.zeros((TOTAL_FRAMES, GRID_ROWS, GRID_COLS), dtype=np.float32)

    for ch_idx, ch_name in enumerate(SEED62_CH_NAMES):
        if ch_name in CHANNEL_2D_MAP:
            r, c = CHANNEL_2D_MAP[ch_name]
            out[:, r, c] = feat_4x62[:, ch_idx]

    return out

def extract_pse_feature_from_segment(segment):
    seg4x62x200 = segment.reshape(
        N_CHANNELS,
        TOTAL_FRAMES,
        FS,
        order="C"
    ).transpose(1, 0, 2)

    feats_4x62 = np.zeros((TOTAL_FRAMES, N_CHANNELS), dtype=np.float32)

    for t in range(TOTAL_FRAMES):
        for ch in range(N_CHANNELS):
            feats_4x62[t, ch] = calculate_power_spectrum_entropy(
                seg4x62x200[t, ch, :]
            )

    feat_4x8x9 = reshape_to_4x8x9(feats_4x62)

    return feat_4x8x9

def apply_lds_smoothing(trial_features, n_em_iter=5):
    original_shape = trial_features.shape
    num_segments = original_shape[0]

    if num_segments <= 1:
        return trial_features.astype(np.float32)

    features_reshaped = trial_features.reshape(num_segments, -1)

    kf = KalmanFilter(
        transition_matrices=[1],
        observation_matrices=[1],
        transition_covariance=5.0,
        observation_covariance=0.5,
        initial_state_mean=0,
        initial_state_covariance=1
    )

    smoothed_features_reshaped = np.zeros_like(features_reshaped)

    for i in range(features_reshaped.shape[1]):
        observations = features_reshaped[:, i]

        try:
            kf_learned = kf.em(observations, n_iter=n_em_iter)
            smoothed_means, _ = kf_learned.smooth(observations)
            smoothed_features_reshaped[:, i] = smoothed_means.ravel()
        except Exception:
            smoothed_features_reshaped[:, i] = observations

    return smoothed_features_reshaped.reshape(original_shape).astype(np.float32)

def get_session_id_from_filename(filename):
    file_base_name = os.path.splitext(filename)[0]
    parts = file_base_name.split("_")

    try:
        session_id = int(parts[1])
    except Exception:
        raise ValueError(f"无法从文件名解析 session_id: {filename}")

    if session_id not in [1, 2, 3]:
        raise ValueError(f"Session ID 无效: {session_id}")

    return session_id

def get_scene_keys(mat_data):
    scene_keys = [k for k in mat_data.keys() if k.startswith("scene")]

    scene_keys = sorted(
        scene_keys,
        key=lambda s: int(re.search(r"(\d+)$", s).group(1))
    )

    return scene_keys

def process_file(file_path: str, skip_lds: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    filename = os.path.basename(file_path)
    print(f"Processing: {filename}")

    session_id = get_session_id_from_filename(filename)

    labels_path = os.path.join(INPUT_DIR, "all_session_labels.mat")
    all_labels = loadmat(labels_path)
    current_labels = all_labels[f"label_session{session_id}"].flatten()

    mat_data = loadmat(file_path)
    scene_keys = get_scene_keys(mat_data)

    all_trial_features = []
    all_trial_labels = []
    all_subject_ids = []
    all_trial_ids = []
    all_session_ids = []

    for i, scene_key in enumerate(scene_keys):
        trial_data = mat_data[scene_key]

        if trial_data.shape[0] != N_CHANNELS:
            print(f"Skip {filename} {scene_key}: 通道数不是 {N_CHANNELS}, 当前为 {trial_data.shape[0]}")
            continue

        label = current_labels[i]

        normalized_trial = zscore_trial(trial_data)
        segments = segment_trial(normalized_trial)

        if not segments:
            continue

        trial_features_list = []

        for segment in segments:
            feat_4x8x9 = extract_pse_feature_from_segment(segment)
            trial_features_list.append(feat_4x8x9)

        trial_features = np.stack(trial_features_list, axis=0)
        if not skip_lds:
            trial_features = apply_lds_smoothing(trial_features)

        all_trial_features.append(trial_features)
        n_windows = trial_features.shape[0]
        all_trial_labels.extend([label] * n_windows)
        all_subject_ids.extend([int(filename.split('_')[0])] * n_windows)
        all_trial_ids.extend([i + 1] * n_windows)
        all_session_ids.extend([session_id] * n_windows)

    if not all_trial_features:
        return np.array([]), np.array([])

    file_features = np.vstack(all_trial_features).astype(np.float32)
    file_labels = np.array(all_trial_labels, dtype=np.int32)

    return file_features, file_labels, np.array(all_subject_ids, dtype=np.int64), np.array(all_trial_ids, dtype=np.int64), np.array(all_session_ids, dtype=np.int64)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-lds", action="store_true", help="Skip LDS smoothing and use raw PSE features")
    args = parser.parse_args()
    skip_lds = args.skip_lds

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    labels_path = os.path.join(INPUT_DIR, "all_session_labels.mat")

    if not os.path.exists(labels_path):
        print(f"错误: 未找到标签文件: {labels_path}")
        return

    file_paths = sorted(glob.glob(os.path.join(INPUT_DIR, "*.mat")))
    file_paths = [
        f for f in file_paths
        if "labels" not in os.path.basename(f)
    ]

    if not file_paths:
        print(f"错误: 未在 {INPUT_DIR} 中找到数据文件")
        return

    print(f"找到 {len(file_paths)} 个数据文件，开始处理...")

    start_time = time.time()

    mp_ctx = mp.get_context("spawn")

    all_features_list = []
    all_labels_list = []
    all_subject_ids_list, all_trial_ids_list, all_session_ids_list = [], [], []

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        mp_context=mp_ctx
    ) as executor:

        future_to_path = {
            executor.submit(process_file, path, skip_lds): path
            for path in file_paths
        }

        for future in as_completed(future_to_path):
            path = future_to_path[future]
            filename = os.path.basename(path)

            try:
                features, labels, subject_ids, trial_ids, session_ids = future.result()

                if features.size > 0:
                    all_features_list.append(features)
                    all_labels_list.append(labels)
                    all_subject_ids_list.append(subject_ids)
                    all_trial_ids_list.append(trial_ids)
                    all_session_ids_list.append(session_ids)

                print(f"✓ Completed: {filename}")

            except Exception as exc:
                print(f"✗ Failed: {filename}, error: {exc}")

    print(f"\n处理耗时: {time.time() - start_time:.2f}s")

    if not all_features_list:
        print("没有成功生成任何特征")
        return

    X_all = np.vstack(all_features_list).astype(np.float32)
    y_all = np.concatenate(all_labels_list).astype(np.int64)
    subject_all = np.concatenate(all_subject_ids_list).astype(np.int64)
    trial_all = np.concatenate(all_trial_ids_list).astype(np.int64)
    session_all = np.concatenate(all_session_ids_list).astype(np.int64)

    out_name = "all_features_pse_no_lds.mat" if skip_lds else "all_features_pse_lds_smoothed.mat"
    output_path = os.path.join(OUTPUT_DIR, out_name)

    savemat(
        output_path,
        {
            "features": X_all,
            "labels": y_all,
            "subject_id": subject_all,
            "trial_id": trial_all,
            "session_id": session_all
        },
        do_compression=True
    )

    print("\n全部处理完成")
    print(f"features shape: {X_all.shape}")
    print(f"labels shape:   {y_all.shape}")
    print(f"保存路径: {output_path}")

if __name__ == "__main__":
    main()
