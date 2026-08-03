# Revision Group 12 — Final Consistency Audit

## Audit scope

- Authoritative reviewer source: `docs/大修意见.md`
- Authoritative response: `NSR_Author/response_to_reviewers.md`
- Tracker: `NSR_Author/response_tracker.md`
- Manuscript sources: `NSR_Author/main.tex` and `NSR_Author/supplement.tex`
- Journal requirements: `docs/Manuscript_Instructions.md`
- Verification mode: static source audit only; no compilation was performed

## 1. Completeness and uniqueness

- Reviewer 1: 7/7 comments present.
- Reviewer 2: 6/6 comments present.
- Reviewer 3: 6/6 comments present.
- Reviewer 4: 23/23 comments present.
- Total: 42/42 stable IDs, with no duplicate ID in the response or tracker.
- Every response block contains reviewer-comment text, a direct response, and at least one manuscript location.
- R1-5 covers both terminology/model naming and metric definitions.
- R2-5 is consolidated as one response containing interface semantics, component cost, measurement boundary, energy arithmetic, and the matched synchronous baseline; R2-1 additionally distinguishes the cross-model EEGNet FPGA deployment comparison.
- R4-22 appears once in the authoritative response.
- Legacy `response_*.md` files are marked as superseded working drafts and are not submission artifacts.

## 2. Evidence and claim audit

- No response claims an experiment, analysis, figure, or measurement that is absent from the manuscript sources, except that the former unverified R4-16 response-only diagnostic was found and removed from the authoritative response.
- R4-16 is handled as `PARTIAL + SOFTEN_CLAIM`: the response accepts that a full masked-Jacobian analysis would be required, does not submit unverified numerical evidence, and points to removal of the network-level stability claim.
- R2-4 does not claim online calibration, continual learning, pseudo-label learning, MCU feasibility, or zero-cost adaptation.
- R3-6 does not claim complete preprocessing fits in model memory, that 18 μs is acquisition-to-decision latency, or that ASIC migration gives a quantified scaling benefit.
- Reviewer-comment formula-image dependencies in R4-12 and R4-17 were replaced by faithful text descriptions; the responses and manuscript equations remain explicit.

## 3. Narrative and contribution boundary

The Abstract, Introduction, Results, Discussion, Conclusion, and response letter use the same causal sequence:

1. emotion-related neural activity motivates event-driven and temporally sparse representations;
2. scalp EEG is continuously sampled and is not a directly usable hardware event stream;
3. DA-SNN/DF-TTFS converts EEG-derived dense features into sparse spike events;
4. the GALS accelerator uses valid model events to trigger data movement and computation.

No authoritative file states that GALS directly exploits raw EEG sparsity. The contribution list is not reordered or replaced.

## 4. Evaluation-protocol consistency

- Main Table 1: subject-dependent, class-stratified random outer-window-level 80/20 benchmark.
- Outer windows are non-overlapping; PSE temporal-bin lengths are not described as outer-window strides.
- Subjects and trials may occur in both main-benchmark partitions.
- LDS smoothing is trial-wise but is applied to the complete trial sequence before the subject-dependent split; the remaining coupling is disclosed.
- No independent validation subset is claimed. The held-out evaluation partition is used for checkpoint selection and final reporting, and the interpretation is restricted accordingly.
- Subject-independent evaluation uses LOSO for the SEED family and five fixed subject-holdout splits for DEAP and DREAMER.
- Training seeds are 1–5; sample standard deviation uses `ddof=1` where repeat- or split-level values are available.
- DEAP/DREAMER subject-holdout dispersion is not imputed when only aggregate point estimates are available.

## 5. Numerical consistency

| Quantity | Frozen value and interpretation |
|---|---|
| Main SEED benchmark | 96.85 ± 1.44% |
| Quantization sweep | FP32 96.98%; INT8 96.94%; difference −0.04 percentage points |
| GALS accelerator latency | 18 μs from one preprocessed tensor to class output |
| GALS power | 40/108/148 mW dynamic/static/total |
| GALS energy | 0.72 μJ dynamic-only; 2.66 μJ total-power energy |
| Energy arithmetic | 148 mW × 18 μs = 2.664 μJ, reported as 2.66 μJ |
| Matched synchronous baseline | 16.5 μs; 3.35 μJ total energy |
| Net GALS implementation cost | +172 LUTs, +139 FFs, +9.09% latency |
| Matched energy result | 20.6% lower total energy for the evaluated GALS implementation |
| GALS interface gross budget | 981 LUTs and 602 FFs; not the net asynchronous overhead |
| Model-side INT8 memory | 12.50 KB parameters and 13.68 KB runtime memory |

The response distinguishes the 96.85% main result from the 96.98% FP32 quantization-sweep value. Accelerator energy excludes PSE/LDS, EEG acquisition, sensor front end, processing-system cores, external DDR, and board peripherals.

## 6. Terminology, mathematics, and cross-references

- Complete model: DA-SNN; temporal spiking classifier: ATSNN.
- Temporal terms: outer window, PSE temporal bin, and layer-wise temporal window.
- Event terms: spike time, timestamp, event, and active spike retain distinct meanings.
- B1 terminology, active mask, censored time, strict upper boundary, empty-valid-set fallback, and masked-equivalent readout are synchronized across main and Supplementary Information.
- DF-TTFS includes the zero-range safeguard and is framed as a hardware-efficiency contribution rather than an accuracy advantage.
- Signed INT8 weights use −127 to 127; the −128 code is unused.
- No duplicate LaTeX labels or undefined internal `\ref`/`\eqref` targets were found in either TeX source.
- Checked LaTeX environment pairs and brace balance are consistent in both TeX files.

## 7. NSR static compliance

| Requirement | Static result |
|---|---|
| Main text ≤5000 words | approximately 4094 words after excluding display environments |
| Abstract ≤150 words, single paragraph | 138 words |
| Methods ≤500 words | 36 words |
| Main figures/tables ≤6 | 4 figures + 2 tables = 6 |
| References ≤50 | 47 unique main-text citation keys |
| Main-figure alt text | 4/4 figures contain `Alt text:` |
| Table style | no vertical rules or coloured/shaded cells; units are in headers |

The word counts are static source estimates because the user requested no compilation and no TeX counting environment is available.

## 8. Package readiness

- All 42 tracker rows are `ready_to_submit` at the content level.
- The authoritative Markdown response contains no result placeholders, missing evidence claims, temporary reviewer IDs, or non-standard action labels.
- Final page and line numbers may be added after pagination, but current section/equation/figure/table locations are already traceable and do not require invented numbers.
- Package readiness: `ready_to_submit` for content; typesetting and final author approval remain normal submission steps rather than unresolved scientific evidence.
