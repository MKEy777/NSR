import numpy as np
import pytest
from scipy.io import savemat
import importlib.util
from pathlib import Path

from common.data_loader import (
    DatasetBundle,
    build_splits,
    load_feature_bundle,
    make_loso_splits,
    make_random_splits,
    make_subject_stratified_splits,
)


def write_mat(path, include_metadata=True):
    payload = {
        "features": np.random.default_rng(0).normal(size=(12, 4, 8, 9)).astype(np.float32),
        "labels": np.array([0, 1, 0, 1] * 3, dtype=np.int64),
    }
    if include_metadata:
        payload.update(
            {
                "subject_id": np.repeat(np.arange(3), 4).astype(np.int64),
                "trial_id": np.tile(np.arange(4), 3).astype(np.int64),
                "session_id": np.zeros(12, dtype=np.int64),
            }
        )
    savemat(path, payload)


def test_load_feature_bundle_requires_metadata_for_group_protocols(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file, include_metadata=False)

    with pytest.raises(ValueError, match="subject_id.*trial_id"):
        load_feature_bundle(feature_file, require_metadata=True)


def test_loso_splits_hold_out_each_subject(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file)
    bundle = load_feature_bundle(feature_file, require_metadata=True)

    splits = make_loso_splits(bundle)

    assert len(splits) == 3
    for split in splits:
        train_subjects = set(bundle.subject_id[split.train_indices])
        test_subjects = set(bundle.subject_id[split.test_indices])
        assert len(test_subjects) == 1
        assert train_subjects.isdisjoint(test_subjects)


def test_subject_stratified_splits_keep_each_subject_separate(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file)
    bundle = load_feature_bundle(feature_file, require_metadata=True)

    splits = make_subject_stratified_splits(bundle, test_size=0.5, seed=7)

    assert len(splits) == 3
    for split in splits:
        assert set(bundle.subject_id[split.train_indices]) == set(bundle.subject_id[split.test_indices])
        assert len(split.train_indices) > 0
        assert len(split.test_indices) > 0


def test_random_splits_do_not_require_metadata(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file, include_metadata=False)
    bundle = load_feature_bundle(feature_file, require_metadata=False)

    split = make_random_splits(bundle, test_size=0.25, seed=42)[0]

    assert len(split.train_indices) == 9
    assert len(split.test_indices) == 3


def test_random_splits_are_saved_and_reused(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file, include_metadata=False)
    bundle = load_feature_bundle(feature_file, require_metadata=False)

    first = build_splits(
        "random_80_20",
        bundle,
        seed=42,
        dataset="seed",
        split_dir=tmp_path / "splits",
    )[0]
    split_file = tmp_path / "splits" / "seed" / "random_80_20" / "seed_42.npz"
    assert split_file.exists()

    second = build_splits(
        "random_80_20",
        bundle,
        seed=42,
        dataset="seed",
        split_dir=tmp_path / "splits",
    )[0]

    np.testing.assert_array_equal(first.train_indices, second.train_indices)
    np.testing.assert_array_equal(first.test_indices, second.test_indices)


def test_subject_splits_do_not_cross_trials_between_train_and_test(tmp_path):
    feature_file = tmp_path / "features.mat"
    write_mat(feature_file)
    bundle = load_feature_bundle(feature_file, require_metadata=True)

    splits = make_subject_stratified_splits(bundle, test_size=0.5, seed=7)

    for split in splits:
        train_trials = set(bundle.trial_id[split.train_indices])
        test_trials = set(bundle.trial_id[split.test_indices])
        assert train_trials.isdisjoint(test_trials)


def test_subject_stratified_splits_fail_when_a_class_has_one_trial():
    features = np.random.default_rng(2).normal(size=(4, 4, 8, 9)).astype(np.float32)
    bundle = DatasetBundle(
        features=features,
        labels=np.array([0, 0, 0, 1], dtype=np.int64),
        subject_id=np.zeros(4, dtype=np.int64),
        trial_id=np.arange(4, dtype=np.int64),
        session_id=np.zeros(4, dtype=np.int64),
    )

    with pytest.raises(ValueError, match="subject_00.*cannot be stratified"):
        make_subject_stratified_splits(bundle, test_size=0.5, seed=7)


def test_subject_splits_allow_explicit_nonstratified_fallback():
    features = np.random.default_rng(2).normal(size=(4, 4, 8, 9)).astype(np.float32)
    bundle = DatasetBundle(
        features=features,
        labels=np.array([0, 0, 0, 1], dtype=np.int64),
        subject_id=np.zeros(4, dtype=np.int64),
        trial_id=np.arange(4, dtype=np.int64),
        session_id=np.zeros(4, dtype=np.int64),
    )

    split = make_subject_stratified_splits(bundle, test_size=0.5, seed=7, strict_stratified=False)[0]

    assert len(split.train_indices) == 2
    assert len(split.test_indices) == 2


