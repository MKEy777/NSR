"""T3 robustness: raw-EEG noise injection + PSE/LDS feature extraction.

For each (noise_type, NL) tag we

1. Load a sliced session mat (produced by ``preprocessing_seed.py``).
2. Estimate per-channel signal sigma on the clean session.
3. Inject noise **in memory** (no intermediate mat is written).
4. Run the exact same PSE + spatial mapping + LDS smoothing pipeline as
   ``extract_features.py`` (imported from ``feature_core``).
5. Aggregate across all sessions and ``savemat`` one bundle per tag as

       Feature_PowerSpectrumEntropy_LDS_Smoothed_SEED/
           all_features_pse_lds_smoothed_<TAG>.mat

Clean features are NOT re-generated here; the original
``extract_features.py`` still handles the untagged bundle.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import numpy as np
from scipy.io import loadmat, savemat

from feature_core import (
    FS,
    TOTAL_FRAMES,
    N_CHANNELS,
    calculate_power_spectrum_entropy,
    reshape_to_4x8x9,
    apply_lds_smoothing,
)
from noise_utils import NOISE_MAKERS, estimate_channel_sigma


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_WORKERS = 24

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "PerSession_4sZScore_62x800"
OUTPUT_DIR = BASE_DIR / "Feature_PowerSpectrumEntropy_LDS_Smoothed_SEED"

NL_LEVELS: Tuple[float, ...] = (0.01, 0.03, 0.05, 0.08, 0.10, 0.125)
NOISE_TYPES: Tuple[str, ...] = ("gaussian", "drift", "emg")

# stable numeric ids for seed derivation (never reorder / remove)
NOISE_TYPE_IDS = {"gaussian": 0, "drift": 1, "emg": 2}


def _nl_slug(nl: float) -> str:
    """Format 0.05 -> 'NL0p05', 0.125 -> 'NL0p125'."""
    return "NL" + ("%g" % nl).replace(".", "p")


def build_tag_specs() -> List[Tuple[str, str, float, int]]:
    """Return list of (tag, noise_type, nl, level_idx) for every {type, NL}."""
    specs: List[Tuple[str, str, float, int]] = []
    for ntype in NOISE_TYPES:
        for lvl_idx, nl in enumerate(NL_LEVELS):
            tag = f"{ntype}_{_nl_slug(nl)}"
            specs.append((tag, ntype, float(nl), lvl_idx))
    return specs


TAG_SPECS = build_tag_specs()


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

def make_seed(subject_id: int, session_id: int, noise_type_id: int, level_idx: int) -> int:
    """Deterministic 63-bit seed for (subject, session, noise_type, level).

    Using a hash makes the mapping stable across code refactors and avoids
    accidental collisions from any simple arithmetic scheme.
    """
    key = f"T3|{subject_id}|{session_id}|{noise_type_id}|{level_idx}".encode()
    h = hashlib.blake2b(key, digest_size=8).digest()
    # Force into positive int64 range.
    return int.from_bytes(h, byteorder="big", signed=False) & 0x7FFFFFFFFFFFFFFF


# ---------------------------------------------------------------------------
# Per-file worker
# ---------------------------------------------------------------------------

def _parse_ids(filename: str) -> Tuple[int, int]:
    subject_match = re.search(r"subject_(\d+)", filename)
    session_match = re.search(r"session_(\d+)", filename)
    subject_value = int(subject_match.group(1)) if subject_match else 0
    session_value = int(session_match.group(1)) if session_match else 0
    return subject_value, session_value


def process_file_with_noise(file_path: str, noise_type: str, nl: float, level_idx: int):
    """Load a sliced session, inject noise, run PSE+LDS. Returns aggregated arrays."""
    filename = os.path.basename(file_path)
    print(f"[{noise_type}|nl={nl}] Processing: {filename}")
    mat = loadmat(file_path)
    X_raw = mat["seg_X"]          # [N, 4, 62, 200]
    y_raw = mat["seg_y"].flatten()
    segs_per_trial = mat["segs_per_trial"].flatten()

    subject_value, session_value = _parse_ids(filename)

    # Per-session, per-tag deterministic RNG.
    seed = make_seed(subject_value, session_value, NOISE_TYPE_IDS[noise_type], level_idx)
    rng = np.random.default_rng(seed)

    # Estimate channel-wise sigma on the clean signal, then inject noise.
    sigma_ch = estimate_channel_sigma(X_raw)
    maker = NOISE_MAKERS[noise_type]
    X_noisy = maker(X_raw.astype(np.float32, copy=False), sigma_ch, nl, rng)

    # --- Below mirrors extract_features.process_file_robust exactly ---
    boundaries = np.cumsum(segs_per_trial)
    full_boundaries = np.concatenate(([0], boundaries))
    num_trials = len(segs_per_trial)

    all_session_features = []
    all_session_labels = []
    all_subject_ids = []
    all_trial_ids = []
    all_session_ids = []

    for i in range(num_trials):
        start_idx, end_idx = int(full_boundaries[i]), int(full_boundaries[i + 1])
        if start_idx >= end_idx:
            continue
        trial_label = y_raw[start_idx]
        trial_raw_data = X_noisy[start_idx:end_idx]

        trial_features_list = []
        for j in range(trial_raw_data.shape[0]):
            seg4x62x200 = trial_raw_data[j]
            feats_4x62 = np.zeros((TOTAL_FRAMES, N_CHANNELS), dtype=np.float32)
            for t in range(TOTAL_FRAMES):
                for ch in range(N_CHANNELS):
                    feats_4x62[t, ch] = calculate_power_spectrum_entropy(seg4x62x200[t, ch, :])
            reshaped_feat = reshape_to_4x8x9(feats_4x62)
            trial_features_list.append(reshaped_feat)

        if not trial_features_list:
            continue

        trial_features = np.stack(trial_features_list)
        smoothed_features = apply_lds_smoothing(trial_features)
        all_session_features.append(smoothed_features)
        n_windows = len(trial_features_list)
        all_session_labels.extend([trial_label] * n_windows)
        all_subject_ids.extend([subject_value] * n_windows)
        all_trial_ids.extend([i + 1] * n_windows)
        all_session_ids.extend([session_value] * n_windows)

    if not all_session_features:
        empty = np.array([])
        return empty, empty, empty, empty, empty

    final_features = np.vstack(all_session_features)
    final_labels = np.array(all_session_labels, dtype=np.int32)
    return (
        final_features,
        final_labels,
        np.array(all_subject_ids, dtype=np.int64),
        np.array(all_trial_ids, dtype=np.int64),
        np.array(all_session_ids, dtype=np.int64),
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def run_single_tag(tag: str, noise_type: str, nl: float, level_idx: int,
                   file_paths: List[str], workers: int) -> None:
    print(f"\n=== TAG {tag} ({noise_type}, NL={nl}) — {len(file_paths)} sessions ===")
    start_time = time.time()

    features_list, labels_list = [], []
    subject_ids_list, trial_ids_list, session_ids_list= [], [], []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        future_to_path = {
            executor.submit(process_file_with_noise, path, noise_type, nl, level_idx): path
            for path in file_paths
        }
        for future in as_completed(future_to_path):
            path = future_to_path[future]
            try:
                features, labels, subject_ids, trial_ids, session_ids = future.result()
                if features.size > 0:
                    features_list.append(features)
                    labels_list.append(labels)
                    subject_ids_list.append(subject_ids)
                    trial_ids_list.append(trial_ids)
                    session_ids_list.append(session_ids)
                print(f"   ✓ [{tag}] {os.path.basename(path)}")
            except Exception as exc:  # pragma: no cover - defensive
                print(f"   ✗ [{tag}] {os.path.basename(path)} exception: {exc}")

    dt = time.time() - start_time
    print(f"[{tag}] parallel processing finished in {dt:.2f}s")

    if not features_list:
        print(f"[{tag}] No features produced. Skipping savemat.")
        return

    X_all = np.vstack(features_list)
    y_all = np.concatenate(labels_list).astype(np.int64)
    subject_all = np.concatenate(subject_ids_list).astype(np.int64)
    trial_all = np.concatenate(trial_ids_list).astype(np.int64)
    session_all = np.concatenate(session_ids_list).astype(np.int64)

    print(f"[{tag}] Total samples aggregated: {len(X_all)}")

    output_filename = f"all_features_pse_lds_smoothed_{tag}.mat"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    savemat(
        output_path,
        {
            "features": X_all,
            "labels": y_all,
            "subject_id": subject_all,
            "trial_id": trial_all,
            "session_id": session_all,
        },
        do_compression=True,
    )
    print(f"[{tag}] saved -> {output_path}")

    # Free memory before moving to next tag.
    del features_list, labels_list, subject_ids_list, trial_ids_list, session_ids_list
    del X_all, y_all, subject_all, trial_all, session_all
    gc.collect()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="T3 raw-EEG noise injection + PSE/LDS feature extraction")
    p.add_argument(
        "--noise-type",
        choices=NOISE_TYPES,
        default=None,
        help="Shortcut: run all 6 NL levels for one noise type. Overrides --only-tags when set.",
    )
    p.add_argument(
        "--only-tags",
        type=str,
        default="",
        help="Comma-separated tag subset (e.g. gaussian_NL0p05,drift_NL0p10). Empty = all 18 tags.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned TAG_SPECS and expected output paths without processing.",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=MAX_WORKERS,
        help=f"Parallel workers per tag (default {MAX_WORKERS}).",
    )
    return p.parse_args()


def _filter_specs(only_tags: str):
    if not only_tags.strip():
        return TAG_SPECS
    wanted = {t.strip() for t in only_tags.split(",") if t.strip()}
    filtered = [s for s in TAG_SPECS if s[0] in wanted]
    unknown = wanted - {s[0] for s in TAG_SPECS}
    if unknown:
        raise SystemExit(f"Unknown tag(s): {sorted(unknown)}. "
                         f"Valid tags: {[s[0] for s in TAG_SPECS]}")
    return filtered


def main() -> None:
    args = parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.noise_type is not None:
        specs = [s for s in TAG_SPECS if s[1] == args.noise_type]
        if args.only_tags.strip():
            print(f"[warn] --noise-type={args.noise_type} overrides --only-tags")
    else:
        specs = _filter_specs(args.only_tags)

    print(f"Planned {len(specs)} tag(s):")
    for tag, ntype, nl, lvl_idx in specs:
        out = OUTPUT_DIR / f"all_features_pse_lds_smoothed_{tag}.mat"
        print(f"  - tag={tag:<20s} type={ntype:<8s} nl={nl:<6g} level_idx={lvl_idx}  -> {out}")

    if args.dry_run:
        print("\n[dry-run] not processing.")
        return

    file_paths = [os.path.join(INPUT_DIR, f)
                  for f in sorted(os.listdir(INPUT_DIR))
                  if f.endswith(".mat")]
    if not file_paths:
        raise SystemExit(f"No .mat files under {INPUT_DIR}")

    global_start = time.time()
    for tag, ntype, nl, lvl_idx in specs:
        run_single_tag(tag, ntype, nl, lvl_idx, file_paths, workers=args.workers)
    print(f"\nAll tags done in {time.time() - global_start:.2f}s")


if __name__ == "__main__":
    main()