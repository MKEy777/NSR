from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _load_run(run_dir: Path) -> tuple[str, np.ndarray, str]:
    spectrum_file = run_dir / "square_jacobian_eigenvalues.npz"
    summary_file = run_dir / "square_jacobian_summary.json"
    if not spectrum_file.exists():
        raise FileNotFoundError(f"Missing {spectrum_file}")
    data = np.load(spectrum_file, allow_pickle=False)
    eigenvalues = np.asarray(data["eigenvalues"], dtype=np.complex128)
    layer_name = str(data["layer_name"]) if "layer_name" in data else "square layer"
    condition = str(data["condition"]) if "condition" in data else run_dir.name
    if summary_file.exists():
        payload = json.loads(summary_file.read_text(encoding="utf-8"))
        condition = payload.get("condition", condition)
        layer_name = payload.get("layer_name", layer_name)
    return condition, eigenvalues, layer_name


def plot_square_jacobians(fixed_run: Path, adaptive_run: Path, output_dir: Path) -> Path:
    fixed_condition, fixed_values, fixed_layer = _load_run(fixed_run)
    adaptive_condition, adaptive_values, adaptive_layer = _load_run(adaptive_run)
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    theta = np.linspace(0.0, 2.0 * np.pi, 512)
    palette = {fixed_condition: "#2878B5", adaptive_condition: "#D95319"}
    panels = [
        (axes[0], fixed_condition, fixed_values, fixed_layer),
        (axes[1], adaptive_condition, adaptive_values, adaptive_layer),
    ]
    for ax, condition, values, layer_name in panels:
        flat = np.asarray(values, dtype=np.complex128).reshape(-1)
        radius = max(1.1, float(np.max(np.abs(flat))) * 1.05)
        ax.scatter(flat.real, flat.imag, s=10, alpha=0.55, color=palette[condition], edgecolors="none")
        ax.plot(np.cos(theta), np.sin(theta), color="black", linestyle="--", linewidth=1)
        ax.axhline(0.0, color="#888888", linewidth=0.7)
        ax.axvline(0.0, color="#888888", linewidth=0.7)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlim(-radius, radius)
        ax.set_ylim(-radius, radius)
        ax.set_title(f"{condition} ({layer_name}, max |lambda|={float(np.max(np.abs(flat))):.2f})")
        ax.set_xlabel("Real eigenvalue component")
    axes[0].set_ylabel("Imaginary eigenvalue component")
    fig.suptitle("Square Jacobian eigenvalue scatter for fixed vs adaptive windows", fontweight="bold")
    fig.tight_layout()
    png = output_dir / "square_jacobian_eigenvalues.png"
    pdf = output_dir / "square_jacobian_eigenvalues.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    fig.savefig(pdf, bbox_inches="tight")
    plt.close(fig)
    return png


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Plot square Jacobian eigenvalue scatters for fixed vs adaptive windows.")
    parser.add_argument("--fixed-run", required=True, type=Path)
    parser.add_argument("--adaptive-run", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out = plot_square_jacobians(args.fixed_run, args.adaptive_run, args.output_dir)
    print(out)


if __name__ == "__main__":
    main()