def test_subject_split_cache_does_not_bypass_strict_stratified(tmp_path):
    features = np.random.default_rng(2).normal(size=(4, 4, 8, 9)).astype(np.float32)
    bundle = DatasetBundle(
        features=features,
        labels=np.array([0, 0, 0, 1], dtype=np.int64),
        subject_id=np.zeros(4, dtype=np.int64),
        trial_id=np.arange(4, dtype=np.int64),
        session_id=np.zeros(4, dtype=np.int64),
    )
    split_dir = tmp_path / "splits"

    build_splits(
        "subject_80_20",
        bundle,
        seed=7,
        dataset="deap",
        split_dir=split_dir,
        strict_stratified=False,
    )

    with pytest.raises(ValueError, match="subject_00.*cannot be stratified"):
        build_splits(
            "subject_80_20",
            bundle,
            seed=7,
            dataset="deap",
            split_dir=split_dir,
            strict_stratified=True,
        )


def test_subject_stratified_splits_support_non_contiguous_labels():
    features = np.random.default_rng(3).normal(size=(4, 4, 8, 9)).astype(np.float32)
    bundle = DatasetBundle(
        features=features,
        labels=np.array([1, 3, 1, 3], dtype=np.int64),
        subject_id=np.zeros(4, dtype=np.int64),
        trial_id=np.arange(4, dtype=np.int64),
        session_id=np.zeros(4, dtype=np.int64),
    )

    split = make_subject_stratified_splits(bundle, test_size=0.5, seed=7)[0]

    assert set(bundle.labels[split.train_indices]) == {1, 3}
    assert set(bundle.labels[split.test_indices]) == {1, 3}


def test_dreamer_extraction_preserves_original_trial_boundaries(tmp_path, monkeypatch):
    module_path = Path(__file__).resolve().parents[1] / "Preprocessing" / "DREAMER" / "extraction.py"
    spec = importlib.util.spec_from_file_location("dreamer_extraction_for_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    calls = []

    def fake_lds(features, n_iter=3):
        calls.append(features.shape[0])
        return features

    monkeypatch.setattr(module, "calculate_power_spectrum_entropy", lambda _x: 0.0)
    monkeypatch.setattr(module, "reshape_to_9x4x5", lambda x: np.zeros((module.TOTAL_FRAMES, module.GRID_ROWS, module.GRID_COLS), dtype=np.float32))
    monkeypatch.setattr(module, "apply_lds", fake_lds)

    feature_file = tmp_path / "subject_01.mat"
    savemat(
        feature_file,
        {
            "seg_X": np.zeros((3, module.TOTAL_FRAMES, module.N_CHANNELS, module.FS), dtype=np.float32),
            "seg_y": np.array([0, 0, 1], dtype=np.int64),
            "segs_per_trial": np.array([2, 1], dtype=np.int64),
        },
    )

    _x, y, subject_id, trial_id, session_id = module.process_file(feature_file)

    np.testing.assert_array_equal(y, np.array([0, 0, 1]))
    np.testing.assert_array_equal(subject_id, np.array([1, 1, 1]))
    np.testing.assert_array_equal(trial_id, np.array([1, 1, 2]))
    np.testing.assert_array_equal(session_id, np.array([0, 0, 0]))
    assert calls == [2, 1]


def test_preprocessing_scripts_are_import_safe_from_any_working_directory(tmp_path, monkeypatch):
    script_paths = [
        Path("Preprocessing/SEED/processing_seed.py"),
        Path("Preprocessing/SEED/extract_features.py"),
        Path("Preprocessing/SEEDIV/preprocessing.py"),
        Path("Preprocessing/SEEDIV/extraction.py"),
        Path("Preprocessing/SEEDV/preprocessing.py"),
        Path("Preprocessing/SEEDV/extraction.py"),
        Path("Preprocessing/DEAP/preprocessing.py"),
        Path("Preprocessing/DEAP/extraction.py"),
        Path("Preprocessing/DREAMER/preprocessing.py"),
        Path("Preprocessing/DREAMER/extraction.py"),
    ]
    project_dir = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    for index, relative_path in enumerate(script_paths):
        module_path = project_dir / relative_path
        spec = importlib.util.spec_from_file_location(f"preprocessing_script_{index}", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for attr in ("INPUT_DIR", "OUTPUT_DIR", "RAW_DATA_DIR", "DATA_DIR", "INPUT_PATH"):
            if hasattr(module, attr):
                assert Path(getattr(module, attr)).is_absolute()

    assert not any(tmp_path.iterdir())
