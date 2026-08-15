# DA-SNN Revision Experiments

## DA-SNN Fixed/Adaptive Jacobian Diagnostic

This experiment compares `Fixed Window` and `Adaptive Window` ATSNN under
the same seed, data split, selected validation samples, and batch order. It
uses a reduced four-layer spiking stack with 170 neurons per hidden layer.
The DA-SNN local and cumulative Jacobians are masked using observed active
spikes and reported as singular-value spectra.

```powershell
python experiments/jacobian_spectrum.py --dataset seed --seed 42 --max-epochs 200 --hidden-depth 4 --hidden-width 170
```

Each invocation creates a new child directory under
`experiment_outputs/jacobian_spectrum/`, containing per-sample and summary
singular values, pre- and post-clipping gradient logs, the diagnostic figure,
and a manifest with the network dimensions and complete arguments.

The comparison is empirical. It does not assume that the adaptive window has
a conditioning advantage; the reported spectra and gradient records determine
the interpretation.
