from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from experiments.jacobian_spectrum import (
    _create_run_dir,
    _gradient_norm_rows,
    _select_analysis_indices,
    _summarize_gradient_rows,
    analytical_hidden_jacobian,
    compute_sample_jacobians,
    plot_stability_diagnostics,
    summarize_singular_values,
    train_one_epoch_instrumented,
)
from common.model_builder import build_model
from model.TTFS import DA_SNN, SpikingDense


def _dense(units: int, input_dim: int, name: str, *, output: bool = False) -> SpikingDense:
    layer = SpikingDense(units, name, input_dim=input_dim, outputLayer=output)
    layer.set_time_params(0.0, 0.0, 1.0)
    return layer


def test_select_analysis_indices_is_deterministic_and_unique():
    available = np.arange(100, 180, dtype=np.int64)

    first = _select_analysis_indices(available, count=32, seed=7)
    second = _select_analysis_indices(available, count=32, seed=7)

    assert np.array_equal(first, second)
    assert first.dtype == np.int64
    assert len(first) == len(np.unique(first)) == 32
    assert set(first).issubset(set(available))


def test_select_analysis_indices_rejects_insufficient_samples():
    with pytest.raises(ValueError, match="requested 32.*available 12"):
        _select_analysis_indices(np.arange(12), count=32, seed=1)


def test_create_run_dir_never_overwrites_existing_directory(tmp_path: Path):
    run_dir = _create_run_dir(tmp_path, run_id="kept", seed=1)
    sentinel = run_dir / "legacy.csv"
    sentinel.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError):
        _create_run_dir(tmp_path, run_id="kept", seed=1)

    assert sentinel.read_text(encoding="utf-8") == "keep"


def test_analytical_hidden_jacobian_matches_autograd_with_clipping():
    layer = _dense(2, 3, "hidden")
    with torch.no_grad():
        layer.kernel.copy_(torch.tensor([[-0.2, 0.5], [-0.1, 0.5], [-0.3, 0.5]]))
        layer.D_i.zero_()
    x = torch.tensor([0.2, 0.3, 0.4], requires_grad=True)

    analytical, output, mask = analytical_hidden_jacobian(layer, x)
    automatic = torch.autograd.functional.jacobian(lambda z: layer(z.unsqueeze(0))[0].squeeze(0), x)

    assert mask.tolist() == [True, False]
    assert torch.allclose(analytical, automatic)
    assert torch.allclose(output, torch.tensor([0.81, 1.0]))


def test_compute_sample_jacobians_returns_exact_cumulative_products():
    model = DA_SNN(use_dynamic_window=False)
    h1 = _dense(2, 3, "dense_1")
    h2 = _dense(2, 2, "dense_2")
    out = _dense(1, 2, "dense_output", output=True)
    with torch.no_grad():
        h1.kernel.copy_(torch.tensor([[-0.2, 0.5], [-0.1, 0.5], [-0.3, 0.5]]))
        h2.kernel.copy_(torch.tensor([[-0.4, -0.2], [-0.1, -0.3]]))
        out.kernel.copy_(torch.tensor([[0.7], [-0.6]]))
        h1.D_i.zero_()
        h2.D_i.zero_()
        out.D_i.zero_()
    model.add(h1)
    model.add(h2)
    model.add(out)

    matrices = compute_sample_jacobians(model, torch.tensor([0.2, 0.3, 0.4]))

    assert set(matrices) == {"J1", "J2", "Jout", "J1_2", "J1_out"}
    assert matrices["J1"].shape == (2, 3)
    assert matrices["J2"].shape == (2, 2)
    assert matrices["Jout"].shape == (1, 2)
    assert torch.allclose(matrices["J1_2"], matrices["J2"] @ matrices["J1"])
    assert torch.allclose(matrices["J1_out"], matrices["Jout"] @ matrices["J1_2"])


def test_compute_sample_jacobians_covers_real_seed_spiking_stack():
    torch.manual_seed(4)
    model = build_model(
        "da_snn",
        "seed",
        torch.device("cpu"),
        da_snn_options={"use_dynamic_window": False},
    )
    model.train()
    with torch.no_grad():
        model(torch.randn(2, 4, 8, 9))
    model.eval()

    matrices = compute_sample_jacobians(model, torch.randn(4, 8, 9))

    assert matrices["J1"].shape == (64, 160)
    assert matrices["J2"].shape == (32, 64)
    assert matrices["Jout"].shape == (3, 32)
    assert matrices["J1_2"].shape == (32, 160)
    assert matrices["J1_out"].shape == (3, 160)


