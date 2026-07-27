from __future__ import annotations

import argparse
from pathlib import Path

from common.config import DATASET_CONFIGS, resolve_feature_file
import numpy as np
import torch

from common.data_loader import DatasetBundle, build_splits, load_feature_bundle
from common.metrics import write_csv
from common.model_builder import MODEL_NAMES
from common.trainer import ExperimentConfig, run_experiment


def parse_args():
    parser = argparse.ArgumentParser(description="Run DA-SNN revision experiments.")
    parser.add_argument("--dataset", choices=DATASET_CONFIGS.keys(), required=True)
    parser.add_argument("--model", choices=(*MODEL_NAMES, "all"), required=True)
    parser.add_argument("--exclude", nargs="*", default=None, choices=MODEL_NAMES)
    parser.add_argument("--protocol", choices=("loso", "subject_80_20", "random_80_20"), required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--feature-file", default=None)
    parser.add_argument("--output-dir", default="experiment_outputs")
    parser.add_argument("--split-dir", default="splits")
    parser.add_argument("--max-epochs", type=int, default=200)
    parser.add_argument("--max-splits", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--allow-nonstratified-subject-split", action="store_true")
    parser.add_argument("--standard-minmax", action="store_true")
    parser.add_argument("--no-lds", action="store_true",
                        help="Use PSE features without LDS smoothing (loads *_no_lds.mat)")
    parser.add_argument(
        "--feature-tag",
        default="",
        help=(
            "Optional single feature-bundle tag (e.g. gaussian_NL0p05). When set, "
            "loads all_features_pse_lds_smoothed_<TAG>.mat produced by "
            "Preprocessing/SEED/extract_features_noise.py; empty = clean bundle. "
            "Ignored when --noise is specified."
        ),
    )
    parser.add_argument(
        "--noise",
        choices=("gaussian", "drift", "emg"),
        default=None,
        help=(
            "T3 noise sweep. When set, expands to 6 NL levels "
            "{0.01,0.03,0.05,0.08,0.10,0.125} and runs one experiment per tag, "
            "loading all_features_pse_lds_smoothed_<noise>_NL<slug>.mat for each."
        ),
    )
    parser.add_argument("--no-depthwise-separable", action="store_true")
    parser.add_argument("--no-dsgm", action="store_true")
    parser.add_argument("--no-ttfs-encoder", action="store_true")
    parser.add_argument("--no-dynamic-window", action="store_true")
    parser.add_argument("--replace-dsgm-with-conv", action="store_true",
                        help="Replace DSGM with a plain Conv2d+BN+ReLU of equivalent params (ablation control)")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def make_synthetic_bundle(dataset: str) -> DatasetBundle:
    cfg = DATASET_CONFIGS[dataset]
    samples_per_subject = max(cfg.num_classes * 5, 20)
    subject_count = 5
    n_samples = samples_per_subject * subject_count
    rng = np.random.default_rng(123)
    features = rng.normal(size=(n_samples, *cfg.input_shape)).astype(np.float32)
    labels = np.tile(np.arange(cfg.num_classes, dtype=np.int64), int(np.ceil(n_samples / cfg.num_classes)))[:n_samples]
    subject_id = np.repeat(np.arange(subject_count, dtype=np.int64), samples_per_subject)
    trial_id = np.tile(np.arange(samples_per_subject, dtype=np.int64), subject_count)
    session_id = np.zeros(n_samples, dtype=np.int64)
    return DatasetBundle(features=features, labels=labels, subject_id=subject_id, trial_id=trial_id, session_id=session_id)


NL_LEVELS = (0.01, 0.03, 0.05, 0.08, 0.10, 0.125)


def _nl_slug(nl: float) -> str:
    return "NL" + ("%g" % nl).replace(".", "p")


def _expand_feature_tags(args) -> list[str]:
    """Return the list of feature tags to iterate over.

    - When --noise is provided, expand to 6 NL levels for that noise type.
    - Otherwise, fall back to a single-element list with --feature-tag
      (empty string = clean bundle).
    """
    if args.noise is not None:
        return [f"{args.noise}_{_nl_slug(nl)}" for nl in NL_LEVELS]
    return [args.feature_tag]


def main() -> None:
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    args = parse_args()
    model_names = MODEL_NAMES if args.model == "all" else (args.model,)
    if args.exclude:
        model_names = tuple(m for m in model_names if m not in args.exclude)
    require_metadata = args.protocol in {"loso", "subject_80_20"}
    if args.no_lds:
        if not args.feature_file:
            default = DATASET_CONFIGS[args.dataset].default_feature_file
            args.feature_file = default.replace("_lds_smoothed", "_no_lds")
        if not args.feature_tag:
            args.feature_tag = "no_lds"
    feature_tags = _expand_feature_tags(args)
    summaries = []
    for feature_tag in feature_tags:
        feature_path = resolve_feature_file(args.dataset, args.feature_file, feature_tag=feature_tag)
        if feature_tag:
            print(f"[run_experiments] Loading feature bundle for tag={feature_tag}: {feature_path}")
        try:
            bundle = load_feature_bundle(feature_path, dataset=args.dataset, require_metadata=require_metadata)
        except (OSError, FileNotFoundError, ValueError):
            if not args.dry_run:
                raise
            print(f"[dry-run] Using synthetic {args.dataset} data because {feature_path} is unavailable or lacks metadata.")
            bundle = make_synthetic_bundle(args.dataset)
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
                # Tag-scoped output dir so per-tag CSVs do not overwrite each other.
                if feature_tag:
                    out_dir = Path(args.output_dir) / feature_tag
                else:
                    out_dir = Path(args.output_dir)
                config = ExperimentConfig(
                    dataset=args.dataset,
                    model_name=model_name,
                    protocol=args.protocol,
                    seed=seed,
                    max_epochs=args.max_epochs,
                    max_splits=args.max_splits,
                    batch_size=args.batch_size,
                    output_dir=out_dir,
                    standard_minmax=args.standard_minmax,
                    use_depthwise_separable=not args.no_depthwise_separable,
                    use_dsgm=not args.no_dsgm,
                    use_ttfs_encoder=not args.no_ttfs_encoder,
                    use_dynamic_window=not args.no_dynamic_window,
                    replace_dsgm_with_conv=args.replace_dsgm_with_conv,
                    dry_run=args.dry_run,
                )
                summaries.append(run_experiment(bundle, splits, config))
    write_csv(Path(args.output_dir) / args.dataset / args.protocol / "summary_all.csv", summaries)
    print(f"Completed {len(summaries)} experiment summaries.")


if __name__ == "__main__":
    main()
