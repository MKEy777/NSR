# Jacobian and Gradient-Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace batch-mixed Jacobian sampling with exact per-sample local and cumulative spike-time Jacobians, and record real pre-/post-clipping training gradients without overwriting existing experiment data.

**Architecture:** Keep the experiment self-contained in `experiments/jacobian_spectrum.py`. Exact analytical Jacobians are assembled from `SpikingDense.kernel` and sample activity masks, then multiplied in forward order; a dedicated training loop records gradients before and after the existing global clipping operation and captures three checkpoints from one trajectory per condition.

**Tech Stack:** Python, PyTorch, NumPy, pandas-free CSV writing, Matplotlib, SciPy, pytest.

## Global Constraints

- Use 32 deterministically selected validation samples by default and reuse their dataset indices across fixed/adaptive conditions.
- Never delete or overwrite an existing experiment output directory.
- Preserve raw singular values and raw batch-level gradients alongside summaries.
- Call the result an empirical singular-value diagnostic, never an eigenvalue/unit-circle reproduction or theoretical guarantee.
- Do not alter `common/trainer.py`; reproduce its optimizer, clipping, and window-update order in the experiment-specific instrumented loop.
- Do not commit because the target script and test directory are pre-existing user-owned untracked files in a broadly dirty repository.

---

### Task 1: Output reservation and deterministic sample selection

**Files:**
- Modify: `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py`
- Create: `Complete DA-SNN Experiment Code/tests/test_jacobian_spectrum.py`

**Interfaces:**
- Produces: `_create_run_dir(output_root: Path, run_id: str | None, seed: int) -> Path`
- Produces: `_select_analysis_indices(val_indices: np.ndarray, count: int, seed: int) -> np.ndarray`

- [ ] Write tests asserting deterministic, unique 32-sample selection and rejection when fewer samples exist.
- [ ] Run `python -m pytest tests/test_jacobian_spectrum.py -k "select_analysis_indices" -v` and verify failure because the helpers do not exist.
- [ ] Implement selection with `np.random.default_rng(seed).choice(..., replace=False)` and sorted `int64` output.
- [ ] Write tests asserting `_create_run_dir` creates a new directory and raises `FileExistsError` for an existing explicit run ID.
- [ ] Implement timestamped default run IDs and exclusive directory creation with `mkdir(parents=True, exist_ok=False)`.
- [ ] Run the focused tests and verify they pass.

### Task 2: Exact per-sample local and cumulative Jacobians

**Files:**
- Modify: `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py`
- Test: `Complete DA-SNN Experiment Code/tests/test_jacobian_spectrum.py`

**Interfaces:**
- Produces: `collect_spiking_stack_state(model: DA_SNN, x: torch.Tensor) -> list[dict]`
- Produces: `compute_sample_jacobians(model: DA_SNN, x_single: torch.Tensor) -> dict[str, torch.Tensor]`
- Produces: `summarize_singular_values(matrix: torch.Tensor, zero_tol: float = 1e-8) -> tuple[np.ndarray, dict[str, float | int]]`

- [ ] Write a deterministic tiny two-hidden-layer model test with active and clipped units; compare each analytical local matrix against `torch.autograd.functional.jacobian` for one sample.
- [ ] Run the local-Jacobian test and verify failure because the new API does not exist.
- [ ] Implement a forward-state collector that retains encoder times and per-layer active masks for one sample without mixing batch rows.
- [ ] Implement hidden Jacobians as postsynaptically masked transposed kernels and the output Jacobian as the derivative of the implemented output-layer map; allow preceding-layer masks to enter cumulative products naturally.
- [ ] Run the local-Jacobian test and verify it passes.
- [ ] Write a failing test asserting `J1_2 == J2 @ J1` and `J1_out == Jout @ J1_2`, with different samples producing independently masked matrices.
- [ ] Implement cumulative products and return `J1`, `J2`, `Jout`, `J1_2`, and `J1_out` under stable names.
- [ ] Write failing summary tests for rectangular, rank-deficient, and all-zero matrices.
- [ ] Implement singular-value metrics: `sigma_max`, `sigma_min_nonzero`, `effective_rank`, `condition_number`, `mean_abs_log_sigma`, `frac_above_one`, and `frac_near_zero`; represent undefined finite metrics as NaN plus explicit rank.
- [ ] Run all Task 2 tests and verify they pass.

