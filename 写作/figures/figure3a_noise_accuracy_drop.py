#!/usr/bin/env python3
"""Draw Fig. 3a with absolute accuracy curves and endpoint accuracy drops."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator

from figure3a_noise_robustness import (
    DATASETS,
    LEVELS,
    LEVEL_LABELS,
    MODELS,
    NOISE_TYPES,
    ROW_LIMITS,
    STYLE,
    parse_results,
    save_figure,
    values_for,
    write_source_data,
)


def draw(rows: list[dict[str, object]]) -> plt.Figure:
    width_in = 142.4 / 25.4
    height_in = 126.0 / 25.4
    fig, axes = plt.subplots(
        3,
        3,
        figsize=(width_in, height_in),
        sharex=True,
        gridspec_kw={"hspace": 0.24, "wspace": 0.16},
    )

    x = np.arange(len(LEVELS), dtype=float)
    display_lowers = {"SEED": 80.0, "DEAP": 57.0, "DREAMER": 67.0}

    for row_index, dataset in enumerate(DATASETS):
        ylim, yticks = ROW_LIMITS[dataset]

        for col_index, noise_type in enumerate(NOISE_TYPES):
            ax = axes[row_index, col_index]
            series = {
                model: values_for(rows, dataset, noise_type, model) for model in MODELS
            }

            for model in MODELS:
                style = STYLE[model]
                ax.plot(
                    x,
                    series[model],
                    label=model,
                    color=style["color"],
                    linestyle=style["linestyle"],
                    linewidth=1.75 if model == "DA-SNN" else 1.35,
                    marker="s",
                    markersize=3.25,
                    markerfacecolor=style["color"] if model != "EEGNet" else "white",
                    markeredgecolor=style["color"],
                    markeredgewidth=0.65,
                    zorder=style["zorder"],
                )

            if row_index == 0 and col_index == 0:
                clean_accuracy = series["DA-SNN"][0]
                endpoint_accuracy = series["DA-SNN"][-1]
                bracket_x = 5.62
                ax.plot(
                    [0.0, bracket_x],
                    [clean_accuracy, clean_accuracy],
                    color=STYLE["DA-SNN"]["color"],
                    linewidth=0.75,
                    linestyle=(0, (2.0, 2.0)),
                    alpha=0.75,
                    zorder=2,
                )
                ax.plot(
                    [bracket_x, x[-1]],
                    [endpoint_accuracy, endpoint_accuracy],
                    color=STYLE["DA-SNN"]["color"],
                    linewidth=0.75,
                    linestyle=(0, (2.0, 2.0)),
                    alpha=0.75,
                    zorder=2,
                )
                ax.annotate(
                    "",
                    xy=(bracket_x, endpoint_accuracy),
                    xytext=(bracket_x, clean_accuracy),
                    arrowprops={
                        "arrowstyle": "<->",
                        "color": STYLE["DA-SNN"]["color"],
                        "linewidth": 0.9,
                        "shrinkA": 0,
                        "shrinkB": 0,
                    },
                    zorder=6,
                )
                ax.text(
                    bracket_x - 0.18,
                    (clean_accuracy + endpoint_accuracy) / 2,
                    "\u0394Acc",
                    color=STYLE["DA-SNN"]["color"],
                    fontsize=6.8,
                    fontweight="bold",
                    rotation=90,
                    ha="right",
                    va="center",
                    zorder=7,
                )

            for label_x, model in zip((0.18, 0.50, 0.82), MODELS):
                style = STYLE[model]
                drop = series[model][-1] - series[model][0]
                drop_text = f"{drop:+.2f}".replace("-", "\u2212")
                ax.text(
                    label_x,
                    0.035,
                    f"\u0394{drop_text}",
                    transform=ax.transAxes,
                    color=style["color"],
                    fontsize=6.8,
                    fontweight="bold",
                    ha="center",
                    va="bottom",
                )

            ax.set_ylim(display_lowers[dataset], ylim[1])
            ax.set_yticks(yticks)
            ax.yaxis.set_minor_locator(AutoMinorLocator(2))
            ax.set_xlim(-0.18, 6.22)
            ax.set_xticks(x)
            ax.set_xticklabels(LEVEL_LABELS)
            ax.grid(axis="y", which="major", color="#C8C8C8", linestyle=":", linewidth=0.55)
            ax.grid(axis="y", which="minor", color="#DEDEDE", linestyle=":", linewidth=0.4)
            ax.set_axisbelow(True)
            ax.tick_params(labelsize=7.2, pad=1.2, width=0.65, length=2.2)

            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color("black")
                spine.set_linewidth(0.65)

            if col_index == 0:
                ax.set_ylabel("Accuracy (%)", fontsize=8.2, fontweight="bold", labelpad=2.5)
                ax.text(
                    -0.23,
                    0.50,
                    dataset,
                    transform=ax.transAxes,
                    rotation=90,
                    ha="center",
                    va="center",
                    fontsize=8.6,
                    fontweight="bold",
                )
            else:
                ax.tick_params(axis="y", labelleft=False)

            if row_index == 0:
                ax.set_title(noise_type, fontsize=9.0, fontweight="bold", pad=3)
            if row_index != len(DATASETS) - 1:
                ax.tick_params(axis="x", labelbottom=False)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.56, 0.995),
        ncol=3,
        handlelength=2.1,
        columnspacing=1.0,
        handletextpad=0.35,
        fontsize=8.3,
        prop={"family": "Times New Roman", "size": 8.3, "weight": "bold"},
    )
    fig.supxlabel("Noise level (NL)", x=0.54, y=0.012, fontsize=8.8, fontweight="bold")
    fig.subplots_adjust(left=0.08, right=0.992, bottom=0.10, top=0.88)
    return fig


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=(
            project_root
            / "\u6700\u7ec8\u7ed3\u679c"
            / "\u566a\u58f0\u9c81\u68d2\u6027\u7ed3\u679c\u6c47\u603b.md"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    parser.add_argument("--stem", default="figure3a_noise_accuracy_drop")
    args = parser.parse_args()

    rows = parse_results(args.source)
    write_source_data(rows, args.output_dir / f"{args.stem}_source_data.csv")
    outputs = save_figure(draw(rows), args.output_dir, args.stem)
    for output in outputs:
        print(output)


if __name__ == "__main__":
    main()
