# Response Letter: Limitations Responses

> **Superseded working draft.** This file contains pre-audit language and must not be submitted. The authoritative R2-1, R2-3, R2-4, R3-6, and R4-22 responses are in `response_to_reviewers.md`.

## L1. LDS Computational Cost and Real-Time Feasibility (R2-3)

**Reviewer concern:** *"The methodology relies heavily on Linear Dynamical System (LDS) smoothing to filter the feature sequences across windows. LDS smoothing inherently requires observing sequences over time, which introduces significant computational latency, memory buffering, and complex matrix operations. The manuscript entirely fails to address how this computationally expensive, latency-inducing smoothing process is executed in real-time on the proposed resource-constrained edge hardware."*

**Response:**

We thank the reviewer for raising the computational and buffering cost of trial-wise LDS smoothing. We agree that the original accelerator figures did not make the preprocessing boundary sufficiently clear. The reported 18~$\mu$s latency and 2.66~$\mu$J energy correspond only to inference from a preprocessed input tensor to the class output; PSE extraction and LDS smoothing are not included in those accelerator-side values.

To quantify the omitted preprocessing rather than treating it as negligible, we implemented and tested PSE and LDS as independent FPGA kernels on the same board. The LDS kernel uses 4,797 LUTs, 374 FFs, one BRAM, and eight DSPs at 4~MHz. Its reported test processes 288 lanes over three steps (864 outputs) in 0.216~ms, with board-measured dynamic, static, and total power of 5, 105, and 109~mW, respectively, corresponding to 23.544~$\mu$J for that kernel test. This is not a complete trial-level LDS measurement and is therefore not reported as per-inference preprocessing energy. For completeness, the PSE kernel was also independently measured per 200-sample call. Because PSE, LDS, and accelerator inference were tested separately rather than as a jointly integrated pipeline, their static-power and energy values are not directly summed into an end-to-end system value.

We have revised the Supplementary Information to add a system inclusion table and a standalone preprocessing-kernel table, and we now state the exclusion of PSE/LDS in the Abstract, Hardware Implementation section, and Conclusion. This revision quantifies the available kernel-level cost while avoiding an unsupported end-to-end or real-time preprocessing claim.

---

## L2. Absence of Online Adaptive Mechanism (R2-4)

**Reviewer concern:** *"The authors acknowledge in the Discussion that long-term wearable deployment faces severe challenges from individual state variations and electrode impedance drift. However, for a system whose primary selling point is enabling 'continuous wearable monitoring,' the complete absence of any implemented online adaptive or calibration mechanism is a critical functional gap in the proposed framework."*

**Response:**

We agree with the reviewer that online adaptation is essential for sustained wearable deployment, and we acknowledge that the current system's parameters are frozen after training with no built-in recalibration mechanism. We position this not as an oversight but as a deliberate scoping decision for the present work, which focuses on establishing the algorithm–hardware co-design foundation. Nevertheless, we have expanded the Discussion to articulate a concrete, phased roadmap for online adaptation:

**Phase 1 — EMA normalization statistics update (near-term, MCU-feasible).** The simplest adaptation mechanism involves maintaining exponential moving average (EMA) estimates of feature normalization statistics (mean and variance) at the edge. This requires only two scalar multiplications and additions per feature dimension per update step, with negligible computational overhead that is well within the capability of a Cortex-M-class MCU. This addresses slow distribution shifts caused by electrode impedance drift and ambient condition changes.

**Phase 2 — Subject-specific bias correction with minimal calibration (medium-term).** For scenarios requiring personalized deployment, we propose a lightweight calibration protocol using 1–3 labeled trials per subject, during which only the final classification layer's bias term is fine-tuned while all preceding weights remain frozen. This constrains the trainable parameter count to the number of output classes (e.g., 3 for SEED's valence/arousal/dominance), making it feasible for on-device gradient computation.

**Phase 3 — Online continual learning with pseudo-labels (long-term).** For fully autonomous long-term monitoring, pseudo-label-based self-training can be employed, where high-confidence predictions serve as online supervision signals. This direction requires careful management of prediction drift and error accumulation, which we reserve for dedicated future investigation.

We emphasize that these are clearly defined future work items that build upon the current contribution rather than gaps in the present work's scope.

---

## L3. Noise Injection at Feature Level vs. Raw EEG (R4-22)

**Reviewer concern:** *"Noise injected into feature maps rather than raw EEG; doesn't model realistic wearable artifacts."*

**Response:**

We agree that the original description and the associated wearable-robustness claim were too broad. In the revised experiment, perturbations are applied to time-domain EEG samples after dataset-specific signal conditioning and segmentation but before PSE extraction, spatial mapping, and LDS smoothing. All downstream features are therefore recomputed from the perturbed samples; no perturbation is added directly to the PSE feature maps.