### Task 3: Instrumented training and matched checkpoint trajectory

**Files:**
- Modify: `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py`
- Test: `Complete DA-SNN Experiment Code/tests/test_jacobian_spectrum.py`

**Interfaces:**
- Produces: `_gradient_norms(model: nn.Module) -> dict[str, float | bool]`
- Produces: `train_one_epoch_instrumented(...) -> tuple[float, float, list[dict]]`
- Produces: `_summarize_gradient_rows(rows: list[dict]) -> list[dict]`

- [ ] Write a failing test using a tiny model with known gradients to assert total, per-`SpikingDense`, and parameter norms before clipping.
- [ ] Implement finite-aware L2 aggregation without modifying `.grad` tensors.
- [ ] Write a failing test asserting the instrumented step records pre-clip norm, post-clip norm, clipping factor, and non-finite status while matching one ordinary optimizer step for finite gradients.
- [ ] Implement the experiment-specific epoch loop in the exact order: zero gradients, forward, loss, backward, pre-clip record, `clip_grad_norm_(1.0)`, post-clip record, valid-gradient optimizer step, dynamic-window update.
- [ ] Write a failing test for epoch aggregation of median, mean, standard deviation, IQR, extrema, coefficient of variation, clipping rate, and non-finite rate.
- [ ] Implement aggregation grouped by condition, seed, epoch, scope, layer, and parameter.
- [ ] Refactor `run_jacobian_experiment` so each condition trains once and captures Jacobians at epoch 0, 5, and `max_epochs`; initialize both conditions and data-loader generators from the same seed.
- [ ] Run all Task 3 tests and verify they pass.

### Task 4: Raw artifacts, summaries, manifest, and visualization

**Files:**
- Modify: `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py`
- Test: `Complete DA-SNN Experiment Code/tests/test_jacobian_spectrum.py`

**Interfaces:**
- Produces run artifacts: `jacobian_per_sample.csv`, `jacobian_summary.csv`, `jacobian_singular_values.npz`, `gradient_per_batch.csv`, `gradient_per_epoch.csv`, `run_manifest.json`, `jacobian_gradient_stability.png`, and `jacobian_gradient_stability.pdf`.

- [ ] Write a failing artifact test that reserves a temporary run directory, supplies synthetic Jacobian/gradient records, and asserts all declared files are created without modifying a sibling legacy file.
- [ ] Implement CSV/NPZ/JSON writers using temporary files followed by same-directory atomic replacement only inside the newly reserved run directory.
- [ ] Implement a four-panel figure: log-scale singular-value distributions, cumulative-Jacobian stage metrics, pre-clip gradient trajectories, and clipping/non-finite event heatmaps.
- [ ] Replace legacy names such as `eigs`, `spectral_radius`, `unit_circle`, and `Converged` in new outputs with singular-value and epoch-specific terminology.
- [ ] Extend CLI with `--jacobian-samples` (default 32), `--stage-epochs` (default `0,5,max`), `--run-id`, and smoke limits while retaining current arguments.
- [ ] Write and pass parser tests for defaults and invalid sample/stage values.
- [ ] Run `python -m pytest tests/test_jacobian_spectrum.py -v` and verify all focused tests pass.

### Task 5: Regression and static verification

**Files:**
- Modify only if failures require it: `Complete DA-SNN Experiment Code/experiments/jacobian_spectrum.py`
- Test: `Complete DA-SNN Experiment Code/tests/test_jacobian_spectrum.py`

- [ ] Run `python -m pytest tests/test_jacobian_spectrum.py tests/test_ttfs.py tests/test_trainer_smoke.py -v`.
- [ ] Run `python -m py_compile experiments/jacobian_spectrum.py`.
- [ ] Do not run a dataset experiment; implementation verification is limited to synthetic unit tests, import checks, and compilation.
- [ ] Verify a second run with the same explicit run ID fails before writing or changing any file.
- [ ] Inspect `git diff --no-index`/file hashes as appropriate to confirm no existing files under `outputs/jacobian_spectrum` were changed.
