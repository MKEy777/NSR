
import os
import time
import numpy as np
from scipy.io import loadmat, savemat
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from feature_core import (
    FS,
    TOTAL_FRAMES,
    N_CHANNELS,
    calculate_power_spectrum_entropy,
    reshape_to_4x8x9,
    apply_lds_smoothing,
)

MAX_WORKERS       = 24
SELECTED_FEATURE  = "PowerSpectrumEntropy"

BASE_DIR          = Path(__file__).resolve().parent
INPUT_DIR         = BASE_DIR / "PerSession_4sZScore_62x800"
OUTPUT_DIR        = BASE_DIR / "Feature_PowerSpectrumEntropy_LDS_Smoothed_SEED"

def process_file_robust(file_path: str):
    print(f"Processing: {os.path.basename(file_path)}")
    mat = loadmat(file_path)
    X_raw = mat['seg_X']
    y_raw = mat['seg_y'].flatten()
    segs_per_trial = mat['segs_per_trial'].flatten()

    boundaries = np.cumsum(segs_per_trial)
    full_boundaries = np.concatenate(([0], boundaries))
    num_trials = len(segs_per_trial)
    import re
    subject_match = re.search(r'subject_(\d+)', os.path.basename(file_path))
    session_match = re.search(r'session_(\d+)', os.path.basename(file_path))
    subject_value = int(subject_match.group(1)) if subject_match else 0
    session_value = int(session_match.group(1)) if session_match else 0
    all_session_features = []
    all_session_labels = []
    all_subject_ids = []
    all_trial_ids = []
    all_session_ids = []

    for i in range(num_trials):
        start_idx, end_idx = int(full_boundaries[i]), int(full_boundaries[i+1])
        if start_idx >= end_idx: continue
        trial_label = y_raw[start_idx]
        trial_raw_data = X_raw[start_idx:end_idx]
        
        trial_features_list = []
        for j in range(trial_raw_data.shape[0]):
            seg4x62x200 = trial_raw_data[j]
            feats_4x62 = np.zeros((TOTAL_FRAMES, N_CHANNELS), dtype=np.float32)
            for t in range(TOTAL_FRAMES):
                for ch in range(N_CHANNELS):
                    feats_4x62[t, ch] = calculate_power_spectrum_entropy(seg4x62x200[t, ch, :])
            reshaped_feat = reshape_to_4x8x9(feats_4x62)
            trial_features_list.append(reshaped_feat)
        
        if not trial_features_list: continue
        
        trial_features = np.stack(trial_features_list)
        
        smoothed_features = apply_lds_smoothing(trial_features)
        all_session_features.append(smoothed_features)
        n_windows = len(trial_features_list)
        all_session_labels.extend([trial_label] * n_windows)
        all_subject_ids.extend([subject_value] * n_windows)
        all_trial_ids.extend([i + 1] * n_windows)
        all_session_ids.extend([session_value] * n_windows)

    if not all_session_features: return np.array([]), np.array([])
    final_features = np.vstack(all_session_features)
    final_labels = np.array(all_session_labels, dtype=np.int32)
    return final_features, final_labels, np.array(all_subject_ids, dtype=np.int64), np.array(all_trial_ids, dtype=np.int64), np.array(all_session_ids, dtype=np.int64)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_features_list, all_labels_list = [], []
    all_subject_ids_list, all_trial_ids_list, all_session_ids_list = [], [], []
    file_paths = [os.path.join(INPUT_DIR, f) for f in sorted(os.listdir(INPUT_DIR)) if f.endswith('.mat')]
    
    start_time = time.time()
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_path = {executor.submit(process_file_robust, path): path for path in file_paths}
        
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                features, labels, subject_ids, trial_ids, session_ids = future.result()
                if features.size > 0:
                    all_features_list.append(features)
                    all_labels_list.append(labels)
                    all_subject_ids_list.append(subject_ids)
                    all_trial_ids_list.append(trial_ids)
                    all_session_ids_list.append(session_ids)
                print(f"   ✓ Completed processing: {os.path.basename(path)}")
            except Exception as exc:
                print(f"   ✗ {os.path.basename(path)} generated an exception: {exc}")
    
    print(f"\nParallel processing finished in {time.time() - start_time:.2f}s.")
    
    if not all_features_list:
        print("No features were processed successfully. Exiting.")
        return

    print("Aggregating results...")
    X_all = np.vstack(all_features_list)
    y_all = np.concatenate(all_labels_list).astype(np.int64)
    subject_all = np.concatenate(all_subject_ids_list).astype(np.int64)
    trial_all = np.concatenate(all_trial_ids_list).astype(np.int64)
    session_all = np.concatenate(all_session_ids_list).astype(np.int64)
    
    print("\n--- Data Aggregation Summary ---")
    print(f"Total samples aggregated: {len(X_all)}")

    output_filename = "all_features_pse_lds_smoothed.mat"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    savemat(output_path, {'features': X_all, 'labels': y_all, 'subject_id': subject_all, 'trial_id': trial_all, 'session_id': session_all}, do_compression=True)
    print(f"\nSuccessfully saved all aggregated data to: {output_path}")

if __name__ == '__main__':
    main()
