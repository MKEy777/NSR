import run_experiments


def test_dry_run_uses_synthetic_data_when_feature_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_experiments.py",
            "--dataset",
            "seed",
            "--model",
            "da_snn",
            "--protocol",
            "loso",
            "--max-epochs",
            "1",
            "--dry-run",
            "--feature-file",
            str(tmp_path / "missing.mat"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    run_experiments.main()

    assert (tmp_path / "out" / "seed" / "loso" / "summary_all.csv").exists()



def test_dry_run_all_models_subject_protocol_uses_synthetic_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "run_experiments.py",
            "--dataset",
            "deap",
            "--model",
            "all",
            "--protocol",
            "subject_80_20",
            "--max-epochs",
            "1",
            "--dry-run",
            "--feature-file",
            str(tmp_path / "missing.mat"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
    )

    run_experiments.main()

    assert (tmp_path / "out" / "deap" / "subject_80_20" / "summary_all.csv").exists()
