# Response Letter: Controlled EEG Perturbations and Quantization

> **Superseded working draft.** The authoritative consolidated response is `response_to_reviewers.md`; status and risk tracking are in `response_tracker.md`. Do not submit this file separately.

## R3-3. Missing Reference Baselines for Robustness and Quantization

**Reviewer comment:** *"Although the manuscript presents results under different conditions (e.g., noise or quantization), these evaluations are not compared against a clear reference baseline under the same settings. Including a simple baseline curve would make the robustness claims more convincing and easier to interpret."*

**Response:**

We thank the reviewer for this suggestion. We have redesigned Fig. 3a to compare DA-SNN with DH-SNN and EEGNet under matched conditions on SEED, DEAP, and DREAMER. All three models use the same generated noisy feature bundle, random window-level 80/20 split, model seed, training schedule, checkpoint-selection rule, and evaluation level for each perturbation condition. The revised analysis covers Gaussian noise, low-frequency drift, and EMG-like transient bursts at relative noise levels (NLs) of 0.01, 0.03, 0.05, 0.08, 0.10, and 0.125, together with the clean condition.

At NL = 0.125, DA-SNN exhibits a smaller clean-to-noisy accuracy decrease than both reference models in all nine dataset--perturbation combinations. Across these combinations, the DA-SNN decrease ranges from 3.71 to 9.37 percentage points, compared with 7.13--15.61 points for DH-SNN and 5.09--11.40 points for EEGNet. Because this robustness experiment uses one model seed, we report the curves and endpoint differences descriptively and do not claim statistical significance. We have revised the Results text and figure caption accordingly.

---

## R4-19. Signed INT8 Quantization Range

**Reviewer comment:** *"The signed INT8 quantization uses a factor of 128. Standard symmetric INT8 quantization usually uses 127 to avoid mapping the largest positive value to 128 and then clipping it to 127. The authors should clarify whether the use of 128 is intentional and justify it."*

**Response:**

We agree with the reviewer. The factor of 128 in the original formula was not intended to define an asymmetric clipping rule. We have corrected the signed weight quantizer to use the symmetric range $[-127,127]$ with

\[
s_w=\frac{\max(\max|r|,\epsilon_q)}{127},\qquad
Q_s(r)=\operatorname{clip}\!\left(\operatorname{round}(r/s_w),-127,127\right).
\]

The additional INT8 code $-128$ is left unused. Nonnegative activations use an unsigned 8-bit range $[0,255]$ with zero-point 0. Both quantizers apply round-to-nearest followed by saturation. We have also clarified that the implementation uses per-tensor scales, quantization-aware training rather than post-training quantization, activation calibration on the complete SEED training partition used by ordinary training, and offline BN folding into the preceding convolution weights and biases. These definitions are now consistent across the quantization equations and hardware description.

---

## R4-22. Scope of the EEG Perturbation Experiment

**Reviewer comment:** *"Noise is injected into feature maps after fine-tuning, not into raw EEG before preprocessing. This does not model realistic wearable artifacts such as motion, EMG, EOG, electrode detachment, impedance drift, or sweat. The experiment is useful as a synthetic perturbation test, but it is not sufficient evidence for real wearable robustness."*

**Response:**

We agree that the original description and the associated wearable-robustness claim were too broad. In the revised experiment, perturbations are applied to time-domain EEG samples after dataset-specific signal conditioning and segmentation but before PSE extraction, spatial mapping, and LDS smoothing. All downstream features are therefore recomputed from the perturbed signal samples; no perturbation is added directly to the PSE feature maps. We now describe this procedure as a controlled signal-level perturbation test rather than as validation of real-world wearable robustness.

The revised evaluation includes three synthetic perturbation families: additive Gaussian noise, low-frequency drift, and EMG-like transient bursts. We have removed the unsupported attribution of the observed behavior to TTFS encoding or adaptive temporal windows because the experiment compares complete models and does not isolate the mechanism responsible for the difference. We also state explicitly that synthetic perturbations do not reproduce the full distribution of naturally occurring motion, electrode-contact, sweat, ocular, or muscular artifacts in long-term wearable recordings.

---

## R4-23. Relative Noise Levels and EEG-Like Interference

**Reviewer comment:** *"Robustness should be tested with realistic SNR for common EEG experiments. One reference cites values Relative Noise Level (NL) ranging from 0.05 to 0.125."*

**Response:**

We thank the reviewer for identifying this missing range. The revised evaluation defines the relative noise level per channel as $\mathrm{NL}=\sigma_{\mathrm{noise}}/\sigma_{\mathrm{signal}}$ and evaluates NL = 0.01, 0.03, 0.05, 0.08, 0.10, and 0.125. The sweep therefore includes the suggested 0.05--0.125 interval while retaining lower levels to show the onset of degradation.

To broaden the test beyond white noise, we added low-frequency drift and EMG-like transient bursts on SEED, DEAP, and DREAMER. Perturbation generators receive the dataset-specific sampling rate (200 Hz for SEED and 128 Hz for DEAP and DREAMER), and EMG carrier bands are constrained below the corresponding Nyquist frequency. The Supplementary Methods now report the injection stage, NL definition, generator construction, matched model protocol, and single-seed boundary. We interpret the resulting curves as controlled comparative sensitivity evidence, not as a substitute for evaluation on recordings containing naturally occurring wearable artifacts.
