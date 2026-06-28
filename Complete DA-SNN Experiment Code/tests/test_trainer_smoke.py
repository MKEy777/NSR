import numpy as np
from scipy.io import savemat

from common.data_loader import load_feature_bundle, make_random_splits
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

    assert summary["count"] == 1
    assert "accuracy_mean" in summary
    assert (tmp_path / "out" / "seed" / "random_80_20" / "da_snn" / "seed_42" / "summary.json").exists()
