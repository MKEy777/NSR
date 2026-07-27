import os
import numpy as np
import pickle as cPickle
from scipy import signal as sig
from scipy.io import savemat
from pathlib import Path

FS = 128
WINDOW_S = 9
STEP_S = 9
BASELINE_S = 3
N_CHANNELS = 32
TOTAL_FRAMES = 6

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "dataset"
OUTPUT_DIR = BASE_DIR / "PerSubject_9sZScore_32x1152"

def discretize_label(valence, arousal):
    hv = 1 if valence >= 5 else 0
    ha = 1 if arousal >= 5 else 0
    return hv * 2 + ha

def bandpass_filter(data, fs=FS, lowcut=1.0, highcut=50.0, order=4):
    nyq = 0.5 * fs
    b, a = sig.butter(order, [lowcut / nyq, highcut / nyq], btype='band')
    return sig.filtfilt(b, a, data, axis=1).astype(np.float32)

def segment_trial(trial_data):
    win = int(WINDOW_S * FS)
    step = int(STEP_S * FS)
    n_ch = trial_data.shape[0]
    pts_per_frame = int(1.5 * FS)
    segments = []
    _, T = trial_data.shape
    if T < win:
        return segments
    num_seg = (T - win) // step + 1
    for i in range(num_seg):
        seg = trial_data[:, i * step : i * step + win]
        seg = seg.reshape(n_ch, TOTAL_FRAMES, pts_per_frame)
        seg = np.transpose(seg, (1, 0, 2))
        segments.append(seg.astype(np.float32))
    return segments

def process_subject(filepath):
    print(f"Processing: {os.path.basename(filepath)}")
    with open(filepath, 'rb') as f:
        loaddata = cPickle.load(f, encoding="latin1")

    labels_raw = loaddata['labels']
    data_raw = loaddata['data'].astype(np.float32)
    data_raw = data_raw[:, :N_CHANNELS, :]

    num_trials = data_raw.shape[0]
    segments_list = []
    seg_labels_list = []
    segs_per_trial_list = []

    baseline_len = int(BASELINE_S * FS)

    for trial_idx in range(num_trials):
        trial_data = data_raw[trial_idx]

        filtered = bandpass_filter(trial_data)

        bl = filtered[:, :baseline_len]
        baseline_mean = np.mean(bl, axis=1, keepdims=True)
        baseline_std = np.std(bl, axis=1, keepdims=True)

        corrected = (filtered[:, baseline_len:] - baseline_mean) / (baseline_std + 1e-8)
        corrected = np.nan_to_num(corrected.astype(np.float32))

        valence = labels_raw[trial_idx, 0]
        arousal = labels_raw[trial_idx, 1]
        label = discretize_label(valence, arousal)

        segs = segment_trial(corrected)
        if not segs:
            continue

        segments_list.extend(segs)
        seg_labels_list.extend([label] * len(segs))
        segs_per_trial_list.append(len(segs))

    if not segments_list:
        print("   no valid segments, skipping")
        return

    X = np.array(segments_list, dtype=np.float32)
    y = np.array(seg_labels_list, dtype=np.int32)
    spt = np.array(segs_per_trial_list, dtype=np.int32)

    subj_id = os.path.splitext(os.path.basename(filepath))[0]
    out_name = f"{subj_id}_deap.mat"

    savemat(
        os.path.join(OUTPUT_DIR, out_name),
        {'seg_X': X, 'seg_y': y, 'segs_per_trial': spt},
        do_compression=True
    )

    print(f"   Saved: {out_name}, segments: {X.shape[0]}, shape: {X.shape[1:]}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filenames = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.dat') and f.startswith('s')])
    print(f"Found {len(filenames)} subjects")
    for fname in filenames:
        process_subject(os.path.join(DATA_DIR, fname))
    print("DEAP preprocessing done.")

if __name__ == '__main__':
    main()
