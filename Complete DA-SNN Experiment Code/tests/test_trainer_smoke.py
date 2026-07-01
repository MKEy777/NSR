import json

import numpy as np
from scipy.io import savemat

from common.data_loader import build_splits, load_feature_bundle, make_loso_splits, make_random_splits
from common.trainer import ExperimentConfig, run_experiment


def test_run_experiment_smoke_writes_summary(tmp_path):
    feature_file = tmp_path / "features.mat"
    savemat(
        feature_file,
        {
            "features": np.random.default_rng(1).normal(size=(12, 4, 8, 9)).astype(np.float32),
            "labels": np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2], dtype=np.int64),
            "subject_id": np.repeat(np.arange(4), 3).astype(np.int64),
            "trial_id": np.tile(np.arange(3), 4).astype(np.int64),
            "session_id": np.zeros(12, dtype=np.int64),
        },
    )
    bundle = load_feature_bundle(feature_file, require_metadata=True)
    splits = make_random_splits(bundle, test_size=0.25, seed=42)
    config = ExperimentConfig(
        dataset="seed",
        model_name="da_snn",
        protocol="random_80_20",
        seed=42,
        max_epochs=1,
        batch_size=4,
        output_dir=tmp_path / "out",
    )

    summary = run_experiment(bundle, splits, config)
    split_json = tmp_path / "out" / "seed" / "random_80_20" / "da_snn" / "seed_42" / "seed_42.json"
    payload = json.loads(split_json.read_text(encoding="utf-8"))

    assert summary["count"] == 1
    assert "accuracy_mean" in summary
    assert payload["train_count"] == 9
    assert payload["val_count"] == payload["test_count"] == 3
    assert (tmp_path / "out" / "seed" / "random_80_20" / "da_snn" / "seed_42" / "summary.json").exists()


def test_run_experiment_loso_writes_complete_split_result_fields(tmp_path):
    feature_file = tmp_path / "features.mat"
    savemat(
        feature_file,
        {
            "features": np.random.default_rng(2).normal(size=(12, 4, 8, 9)).astype(np.float32),
            "labels": np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2], dtype=np.int64),
            "subject_id": np.repeat(np.arange(4), 3).astype(np.int64),
            "trial_id": np.tile(np.arange(3), 4).astype(np.int64),
            "session_id": np.zeros(12, dtype=np.int64),
        },
    )
    bundle = load_feature_bundle(feature_file, require_metadata=True)
    splits = make_loso_splits(bundle)
    config = ExperimentConfig(
        dataset="seed",
        model_name="da_snn",
        protocol="loso",
        seed=42,
        max_epochs=1,
        batch_size=4,
        output_dir=tmp_path / "out",
        dry_run=True,
    )

    run_experiment(bundle, splits, config)

    split_json = tmp_path / "out" / "seed" / "loso" / "da_snn" / "seed_42" / "subject_00.json"
    runs_csv = tmp_path / "out" / "seed" / "loso" / "da_snn" / "seed_42" / "runs.csv"
    payload = json.loads(split_json.read_text(encoding="utf-8"))
    expected_keys = {
        "precision",
        "sensitivity",
        "specificity",
        "best_val_precision",
        "best_val_sensitivity",
        "best_val_specificity",
        "best_epoch",
        "stopped_epoch",
        "epochs_ran",
        "early_stopped",
        "train_subjects",
        "val_subjects",
        "test_subjects",
    }

    assert expected_keys.issubset(payload)
    assert payload["val_subjects"] == payload["test_subjects"] == [0]
    assert set(payload["train_subjects"]) == {1, 2, 3}
    assert runs_csv.exists()


def test_run_experiment_respects_max_splits_without_dry_run(tmp_path):
    feature_file = tmp_path / "features.mat"
    savemat(
        feature_file,
        {
            "features": np.random.default_rng(4).normal(size=(12, 4, 8, 9)).astype(np.float32),
            "labels": np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2], dtype=np.int64),
            "subject_id": np.repeat(np.arange(4), 3).astype(np.int64),
            "trial_id": np.tile(np.arange(3), 4).astype(np.int64),
            "session_id": np.zeros(12, dtype=np.int64),
        },
    )
    bundle = load_feature_bundle(feature_file, require_metadata=True)
    splits = make_loso_splits(bundle)
    config = ExperimentConfig(
        dataset="seed",
        model_name="da_snn",
        protocol="loso",
        seed=42,
        max_epochs=1,
        max_splits=2,
        batch_size=4,
        output_dir=tmp_path / "out",
    )

    summary = run_experiment(bundle, splits, config)

    assert summary["count"] == 2
    assert (tmp_path / "out" / "seed" / "loso" / "da_snn" / "seed_42" / "subject_00.json").exists()
    assert (tmp_path / "out" / "seed" / "loso" / "da_snn" / "seed_42" / "subject_01.json").exists()
    assert not (tmp_path / "out" / "seed" / "loso" / "da_snn" / "seed_42" / "subject_02.json").exists()


def test_run_experiment_subject_80_20_writes_subject_group_result(tmp_path):
    subject_count = 12
    samples_per_subject = 2
    feature_file = tmp_path / "features.mat"
    savemat(
        feature_file,
        {
            "features": np.random.default_rng(3).normal(size=(subject_count * samples_per_subject, 4, 8, 9)).astype(np.float32),
            "labels": np.tile(np.array([0, 1], dtype=np.int64), subject_count),
            "subject_id": np.repeat(np.arange(subject_count), samples_per_subject).astype(np.int64),
            "trial_id": np.tile(np.arange(samples_per_subject), subject_count).astype(np.int64),
            "session_id": np.zeros(subject_count * samples_per_subject, dtype=np.int64),
        },
    )
    bundle = load_feature_bundle(feature_file, require_metadata=True)
    splits = build_splits(
        "subject_80_20",
        bundle,
        seed=42,
        dataset="seed",
        split_dir=tmp_path / "splits",
    )
    config = ExperimentConfig(
        dataset="seed",
        model_name="da_snn",
        protocol="subject_80_20",
        seed=42,
        max_epochs=1,
        batch_size=4,
        output_dir=tmp_path / "out",
        dry_run=True,
    )

    run_experiment(bundle, splits, config)

    split_json = tmp_path / "out" / "seed" / "subject_80_20" / "da_snn" / "seed_42" / "subject_group_00.json"
    payload = json.loads(split_json.read_text(encoding="utf-8"))

    assert payload["split"] == "subject_group_00"
    assert payload["val_subjects"] == payload["test_subjects"]
    assert set(payload["train_subjects"]).isdisjoint(payload["test_subjects"])
    assert {"accuracy", "precision", "sensitivity", "specificity"}.issubset(payload)