The revised evaluation covers additive Gaussian noise, low-frequency drift, and EMG-like transient bursts on SEED, DEAP, and DREAMER, with DH-SNN and EEGNet evaluated under the same noisy bundles and training protocol. We now describe this evidence as a controlled signal-level sensitivity test. We have also removed the unsupported attribution of the observed behavior to TTFS encoding or adaptive temporal windows because the experiment does not isolate either mechanism.

We explicitly acknowledge that these synthetic perturbations, evaluated with one model seed and noise-matched training, do not establish zero-shot robustness of a fixed clean-trained model or reproduce the full distribution of naturally occurring motion, electrode-contact, sweat, ocular, and muscular artifacts in long-term wearable recordings. Evaluation on recorded wearable artifacts and across multiple seeds remains future work.

---

## L4. FPGA vs. ARM Hardware Comparison Fairness (R2-1)

**Reviewer concern:** *"The energy efficiency of the proposed GALS accelerator, deployed on a customized FPGA, is compared directly against conventional lightweight CNNs running on a general-purpose ARM processor (Raspberry Pi 5). This 'apples-to-oranges' comparison fails to objectively demonstrate the true architectural advantages of the asynchronous design against appropriate hardware-level baselines."*

**Response:**

We thank the reviewer for identifying that the original presentation did not isolate the architectural contribution of GALS. We have retained Table~2 as a model-level comparison: its 13 classifier rows, columns, and Raspberry Pi~5 measurements are unchanged, and its revised caption now states explicitly that these values characterize model inference on the common general-purpose ARM platform. FPGA implementation results are no longer interpreted through that table.

To provide an architecture-level baseline, we implemented a synchronous version of the same INT8 DA-SNN on the same Zynq-7020 FPGA using the same input tensor. The synchronous implementation replaces the two-island four-phase Req/Ack boundary with a single-clock ready/valid interface while retaining clock-enable control. It achieves 16.5~$\mu$s latency, 96~mW dynamic power, 107~mW static power, 203~mW total power, and 3.35~$\mu$J total energy per inference. Under the matched conditions, the GALS implementation achieves 18~$\mu$s latency, 40/108/148~mW dynamic/static/total power, and 2.66~$\mu$J total energy. Thus, the GALS implementation incurs a 9.09\% latency increase while reducing total energy by 20.6\%.

The concise comparison is now reported in the Hardware Implementation section, and the complete resource, timing, interface-latency, and energy results are provided in the Supplementary Information. We have also revised the Discussion to limit the conclusion to this matched implementation rather than making a universal asynchronous-versus-synchronous claim.

---

## L5. Practical Deployment Constraints (R3-6)

**Reviewer concern:** *"While the manuscript emphasizes potential wearable applications, there is limited discussion on practical constraints such as latency stability, memory footprint in real devices, or deployment scenarios. Expanding this part would strengthen the real-world relevance of the work."*

**Response:**

We thank the reviewer for this constructive suggestion. We have substantially expanded the discussion of practical deployment constraints in the revised manuscript. Below, we summarize the key quantitative analyses that have been added.

**Inference latency.** The FPGA accelerator completes a single inference in **0.018 ms**, which is approximately five orders of magnitude shorter than the EEG window duration (4–9 s depending on the dataset). Inference latency is therefore not the system bottleneck; the dominant temporal constraint is the EEG signal acquisition time itself. This confirms that the FPGA accelerator can comfortably operate within the temporal requirements of any standard EEG paradigm without introducing latency-related constraints on the sensing pipeline.

**Memory footprint.** The INT8-quantized DA-SNN model requires **12.50 KB** for parameter storage and **13.68 KB** for runtime activation memory, totaling **26.18 KB**. This is well below the SRAM capacity of typical microcontrollers used in wearable devices—for reference, the STM32L4 series offers 256 KB of SRAM, and even resource-constrained MCUs such as the STM32G0 series provide 8–36 KB. The complete model, including preprocessing buffers, can be accommodated within the on-chip memory of a single low-cost MCU without requiring external memory, eliminating the associated power and latency penalties of off-chip access.

**Deployment maturity and scope.** We have revised the manuscript to clearly state the current deployment maturity level: **laboratory-environment offline analysis validated on an FPGA prototype**. We do not claim that the current system is ready for deployment as a consumer wearable device. Real-world wearable deployment requires additional engineering efforts—including integration with analog front-end ICs, power management circuit design, on-body thermal and mechanical validation, and regulatory compliance testing—that are beyond the scope of the present algorithm–hardware co-design study.

**FPGA-to-ASIC migration path.** The current FPGA prototype serves as a functional validation platform. Migration to a custom ASIC implementation is expected to yield further improvements in area efficiency (eliminating FPGA routing overhead), dynamic power reduction (custom standard-cell logic versus configurable logic blocks), and energy per inference. Preliminary estimates based on typical FPGA-to-ASIC scaling factors suggest an order-of-magnitude reduction in both area and power, which we have noted as a forward-looking statement in the revised Discussion.