def test_singular_value_summary_handles_rectangular_rank_deficient_and_zero():
    matrix = torch.tensor([[3.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    values, summary = summarize_singular_values(matrix)

    assert np.allclose(values, [3.0, 0.0])
    assert summary["sigma_max"] == pytest.approx(3.0)
    assert summary["sigma_min_nonzero"] == pytest.approx(3.0)
    assert summary["effective_rank"] == 1
    assert summary["condition_number"] == pytest.approx(1.0)
    assert summary["frac_near_zero"] == pytest.approx(0.5)

    zero_values, zero_summary = summarize_singular_values(torch.zeros(2, 3))
    assert np.array_equal(zero_values, np.zeros(2))
    assert zero_summary["effective_rank"] == 0
    assert np.isnan(zero_summary["sigma_min_nonzero"])
    assert np.isnan(zero_summary["condition_number"])


def test_gradient_norm_rows_capture_total_layer_and_parameter_norms():
    model = DA_SNN(use_dynamic_window=False)
    layer = _dense(1, 2, "dense_1")
    model.add(layer)
    layer.kernel.grad = torch.tensor([[3.0], [4.0]])
    layer.D_i.grad = torch.tensor([12.0])

    rows = _gradient_norm_rows(model)
    keyed = {(row["scope"], row["layer"], row["parameter"]): row for row in rows}

    assert keyed[("model", "all", "all")]["grad_norm"] == pytest.approx(13.0)
    assert keyed[("layer", "dense_1", "all")]["grad_norm"] == pytest.approx(13.0)
    assert keyed[("parameter", "dense_1", "kernel")]["grad_norm"] == pytest.approx(5.0)
    assert keyed[("parameter", "dense_1", "D_i")]["grad_norm"] == pytest.approx(12.0)
    assert all(row["is_finite"] for row in rows)


def test_instrumented_training_records_pre_and_post_clipping_norms():
    model = DA_SNN(use_dynamic_window=False)
    hidden = _dense(2, 2, "dense_1")
    output = _dense(2, 2, "dense_output", output=True)
    with torch.no_grad():
        hidden.kernel.copy_(torch.tensor([[-0.2, -0.1], [-0.1, -0.2]]))
        output.kernel.copy_(torch.tensor([[0.8, -0.8], [-0.7, 0.7]]))
        hidden.D_i.zero_()
        output.D_i.zero_()
    model.add(hidden)
    model.add(output)
    loader = DataLoader(
        TensorDataset(
            torch.tensor([[0.2, 0.3], [0.4, 0.1]]),
            torch.tensor([0, 1]),
        ),
        batch_size=2,
        shuffle=False,
    )
    optimizer = torch.optim.SGD(model.parameters(), lr=0.0)

    _, _, rows = train_one_epoch_instrumented(
        model,
        loader,
        torch.nn.CrossEntropyLoss(),
        optimizer,
        torch.device("cpu"),
        10.0,
        condition="Fixed Window",
        seed=1,
        epoch=1,
        max_grad_norm=1e-4,
    )

    model_row = next(row for row in rows if row["scope"] == "model")
    assert model_row["pre_clip_norm"] > 1e-4
    assert model_row["post_clip_norm"] <= 1.01e-4
    assert model_row["clip_applied"] is True
    summaries = _summarize_gradient_rows(rows)
    model_summary = next(row for row in summaries if row["scope"] == "model")
    assert model_summary["clipping_rate"] == pytest.approx(1.0)
    assert model_summary["nonfinite_rate"] == pytest.approx(0.0)


def test_stability_plot_writes_png_and_pdf_from_synthetic_records(tmp_path: Path):
    jacobian_rows = []
    singular_arrays = {}
    gradient_summaries = []
    for condition in ("Fixed Window", "Adaptive Window"):
        token = condition.replace(" ", "_")
        singular_arrays[f"{token}__epoch_0__sample_1__J1_out"] = np.array([0.5, 1.2])
        jacobian_rows.append(
            {
                "condition": condition,
                "epoch": 0,
                "matrix": "J1_out",
                "sigma_max": 1.2,
            }
        )
        gradient_summaries.extend(
            [
                {
                    "condition": condition,
                    "epoch": 1,
                    "scope": "model",
                    "layer": "all",
                    "pre_clip_median": 0.8,
                    "clipping_rate": 0.25,
                },
                {
                    "condition": condition,
                    "epoch": 1,
                    "scope": "layer",
                    "layer": "dense_1",
                    "pre_clip_median": 0.4,
                    "clipping_rate": 0.25,
                },
            ]
        )

    plot_stability_diagnostics(jacobian_rows, singular_arrays, gradient_summaries, tmp_path)

    assert (tmp_path / "jacobian_gradient_stability.png").stat().st_size > 0
    assert (tmp_path / "jacobian_gradient_stability.pdf").stat().st_size > 0
