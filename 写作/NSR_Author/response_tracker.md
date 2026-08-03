# Comment–Response Tracker

## Package status

- Decision type: major revision
- Task mode: revision-package audit and consolidation
- Package readiness: `ready_to_submit` at the content level; final pagination and author approval are normal submission steps
- R4-16 resolution: the unverified response-only numerical diagnostic is not used; the final response accepts the reviewer’s evidentiary standard and withdraws the network-level stability claim
- Location convention: section, equation, figure, and table identifiers are used until final pagination is available

| ID | Concern | Action | Evidence / manuscript location | Risk | Readiness |
|---|---|---|---|---|---|
| R1-1 | Evaluation protocol is unclear across five datasets | `ACCEPT_TEXT + ACCEPT_ANALYSIS + SOFTEN_CLAIM` | Main Table 1 and Results; Supplementary Methods “Evaluation Protocols, Model Selection, and Statistics”; Tables S3–S5 | high | `ready_to_submit` |
| R1-2 | Main text does not show what adaptive windows and gates do | `ACCEPT_ANALYSIS + ACCEPT_FIGURE + SOFTEN_CLAIM` | Results “Emotion Recognition Performance Across EEG Benchmarks”; Supplementary Table S6 and Fig. S3 | medium | `ready_to_submit` |
| R1-3 | Ablation is limited to SEED | `ACCEPT_ANALYSIS` | Results; Supplementary “Ablation Studies”; Table S6 | medium | `ready_to_submit` |
| R1-4 | GALS domains, handshake, and efficiency mechanism are unclear | `CLARIFY_EXISTING + ACCEPT_TEXT + ACCEPT_FIGURE` | Fig. 4 legend; Hardware Implementation; Supplementary “Detailed Hardware Control Protocol”, Fig. S1, Table S10, and matched synchronous analysis | medium | `ready_to_submit` |
| R1-5 | Window/model terminology and metric definitions are inconsistent | `ACCEPT_TEXT` | Main Table 1 note; Results; Supplementary Methods and Tables S3–S6; terminology synchronized across both TeX files | low | `ready_to_submit` |
| R1-6 | Fig. 4 does not distinguish tensors from events | `ACCEPT_TEXT + ACCEPT_FIGURE` | Fig. 4 legend and alt text; Hardware Implementation | low | `ready_to_submit` |
| R1-7 | Research gap and SNN–GALS motivation are unclear | `ACCEPT_TEXT + CLARIFY_EXISTING` | Introduction, especially the dense-execution and model-to-hardware transition paragraphs | medium | `ready_to_submit` |
| R2-1 | FPGA–ARM comparison is unbalanced | `ACCEPT_EXPERIMENT + ACCEPT_ANALYSIS + SOFTEN_CLAIM` | Table 2 caption; Hardware Implementation and Discussion; Supplementary “FPGA Deployment Comparisons” and Table S11 | high | `ready_to_submit` |
| R2-2 | Cross-subject generalization is missing | `ACCEPT_ANALYSIS + ACCEPT_TEXT` | Main Table 1 and Results; Supplementary Tables S3–S5 | high | `ready_to_submit` |
| R2-3 | PSE/LDS preprocessing cost and latency boundary are omitted | `ACCEPT_EXPERIMENT + PARTIAL + SOFTEN_CLAIM` | Abstract; Hardware Implementation; Discussion and Conclusion; Supplementary Tables S7–S8 | high | `ready_to_submit` |
| R2-4 | No online adaptation or calibration is implemented | `PARTIAL + SOFTEN_CLAIM` | Discussion and Conclusion | high | `ready_to_submit` |
| R2-5 | GALS interface cost and measurement boundary are incomplete | `ACCEPT_ANALYSIS + ACCEPT_TEXT + SOFTEN_CLAIM` | Hardware Implementation and Discussion; Supplementary Tables S7, S10, and S12 plus matched synchronous analysis | high | `ready_to_submit` |
| R2-6 | Main tables have inconsistent visual styles | `ACCEPT_TEXT` | Main Tables 1–2 | low | `ready_to_submit` |
| R3-1 | Variability is not reported | `ACCEPT_ANALYSIS + ACCEPT_TEXT` | Main Table 1; Supplementary Methods statistics paragraph; Tables S4–S6 | high | `ready_to_submit` |
| R3-2 | Terminology and model naming are inconsistent | `ACCEPT_TEXT` | Main text and Supplementary Information throughout | low | `ready_to_submit` |
| R3-3 | Robustness and quantization lack matched baselines | `ACCEPT_ANALYSIS + ACCEPT_FIGURE + SOFTEN_CLAIM` | Fig. 3a and Results “Sensitivity to Controlled EEG Perturbations and Quantization”; Supplementary perturbation protocol | high | `ready_to_submit` |
| R3-4 | EEG-to-feature-to-spike transformations are unclear | `CLARIFY_EXISTING + ACCEPT_TEXT` | Results “Neuromorphic framework for EEG emotion recognition”; Fig. 2 legend; Supplementary preprocessing and DSGM dimensions | medium | `ready_to_submit` |
| R3-5 | Experimental and hardware settings are scattered | `ACCEPT_TEXT` | Supplementary Methods “Implementation Details”, Table S2, and Table S3 | medium | `ready_to_submit` |
| R3-6 | Practical deployment constraints are under-discussed | `PARTIAL + ACCEPT_TEXT + SOFTEN_CLAIM` | Discussion and Conclusion; Supplementary Tables S7–S12 | high | `ready_to_submit` |
| R4-1 | Raw EEG sparsity and model-induced event sparsity are conflated | `CLARIFY_EXISTING + ACCEPT_TEXT` | Abstract; Introduction; Results “Neuromorphic framework for EEG emotion recognition” | high | `ready_to_submit` |
| R4-2 | Prose is generic and insufficiently polished | `ACCEPT_TEXT` | Abstract and manuscript-wide language revision | low | `ready_to_submit` |
| R4-3 | “@” in Fig. 2 is undefined | `ACCEPT_TEXT` | Fig. 2 legend | low | `ready_to_submit` |
| R4-4 | C, H, and W and the EEG-to-tensor map are unclear | `ACCEPT_TEXT` | Results “Neuromorphic framework for EEG emotion recognition”; Fig. 2 legend; Supplementary preprocessing and dimension tables | medium | `ready_to_submit` |
| R4-5 | Element-wise multiplication notation is inconsistent | `ACCEPT_TEXT` | DSGM equations and Fig. 2 legend | low | `ready_to_submit` |
| R4-6 | Equation punctuation and typesetting are inconsistent | `ACCEPT_TEXT` | All equation environments in main and Supplementary Information | low | `ready_to_submit` |
| R4-7 | DSGM tensor dimensions and broadcasting are ambiguous | `ACCEPT_TEXT` | Main DSGM equations; Supplementary operation-level and dataset-specific dimensions | medium | `ready_to_submit` |
| R4-8 | “B1-model” terminology is inconsistent | `ACCEPT_TEXT` | Main B1 paragraph; Supplementary “B1-model Definition and Forward Semantics” | low | `ready_to_submit` |
| R4-9 | Threshold is not defined before use | `ACCEPT_TEXT` | Main B1 dynamics paragraph; Supplementary B1 definition | low | `ready_to_submit` |
| R4-10 | B1 selection and inherited/new boundary are unclear | `CLARIFY_EXISTING + ACCEPT_TEXT + SOFTEN_CLAIM` | Main B1 and adaptive-window paragraphs; Supplementary B1 definition | high | `ready_to_submit` |
| R4-11 | Supplement lacks core B1 definitions and assumptions | `ACCEPT_TEXT` | Supplementary “B1-model Definition and Forward Semantics” | medium | `ready_to_submit` |
| R4-12 | Eq. (6) conflates integration with censoring | `ACCEPT_TEXT` | Main censored B1 equations; Supplementary Eqs. for theoretical time, mask, and observed time; Algorithm 1 | high | `ready_to_submit` |
| R4-13 | DF-TTFS has no zero-range safeguard | `ACCEPT_TEXT` | Main DF-TTFS equation; Supplementary “Division-Free TTFS Encoding Derivation” | medium | `ready_to_submit` |
| R4-14 | Boundary spikes and silent neurons are ambiguous | `ACCEPT_TEXT` | Main censored B1 equation and readout; Supplementary B1 definition, Algorithm 1, and masked readout | high | `ready_to_submit` |
| R4-15 | Local derivative does not establish network-level stability | `SOFTEN_CLAIM + ACCEPT_TEXT` | Abstract; main ATSNN paragraph; Discussion; Supplementary local-gradient subsection | high | `ready_to_submit` |
| R4-16 | B1-style Jacobian-spectrum experiment is requested | `PARTIAL + SOFTEN_CLAIM` | Abstract, main ATSNN paragraph, Discussion, and Supplementary local-gradient subsection remove the unsupported stability claim; no unverified diagnostic is submitted | high | `ready_to_submit` |
| R4-17 | Algorithm 1 has an empty-valid-set fallback bug | `ACCEPT_TEXT` | Supplementary Algorithm 1 and adaptive-window definition | high | `ready_to_submit` |
| R4-18 | Output readout should exclude inactive neurons | `ACCEPT_TEXT + CLARIFY_EXISTING` | Main output-logit equation; Supplementary masked-readout equation | high | `ready_to_submit` |
| R4-19 | Signed INT8 quantization should use 127 | `ACCEPT_TEXT` | Supplementary “Quantization Strategy” | medium | `ready_to_submit` |
| R4-20 | Validation may be inflated by window splitting and preprocessing | `ACCEPT_TEXT + ACCEPT_ANALYSIS + SOFTEN_CLAIM` | Main Table 1 note and Results; Supplementary preprocessing, evaluation protocols, and Tables S1, S3–S5 | high | `ready_to_submit` |
| R4-21 | DF-TTFS should be framed as hardware efficiency, not accuracy gain | `ACCEPT_TEXT + SOFTEN_CLAIM` | Results cross-dataset ablation paragraph; Supplementary Table S6 | medium | `ready_to_submit` |
| R4-22 | Feature-level noise does not establish wearable robustness | `ACCEPT_ANALYSIS + SOFTEN_CLAIM` | Fig. 3a and Results; Supplementary controlled perturbation protocol; Discussion | high | `ready_to_submit` |
| R4-23 | Robustness should include NL 0.05–0.125 | `ACCEPT_ANALYSIS + ACCEPT_FIGURE` | Fig. 3a and Results; Supplementary controlled perturbation protocol | medium | `ready_to_submit` |

## Package gate

- All 42 comment rows have a complete response strategy, traceable manuscript location, and `ready_to_submit` status. Numerical, cross-reference, terminology, evidence-boundary, and NSR static-format audits are recorded in `revision_consistency_audit.md`.
