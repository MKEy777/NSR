import torch

from model.TTFS import DA_SNN, DF_TTFS_Encoder, SpikingDense


def test_da_snn_instantiates_and_runs_small_forward():
    model = DA_SNN()
    model.add(DF_TTFS_Encoder())
    model.add(torch.nn.Flatten())
    model.add(SpikingDense(4, "hidden", input_dim=6))
    model.add(SpikingDense(3, "out", input_dim=4, outputLayer=True))

    logits, min_ti_list = model(torch.rand(2, 1, 2, 3))

    assert logits.shape == (2, 3)
    assert len(min_ti_list) == 1
    spike_times, spike_mask = min_ti_list[0]
    assert spike_times.shape == spike_mask.shape
    assert spike_mask.dtype == torch.bool


def test_spiking_dense_delta_safeguard_prevents_nan():
    layer = SpikingDense(3, "out", input_dim=4, outputLayer=True, delta=1e-4)
    layer.set_time_params(1.0, 1.0, 1.0)
    out, min_ti = layer(torch.ones(2, 4))

    assert min_ti is None
    assert torch.isfinite(out).all()


def test_spiking_dense_empty_spike_mask_is_represented():
    layer = SpikingDense(3, "hidden", input_dim=4)
    with torch.no_grad():
        layer.kernel.zero_()
        layer.D_i.zero_()
    layer.set_time_params(0.0, 1.0, 1.0)
    out, min_ti = layer(torch.full((2, 4), 1e6))
    spike_times, spike_mask = min_ti

    assert torch.isfinite(out).all()
    assert spike_times.shape == spike_mask.shape
    assert not spike_mask.any()
