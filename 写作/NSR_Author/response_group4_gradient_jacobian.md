# Response Letter — Group 4: Gradient-Stability Claim and Jacobian Diagnostics

> **Superseded working draft.** Its unverified numerical diagnostic and missing image are excluded from the authoritative `response_to_reviewers.md`. Do not submit this file separately.

## Revision status

The manuscript changes for Reviewer 4, Comments 15 and 16 have been implemented in the Abstract, the ATSNN description in the main text, the Discussion, and the Supplementary Information. The responses below are ready for integration into the full response letter.

## Response strategy summary

- **Decision type:** Major revision
- **Task mode:** Draft
- **Overall posture:** Accept the criticism, report the requested analysis, and remove the unsupported network-level claim
- **Actions:** `SOFTEN_CLAIM + ACCEPT_ANALYSIS`
- **Readiness:** Ready for integration into the complete response letter

| ID | Reviewer concern | Action | Manuscript change |
|---|---|---|---|
| R4-15 | A local weight derivative does not establish multilayer gradient stability | `SOFTEN_CLAIM` | Retained the local relation but removed the network-level stability interpretation |
| R4-16 | A fixed-versus-adaptive Jacobian-spectrum analysis is required | `ACCEPT_ANALYSIS` | Performed the diagnostic; the response-only figure and numerical summary are reported below |

---

## Reviewer 4, Comment 15

> **The gradient-stability argument around Eq. (9) is too weak.**  
> Eq. (9) gives only the local derivative of an active neuron's spike time with respect to a synaptic weight. However, vanishing or exploding gradients in a deep TTFS network are controlled by the product of layer-wise spike-time Jacobians, not by this local temporal offset alone. The B1 paper analyzes the full masked Jacobian, whose spectrum depends on the active-neuron mask and the fixed-slope identity condition. The submitted manuscript does not derive the corresponding Jacobian for DA-SNN and does not show that the adaptive window keeps the multilayer Jacobian spectrum bounded.

**Response:**

We agree that the original local derivative did not establish multilayer gradient stability. We retained the equation only as a local active-neuron weight-gradient relation and removed the network-level interpretation. Specifically, the revised Abstract no longer describes ATSNN as providing stable learning; the main text now states only that the local gradient contains a presynaptic temporal-offset term; and the previous vanishing/exploding-gradient argument, temporal-offset gradient bounds, and masked-Jacobian stability claim have been removed. The adaptive temporal-window equation is presented as the definition of the implemented regulation rule.

**Locations revised:** Abstract; main text, ATSNN temporal-window paragraph; Discussion; Supplementary Information, “Local Weight-Gradient Relation and Adaptive Temporal-Window Regulation.”

---

## Reviewer 4, Comment 16

> **The authors should reproduce a B1-style Jacobian-spectrum experiment.**  
> To support the claim that ATSNN stabilizes gradients, the authors should reproduce an analogue of Fig. 2 from the B1 paper under their own DA-SNN/ATSNN conditions. They should initialize weights using standard deep-learning initialization, compute the layer-wise spike-time Jacobian with active-neuron masks, and examine whether eigenvalues remain inside or near the unit circle. This should be shown for both fixed-window and adaptive-window ATSNN. Without this analysis, the stability claim remains heuristic.

**Response:**

Following the reviewer's suggestion, we performed a matched fixed-window versus adaptive-window diagnostic on SEED. Both conditions used the same standard initialization, data split, selected validation samples, and batch order. For one training seed, we computed complete per-sample local and cumulative Jacobians for 32 fixed validation samples at initialization, epoch 5, and epoch 200. Because the implemented layer maps are rectangular, we analysed their singular-value spectra. We also recorded the actual parameter-gradient norms before global gradient clipping for every training batch.

![Response-only Jacobian and gradient diagnostic](<../Complete DA-SNN Experiment Code/outputs/jacobian_spectrum/seed_1_20260802T143923_063521/jacobian_gradient_stability.png>)

**Response-only diagnostic figure.** Per-sample cumulative Jacobian singular values and actual pre-clipping gradient norms for matched fixed- and adaptive-window DA-SNN training. The analysis used SEED, seed 1, 32 fixed validation samples, and checkpoints at epochs 0, 5, and 200. The sample distributions describe one training run and are not independent training replicates.

The table summarizes the median per-sample spectrum statistics for the hidden-stack cumulative Jacobian $J_{1\rightarrow2}\in\mathbb{R}^{32\times160}$ and the cumulative input-to-logit Jacobian $J_{1\rightarrow\mathrm{out}}\in\mathbb{R}^{3\times160}$.

| Epoch | Matrix | Median \(\sigma_{\max}\), fixed / adaptive | Median condition number, fixed / adaptive | Median mean \(|\log\sigma|\), fixed / adaptive | Median near-zero fraction, fixed / adaptive |
|---:|---|---:|---:|---:|---:|
| 0 | \(J_{1\rightarrow2}\) | 1.18 / 1.18 | 3.74 / 3.74 | 0.44 / 0.44 | 0.500 / 0.500 |
| 0 | \(J_{1\rightarrow\mathrm{out}}\) | 0.71 / 0.71 | 1.81 / 1.81 | 0.64 / 0.64 | 0.000 / 0.000 |
| 5 | \(J_{1\rightarrow2}\) | 19.24 / 19.23 | 52.57 / 59.79 | 0.63 / 0.64 | 0.359 / 0.359 |
| 5 | \(J_{1\rightarrow\mathrm{out}}\) | 37.24 / 35.92 | 47.39 / 45.39 | 1.89 / 1.89 | 0.000 / 0.000 |
| 200 | \(J_{1\rightarrow2}\) | 42.21 / 43.56 | 57.49 / 51.79 | 1.49 / 1.55 | 0.281 / 0.313 |
| 200 | \(J_{1\rightarrow\mathrm{out}}\) | 364.14 / 410.71 | 34.86 / 26.56 | 4.61 / 4.76 | 0.000 / 0.000 |

The two conditions showed mixed spectrum differences. At epoch 200, the adaptive condition had lower condition numbers, but it also had a larger cumulative $\sigma_{\max}$, a slightly larger mean $|\log\sigma|$, and a higher near-zero fraction for $J_{1\rightarrow2}$. The real-gradient trajectories were similar: the median of the epoch-level pre-clipping model-gradient norms across 200 epochs was 9.02 for the fixed condition and 8.71 for the adaptive condition. Mean clipping rates were 99.38% and 99.30%, respectively, and neither condition produced non-finite gradients.

Thus, this single-seed diagnostic did not show a consistent relative-conditioning advantage for the adaptive window. We therefore removed the network-level gradient-stability claim from the manuscript. The diagnostic is provided here to document the analysis underlying that revision.

**Locations revised:** Abstract; main text, ATSNN temporal-window paragraph; Discussion; Supplementary Information, “Local Weight-Gradient Relation and Adaptive Temporal-Window Regulation.”

**Data source:** `Complete DA-SNN Experiment Code/outputs/jacobian_spectrum/seed_1_20260802T143923_063521/`.

---

## Manuscript change checklist

- Removed `for stable learning` from the Abstract.
- Retained Eq. `grad_w` as a local active-neuron relation and removed its network-level gradient-stability interpretation.
- Retained the adaptive temporal-window update as a method definition.
- Removed the temporal-offset gradient bounds and masked-Jacobian stability argument from the Supplementary Information.
- Removed residual statements that framed window evolution as evidence for gradient stability.

## Missing information / risk flags

None for this response segment. The response-only image must be embedded when the complete response letter is typeset.
