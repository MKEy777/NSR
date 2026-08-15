from __future__ import annotations

from pathlib import Path

import numpy as np

from analysis.plot_square_jacobian_eigenvalues import plot_square_jacobians


def _make_run_dir(base: Path, name: str, condition: str) -> Path:
    run_dir = base / name
    run_dir.mkdir(parents=True, exist_ok=True)
    eigenvalues = np.array([[0.2 + 0.1j, 0.8 - 0.3j], [0.4 + 0.5j, 1.1 + 0.0j]], dtype=np.complex128)
    np.savez_compressed(
        run_dir / "square_jacobian_eigenvalues.npz",
        eigenvalues=eigenvalues,
        layer_name=np.array("dense_4"),
        condition=np.array(condition),
    )
    return run_dir


def test_plot_square_jacobians_writes_png_and_pdf(tmp_path: Path):
    fixed = _make_run_dir(tmp_path, "fixed", "Fixed Window")
    adaptive = _make_run_dir(tmp_path, "adaptive", "Adaptive Window")
    out_dir = tmp_path / "out"

    png = plot_square_jacobians(fixed, adaptive, out_dir)

    assert png.exists()
    assert png.stat().st_size > 0
    assert (out_dir / "square_jacobian_eigenvalues.pdf").exists()
    assert (out_dir / "square_jacobian_eigenvalues.pdf").stat().st_size > 0
