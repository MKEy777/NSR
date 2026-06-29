import scipy.io as sio
import numpy as np
import os
from scipy import signal as sig
from scipy.io import savemat
from pathlib import Path

FS = 128
WINDOW_S = 9
STEP_S = 9
BASELINE_S = 61

BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "DREAMER.mat"
OUTPUT_DIR = BASE_DIR / "PerSubject_9sZScore_14x1152"

def unwrap(x):
    while isinstance(x, np.ndarray) and x.dtype == object and x.size == 1:
        x = x[0, 0]
    return x

def label(v, a):
    return (v >= 3) * 2 + (a >= 3)

def bandpass(x):
    nyq = 0.5 * FS
    b, a = sig.butter(4, [1 / nyq, 50 / nyq], btype='band')
    return sig.filtfilt(b, a, x, axis=0).astype(np.float32)

def segment(x):
    win = int(WINDOW_S * FS)
    step = int(STEP_S * FS)

    T, C = x.shape
    segs = []

    if T < win:
        return segs

    n = (T - win) // step + 1

    for i in range(n):
        s = x[i * step:i * step + win, :]   

        s = s.reshape(9, FS, C)
        s = np.transpose(s, (0, 2, 1))  

        segs.append(s.astype(np.float32))

    return segs

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    raw = sio.loadmat(INPUT_PATH)
    dreamer = raw["DREAMER"]

    subjects = unwrap(dreamer["Data"])

    print("Subjects:", subjects.shape)

    for si in range(subjects.shape[1]):

        subj = subjects[0, si]
        eeg = unwrap(subj["EEG"])

        baselines = unwrap(eeg["baseline"])
        stimuli = unwrap(eeg["stimuli"])

        valence_all = unwrap(subj["ScoreValence"])
        arousal_all = unwrap(subj["ScoreArousal"])

        X_all, y_all, seg_cnt = [], [], []

        for ti in range(18):

            bl = unwrap(baselines[ti, 0]).astype(np.float32)  
            st = unwrap(stimuli[ti, 0]).astype(np.float32)

            assert bl.shape[1] == 14
            assert st.shape[1] == 14

            bl = bandpass(bl)
            st = bandpass(st)

            bl_cut = bl[:int(BASELINE_S * FS), :]

            mean = np.mean(bl_cut, axis=0, keepdims=True)
            std = np.std(bl_cut, axis=0, keepdims=True)
            std = np.maximum(std, 1e-6)

            st = (st - mean) / std
            st = np.nan_to_num(st).astype(np.float32)

            v = float(unwrap(valence_all)[ti, 0])
            a = float(unwrap(arousal_all)[ti, 0])
            y = label(v, a)

            segs = segment(st)

            if len(segs) == 0:
                continue

            X_all.extend(segs)
            y_all.extend([y] * len(segs))
            seg_cnt.append(len(segs))

        assert sum(seg_cnt) == len(y_all)

        X = np.array(X_all, dtype=np.float32)
        y = np.array(y_all, dtype=np.int32)

        out = f"subject_{si+1:02d}.mat"

        savemat(
            os.path.join(OUTPUT_DIR, out),
            {
                "seg_X": X,
                "seg_y": y,
                "segs_per_trial": np.array(seg_cnt)
            }
        )

        print(f"[OK] subject {si+1} | {X.shape}")

if __name__ == "__main__":
    main()
