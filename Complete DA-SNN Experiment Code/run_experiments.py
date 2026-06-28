from __future__ import annotations

import argparse
from pathlib import Path

from common.config import DATASET_CONFIGS, resolve_feature_file
import numpy as np

from common.data_loader import DatasetBundle, build_splits, load_feature_bundle
from common.metrics import write_csv
from common.model_builder import MODEL_NAMES
from common.trainer import ExperimentConfig, run_experiment


def parse_args():
    parser = argparse.ArgumentParser(description="Run DA-SNN revision experiments.")
    parser.add_argument("--dataset", choices=DATASET_CONFIGS.keys(), required=True)
    parser.add_argument("--model", choices=(*MODEL_NAMES, "all"), required=True)
    parser.add_argument("--protocol", choices=("loso", "subject_80_20", "random_80_20"), required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--feature-file", default=None)
    parser.add_argument("--output-dir", default="experiment_outputs")
    parser.add_argument("--split-dir", default="splits")
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--allow-nonstratified-subject-split", action="store_true")
    parser.add_argument("--standard-minmax", action="store_true")
    parser.add_argument("--noise-type", choices=("none", "gaussian", "uniform", "mask"), default="none")
    parser.add_argument("--noise-level", type=float, default=0.0)
    parser.add_argument("--no-depthwise-separable", action="store_true")
    parser.add_argument("--no-dsgm", action="store_true")
    parser.add_argument("--no-ttfs-encoder", action="store_true")
    parser.add_argument("--no-dynamic-window", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def make_synthetic_bundle(dataset: str) -> DatasetBundle:
    cfg = DATASET_CONFIGS[dataset]
    samples_per_subject = max(cfg.num_classes * 5, 20)
    subject_count = 3
    n_samples = samples_per_subject * subject_count
    rng = np.random.default_rng(123)
    features = rng.normal(size=(n_samples, *cfg.input_shape)).astype(np.float32)
    labels = np.tile(np.arange(cfg.num_classes, dtype=np.int64), int(np.ceil(n_samples / cfg.num_classes)))[:n_samples]
    subject_id = np.repeat(np.arange(subject_count, dtype=np.int64), samples_per_subject)
    trial_id = np.tile(np.arange(samples_per_subject, dtype=np.int64), subject_count)
    session_id = np.zeros(n_samples, dtype=np.int64)
    return DatasetBundle(features=features, labels=labels, subject_id=subject_id, trial_id=trial_id, session_id=session_id)


def main() -> None:
    args = parse_args()
    model_names = MODEL_NAMES if args.model == "all" else (args.model,)
    require_metadata = args.protocol in {"loso", "subject_80_20"}
    feature_path = resolve_feature_file(args.dataset, args.feature_file)
    try:
        bundle = load_feature_bundle(feature_path, dataset=args.dataset, require_metadata=require_metadata)
    except (OSError, FileNotFoundError, ValueError):
        if not args.dry_run:
            raise
        print(f"[dry-run] Using synthetic {args.dataset} data because {feature_path} is unavailable or lacks metadata.") 
        bundle = make_synthetic_bundle(args.dataset)
    summaries = []
    for seed in args.seeds:
        splits = build_splits(
            args.protocol,
            bundle,
            seed=seed,
            test_size=args.test_size,
            dataset=args.dataset,
            split_dir=args.split_dir,
            strict_stratified=not args.allow_nonstratified_subject_split,
        )
        for model_name in model_names:
            config = ExperimentConfig(
                dataset=args.dataset,
                model_name=model_name,
                protocol=args.protocol,
                seed=seed,
                max_epochs=args.max_epochs,
                batch_size=args.batch_size,
                output_dir=Path(args.output_dir),
                standard_minmax=args.standard_minmax,
                noise_type=args.noise_type,
                noise_level=args.noise_level,
                use_depthwise_separable=not args.no_depthwise_separable,
                use_dsgm=not args.no_dsgm,
                use_ttfs_encoder=not args.no_ttfs_encoder,
                use_dynamic_window=not args.no_dynamic_window,
                dry_run=args.dry_run,
            )
            summaries.append(run_experiment(bundle, splits, config))
    write_csv(Path(args.output_dir) / args.dataset / args.protocol / "summary_all.csv", summaries)
    print(f"Completed {len(summaries)} experiment summaries.")


if __name__ == "__main__":
    main()
