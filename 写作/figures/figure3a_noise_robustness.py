#!/usr/bin/env python3
"""Draw the noise-robustness component of Fig. 3 from the Markdown results."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager


def configure_times_new_roman() -> str:
    """Register Times New Roman explicitly and prohibit silent font fallback."""
    font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    font_files = ["times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf"]
    available_files = [font_dir / name for name in font_files if (font_dir / name).is_file()]
    for font_path in available_files:
        font_manager.fontManager.addfont(font_path)

    try:
        font_manager.findfont("Times New Roman", fallback_to_default=False)
    except ValueError as exc:
        raise RuntimeError(
            "Times New Roman is required. Install the font before running this script."
        ) from exc
    return "Times New Roman"


TIMES_NEW_ROMAN = configure_times_new_roman()
plt.rcParams["font.family"] = TIMES_NEW_ROMAN
plt.rcParams["font.serif"] = [TIMES_NEW_ROMAN]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.size"] = 7.2
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["legend.frameon"] = False
plt.rcParams["xtick.major.width"] = 0.7
plt.rcParams["ytick.major.width"] = 0.7
plt.rcParams["xtick.major.size"] = 2.5
plt.rcParams["ytick.major.size"] = 2.5


DATASETS = ["SEED", "DEAP", "DREAMER"]
NOISE_TYPES = ["Gaussian", "Drift", "EMG"]
MODELS = ["DA-SNN", "DH-SNN", "EEGNet"]
LEVELS = [0.0, 0.01, 0.03, 0.05, 0.08, 0.10, 0.125]
LEVEL_LABELS = ["Clean", ".01", ".03", ".05", ".08", ".10", ".125"]

STYLE = {
    "DA-SNN": {"color": "#2F5597", "marker": "s", "linestyle": "-", "zorder": 4},
    "DH-SNN": {"color": "#7030A0", "marker": "s", "linestyle": "--", "zorder": 3},
    "EEGNet": {"color": "#7F7F7F", "marker": "s", "linestyle": ":", "zorder": 2},
}

ROW_LIMITS = {
    "SEED": ((82.0, 98.5), [84, 88, 92, 96]),
    "DEAP": ((60.0, 90.0), [60, 70, 80, 90]),
    "DREAMER": ((70.0, 95.0), [70, 80, 90]),
}


def parse_results(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current_dataset: str | None = None
    current_noise: str | None = None
    table_models: list[str] | None = None

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if line.startswith("## ") and not line.startswith("### "):
            candidate = line[3:].strip()
            current_dataset = candidate if candidate in DATASETS else None
            current_noise = None
            table_models = None
            continue
        if line.startswith("### "):
            candidate = line[4:].strip().split()[0]
            current_noise = candidate if candidate in NOISE_TYPES else None
            table_models = None
            continue
        if not (current_dataset and current_noise and line.startswith("|")):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells:
            continue
        if cells[0] == "NL":
            table_models = cells[1:]
            continue
        if cells[0].replace("-", "") == "" or table_models is None:
            continue

        level = 0.0 if cells[0].lower() == "clean" else float(cells[0])
        for model, value in zip(table_models, cells[1:]):
            rows.append(
                {
                    "dataset": current_dataset,
                    "noise_type": current_noise,
                    "NL": level,
                    "model": model,
                    "accuracy": float(value),
                }
            )

    validate(rows)
    return rows


def validate(rows: list[dict[str, object]]) -> None:
    expected = {
        (dataset, noise, level, model)
        for dataset in DATASETS
        for noise in NOISE_TYPES
        for level in LEVELS
        for model in MODELS
    }
    observed = {
        (str(row["dataset"]), str(row["noise_type"]), float(row["NL"]), str(row["model"]))
        for row in rows
    }
    missing = sorted(expected - observed)
    extra = sorted(observed - expected)
    if missing or extra:
        raise ValueError(f"Unexpected source-data grid; missing={missing[:5]}, extra={extra[:5]}")

    for row in rows:
        accuracy = float(row["accuracy"])
        if not 0.0 <= accuracy <= 1.0:
            raise ValueError(f"Accuracy outside [0, 1]: {row}")

    for dataset in DATASETS:
        for model in MODELS:
            clean_values = {
                float(row["accuracy"])
                for row in rows
                if row["dataset"] == dataset and row["model"] == model and row["NL"] == 0.0
            }
            if len(clean_values) != 1:
                raise ValueError(f"Clean accuracy is inconsistent for {dataset}/{model}: {clean_values}")


def write_source_data(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["dataset", "noise_type", "NL", "model", "accuracy", "accuracy_percent"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "accuracy_percent": 100.0 * float(row["accuracy"])})


def values_for(
    rows: list[dict[str, object]], dataset: str, noise_type: str, model: str
) -> np.ndarray:
    lookup = {
        float(row["NL"]): 100.0 * float(row["accuracy"])
        for row in rows
        if row["dataset"] == dataset
        and row["noise_type"] == noise_type
        and row["model"] == model
    }
    return np.asarray([lookup[level] for level in LEVELS])


def draw(rows: list[dict[str, object]]) -> plt.Figure:
    width_in = 178.0 / 25.4
    height_in = 126.0 / 25.4
    fig, axes = plt.subplots(
        3,
        3,
        figsize=(width_in, height_in),
        sharex=True,
        gridspec_kw={"hspace": 0.26, "wspace": 0.18},
    )

    x = np.arange(len(LEVELS))
    for row_index, dataset in enumerate(DATASETS):
        ylim, yticks = ROW_LIMITS[dataset]
        for col_index, noise_type in enumerate(NOISE_TYPES):
            ax = axes[row_index, col_index]
            for model in MODELS:
                style = STYLE[model]
                y_values = values_for(rows, dataset, noise_type, model)
                ax.plot(
                    x,
                    y_values,
                    label=model,
                    color=style["color"],
                    linestyle=style["linestyle"],
                    linewidth=2.15 if model == "DA-SNN" else 1.65,
                    marker=style["marker"],
                    markersize=4.1,
                    markerfacecolor=style["color"] if model != "EEGNet" else "white",
                    markeredgecolor=style["color"],
                    markeredgewidth=0.8,
                    zorder=style["zorder"],
                )
            ax.set_ylim(*ylim)
            ax.set_yticks(yticks)
            ax.set_xlim(-0.18, len(LEVELS) - 0.82)
            ax.set_xticks(x)
            ax.set_xticklabels(LEVEL_LABELS)
            ax.tick_params(labelsize=6.5, pad=1.5, color="#BFBFBF")
            ax.spines["bottom"].set_color("#BFBFBF")
            ax.spines["bottom"].set_linewidth(0.9)

            if col_index != 0:
                ax.tick_params(axis="y", labelleft=False, left=False)
                ax.spines["left"].set_visible(False)
            else:
                ax.set_ylabel("Accuracy (%)", fontsize=7, labelpad=3)
                ax.text(
                    -0.30,
                    0.50,
                    dataset,
                    transform=ax.transAxes,
                    rotation=90,
                    ha="center",
                    va="center",
                    fontsize=7.8,
                    fontweight="bold",
                )

            if row_index == 0:
                ax.set_title(noise_type, fontsize=8.4, fontweight="bold", pad=4)
            if row_index != len(DATASETS) - 1:
                ax.tick_params(axis="x", labelbottom=False)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.54, 0.995),
        ncol=3,
        handlelength=2.4,
        columnspacing=1.5,
        handletextpad=0.5,
        fontsize=7.5,
    )
    fig.supxlabel("Noise level (NL)", x=0.54, y=0.012, fontsize=8.0)
    fig.text(0.007, 0.982, "a", fontsize=9.5, fontweight="bold", ha="left", va="top")
    fig.subplots_adjust(left=0.105, right=0.992, bottom=0.085, top=0.915)
    return fig


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        output_dir / f"{stem}.svg",
        output_dir / f"{stem}.pdf",
        output_dir / f"{stem}.tiff",
        output_dir / f"{stem}_transparent.png",
        output_dir / f"{stem}_preview.png",
    ]
    fig.savefig(outputs[0], bbox_inches="tight", facecolor="white")
    fig.savefig(outputs[1], bbox_inches="tight", facecolor="white")
    fig.savefig(
        outputs[2],
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    fig.savefig(outputs[3], dpi=600, bbox_inches="tight", transparent=True)
    fig.savefig(outputs[4], dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return outputs


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=project_root / "最终结果" / "噪声鲁棒性结果汇总.md",
        help="Markdown results table.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Directory for figure exports and source-data CSV.",
    )
    parser.add_argument("--stem", default="figure3a_noise_robustness")
    args = parser.parse_args()

    rows = parse_results(args.source)
    write_source_data(rows, args.output_dir / f"{args.stem}_source_data.csv")
    outputs = save_figure(draw(rows), args.output_dir, args.stem)
    print(f"Validated {len(rows)} observations from {args.source}")
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
