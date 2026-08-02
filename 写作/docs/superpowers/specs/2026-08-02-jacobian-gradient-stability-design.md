# Jacobian and Gradient-Stability Experiment Design

## Scope

Revise `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py` so that the fixed-window and adaptive-window DA-SNN variants are compared with per-sample full spike-time Jacobians, cumulative Jacobians, and actual training-gradient statistics. Manuscript text is out of scope.

## Data-preservation constraint

- Never delete or overwrite existing experiment outputs.
- A run writes to a new run directory below the requested output root.
- The default run identifier contains the seed and a timestamp; a user-supplied run identifier is allowed only when its directory does not already exist.
- Raw measurements are retained alongside summaries and plots.

## Fair comparison protocol

- Use 32 validation samples per condition and stage by default.
- Select sample indices deterministically from the seed and reuse the same indices for fixed and adaptive conditions.
- Give both conditions identical initial weights and deterministic data-loader order for a given seed.
- Train each condition once and capture checkpoints at epoch 0, epoch 5, and `max_epochs`; do not restart training independently for each stage.
- Label the final stage by its epoch number rather than claiming convergence.

## Jacobian definition

For each sample, construct exact piecewise-linear Jacobians for the spiking stack:

- `J1`: encoder spike times to hidden layer 1.
- `J2`: hidden layer 1 to hidden layer 2.
- `Jout`: hidden layer 2 to logits.
- `J1_2 = J2 @ J1`.
- `J1_out = Jout @ J2 @ J1`.

Hidden-layer local Jacobians apply the postsynaptic activity mask induced by the implemented clipping branch. A preceding layer's inactivity then enters the cumulative Jacobian through ordinary matrix multiplication; adding a second presynaptic column mask to the local derivative would not equal the autograd Jacobian of the implemented model. The output-layer Jacobian follows the implemented output-layer derivative. At clipping boundaries, the inactive branch has zero derivative, matching PyTorch's executed branch. The matrices cover the spike-time stack after the encoder, not the preceding convolutional feature extractor.

The production implementation uses the exact analytical matrices for efficiency. Unit tests compare them with autograd Jacobians on a small deterministic model.

For every local and cumulative matrix, retain the complete singular-value vector and report:

- largest singular value;
- smallest nonzero singular value using a documented numerical tolerance;
- effective rank;
- finite condition number over the nonzero spectrum;
- mean absolute log singular value over the nonzero spectrum;
- fraction above one;
- fraction below the near-zero threshold.

These quantities are empirical conditioning diagnostics, not a proof of global gradient stability.

## Actual-gradient recording

During every training batch, record gradients after `loss.backward()` and before global clipping:

- total model gradient norm;
- aggregate gradient norm for each `SpikingDense` layer;
- gradient norms for each trainable parameter in those layers;
- non-finite-gradient indicator;
- norm returned by `clip_grad_norm_` and the implied clipping factor;
- corresponding post-clipping total and layer norms.

Epoch summaries report count, median, mean, standard deviation, interquartile range, minimum, maximum, coefficient of variation, non-finite rate, and clipping rate. Raw batch-level records are preserved.

## Outputs

Each run directory contains:

- `jacobian_per_sample.csv`;
- `jacobian_summary.csv`;
- `jacobian_singular_values.npz`;
- `gradient_per_batch.csv`;
- `gradient_per_epoch.csv`;
- a comparison figure in PNG and PDF;
- a machine-readable run manifest containing arguments, seed, selected sample indices, stage epochs, metric definitions, and file names.

The comparison figure contains:

1. local and cumulative singular-value distributions on a log scale;
2. cumulative-Jacobian statistics at the recorded stages;
3. pre-clipping layer-wise gradient-norm trajectories;
4. clipping/non-finite event heatmaps.

## CLI compatibility

Retain the current main arguments and add controls for the number of Jacobian samples, stage epochs, run identifier, and optional smoke-test limits. Existing output paths remain readable; new runs do not modify them.

## Error handling

- Reject an existing run directory instead of overwriting it.
- Fail with a clear message when fewer than 32 validation samples are available unless the requested sample count is explicitly lower.
- Represent rank-zero matrices explicitly without reporting an infinite value as an ordinary finite condition number.
- Record non-finite gradients before clearing them or skipping an optimizer step.

## Test strategy

Tests are written before implementation and must demonstrate:

1. analytical local Jacobians match autograd for active and clipped neurons;
2. cumulative Jacobians equal explicit matrix products and remain sample-specific;
3. singular-value summaries handle rectangular, rank-deficient, and zero matrices;
4. gradient norms are captured before and after clipping without changing optimization behavior;
5. fixed/adaptive conditions reuse the same selected validation indices;
6. existing output directories are never overwritten;
7. code-level artifact tests create all declared raw, summary, manifest, and figure artifacts from synthetic in-memory records; no dataset experiment is run during implementation.

## Interpretation boundary

The experiment may support relative empirical stability only if the adaptive condition consistently reduces extreme cumulative singular values and/or real-gradient variability under matched seeds. The code and plots must not label the analysis as an eigenvalue unit-circle reproduction or as a theoretical guarantee.
