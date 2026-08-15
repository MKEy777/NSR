# Response to the Reviewers

Manuscript: “An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition”  
Journal: National Science Review  
Decision: Major revision  

Dear Editor and Reviewers,

We have revised the manuscript in response to the reviewers' comments. The point-by-point responses below identify the corresponding sections, equations, figures, tables, and Supplementary Information.

## Response to Reviewer 1

We thank Reviewer 1 for the careful and constructive comments. We have revised the manuscript accordingly, as detailed below.

### R1-1

> Although results are reported on five datasets, it is not clear how the experiments are actually conducted. For instance, the 96.98% accuracy on SEED is reported without specifying whether it is based on subject-dependent training or a cross-session setting. The same issue appears for DEAP and DREAMER, where the data splitting strategy is not described.

Response

Main Table 1 now identifies the evaluation on all five datasets as a subject-dependent, class-stratified random window-level 80/20 benchmark; the SEED result is therefore not a cross-session evaluation. The 96.98% SEED accuracy cited in the comment was obtained under this protocol with seed 42, while the revised table reports 96.85% ± 1.44% across seeds 1–5. We also added subject-independent evaluations using LOSO for SEED, SEED-IV, and SEED-V and five fixed subject-holdout splits for DEAP and DREAMER, with 26/6 and 19/4 train/held-out subjects, respectively.

Locations: Main Table 1 and “Emotion Recognition Performance Across EEG Benchmarks”; Supplementary Methods “Evaluation Protocols, Model Selection, and Statistics”; Supplementary Tables S3–S5.

### R1-2

> The role of some key components is also not very clear. The paper attributes performance gains to the adaptive temporal window and the gating mechanisms, but the main text does not really show what is happening in practice. The supplementary material includes some theoretical discussion, but in the main paper there is little evidence to support these claims.

Response

We added two complementary forms of evidence. The revised main Results report matched ablations on SEED, DEAP, and DREAMER across five random seeds: replacing the adaptive temporal window with fixed windows reduces mean accuracy by 4.98, 10.75, and 0.83 percentage points, respectively, while removing DSGM reduces it by 3.20, 17.58, and 0.37 points. Supplementary Fig. S3 also shows a representative training trajectory in which the two hidden-layer temporal boundaries evolve to different ranges and settle during late training.

Locations: Main Results “Emotion Recognition Performance Across EEG Benchmarks”; Supplementary “Ablation Studies”, Table S6 and Fig. S3.

### R1-3

> The ablation study is quite limited. It is only done on the SEED dataset, and the main modules are not tested on DEAP or DREAMER, where the signal properties and channel configurations are different. Without these results, it is difficult to tell whether the improvements are consistent across datasets.

Response

We expanded the ablation study from SEED to SEED, DEAP, and DREAMER. The complete DA-SNN, standard convolution, removal of DSGM, conventional min–max normalization, and fixed temporal windows were evaluated under the same subject-dependent random window-level 80/20 protocol using random seeds 1–5. The adaptive temporal window and DSGM improve mean accuracy on all three datasets, with effect sizes that vary across datasets and are smallest on DREAMER.

Locations: Main Results “Emotion Recognition Performance Across EEG Benchmarks”; Supplementary “Ablation Studies” and Table S6.

### R1-4

> The hardware section is not very easy to follow. In Fig. 4(a), the interaction between the synchronous and asynchronous parts is not clearly illustrated, and the handshake mechanism is only briefly mentioned. It is also not very clear how the claimed energy efficiency of the GALS design is achieved, for example, how it relates to event sparsity or clock gating.

Response

We revised the Fig. 4 legend, the Hardware Implementation section, and the Supplementary hardware-control description to identify the two locally synchronous clock islands and the AER clock-domain-crossing boundary. The revised text describes the bundled-data four-phase sequence: the sender stabilizes the address/timestamp payload and asserts Req; synchronized Req enables the receiver; the receiver asserts Ack after completing the event update; Req and Ack then return low before the payload may change. Req and Ack use two-stage synchronizers in their receiving domains, while the multi-bit payload remains stable throughout the transfer.

The revision also separates three efficiency mechanisms. Model-induced spike sparsity reduces event transfers, weight reads, and membrane updates; event-triggered execution activates routing, memory, and CU/PE operations for valid events; and local register clock enables reduce idle dynamic switching.

Locations: Fig. 4 legend; “Hardware Implementation”; Supplementary “Detailed Hardware Control Protocol”, Fig. S1, Tables S9–S10, and “FPGA Deployment Comparisons”.

### R1-5

> There are also some inconsistencies in terminology. Terms like "temporal window," "time window," and "spiking window" are used in different places without clear distinctions. The model naming is also not consistent (e.g., DA-SNN, ATSNN, adaptive SNN). In Table 1, metrics such as Acc, F1, and Spe are reported, but their definitions are not clearly given in the main text.

Response

We standardized the terminology throughout the main text and Supplementary Information. DA-SNN denotes the complete model, whereas ATSNN denotes its temporal spiking classifier. “Outer window” now refers to EEG segmentation, “PSE temporal bin” to the subdivisions used for feature extraction, and “layer-wise temporal window” to the B1/ATSNN interval; the generic terms “time window” and “spiking window” have been replaced where they referred to these defined objects.

Main Table 1 now defines Acc as window-level accuracy, F1 as macro-F1, and Spe as macro-specificity. Macro-specificity is the unweighted mean of one-versus-rest specificity across classes. The Supplementary Methods provide the corresponding formulas, aggregation rules, and sample-standard-deviation convention.

Locations: Main Table 1 note; main text and Supplementary Information throughout; Supplementary “Evaluation Protocols, Model Selection, and Statistics”.

### R1-6

> Fig. 4 does not clearly indicate whether the data is represented as tensors or spike events, which makes the processing pipeline difficult to follow.

Response

The revised Fig. 4 legend and accompanying hardware description now define the representation boundary explicitly. Dense INT8 tensor data pass through the input buffers, tensor compute engine, multi-branch fusion path, and DF-TTFS encoder. DF-TTFS is the tensor-to-event conversion point. Downstream AER packets carry a spike address and timestamp through the event interface and CU/PE arrays, while hidden-layer events recirculate through the spike collector and AER path. The final layer supplies membrane potentials to a comparator-tree decision unit.

Locations: Fig. 4 legend; “Hardware Implementation”.

### R1-7

> The introduction provides general background, but the specific research gap is not stated very clearly. The motivation for combining asynchronous hardware with EEG-based SNNs could be explained more directly, especially in relation to existing methods.

Response

We revised the Introduction to state the gap directly while retaining the original motivation. Affective neural activity motivates event-based representations, but scalp EEG is continuously sampled and is not itself a hardware-ready event stream. DA-SNN converts EEG-derived features into sparse spike events; if those events are still handled by continuously active synchronous datapaths and memory transfers, part of the model-level sparsity benefit can be lost. This motivates coupling event generation in the EEG SNN with a GALS substrate that transfers valid events between locally synchronous domains and activates the required data-movement and compute paths.

Location: Introduction, particularly the paragraphs on dense execution, the model-to-hardware gap, and the final SNN–GALS motivation.

---

## Response to Reviewer 2

We thank Reviewer 2 for the careful and constructive comments. We have revised the manuscript accordingly, as detailed below.

### R2-1

> In the efficiency analysis, the hardware comparison is fundamentally unbalanced. The energy efficiency of the proposed GALS accelerator, deployed on a customized FPGA, is compared directly against conventional lightweight CNNs running on a general-purpose ARM processor (Raspberry Pi 5). This "apples-to-oranges" comparison fails to objectively demonstrate the true architectural advantages of the asynchronous design against appropriate hardware-level baselines.

Response

Main Table 2 now presents a model-level comparison on the common Raspberry Pi 5 platform. To isolate the effect of the clock organization, we implemented a synchronous version of the same INT8 DA-SNN on the same Zynq-7020 FPGA with the same input tensor and clock-enable policy; relative to this matched implementation, GALS increases latency from 16.5 to 18 μs and adds 172 LUTs and 139 FFs while reducing total energy from 3.35 to 2.66 μJ per inference. We also deployed EEGNet on the Zynq-7020: GALS DA-SNN uses more resources and 148 versus 138 mW total power, while reducing latency from 0.772 ms to 18 μs and energy from 106.536 to 2.66 μJ per inference. The matched DA-SNN comparison evaluates the clock organization, and EEGNet provides a cross-model FPGA deployment baseline in Supplementary Table S11.

Locations: Main Table 2 caption; “Hardware Implementation” and Discussion; Supplementary “FPGA Deployment Comparisons”, Table S11.

### R2-2

> Affective EEG signals are highly subject-dependent. While the paper reports exceptionally high accuracies across datasets, it fails to explicitly state whether these results are derived from "within-subject" or "cross-subject" (leave-one-subject-out) cross-validation. Given the wearable context, the omission of clear cross-subject generalization metrics is a major empirical flaw.

Response

Main Table 1 now explicitly reports the subject-dependent random window-level 80/20 benchmark. The Supplementary Information adds LOSO evaluation for SEED, SEED-IV, and SEED-V and five fixed subject-holdout splits for DEAP and DREAMER. Under these subject-independent settings, DA-SNN ranks first in accuracy, macro-F1, and macro-specificity among the ten evaluated models on all five datasets.

Locations: Main Table 1 and Results; Supplementary “Evaluation Protocols, Model Selection, and Statistics”, “Subject-Independent Generalization Across EEG Benchmarks”, and Tables S3–S5.

### R2-3

> The methodology relies heavily on Linear Dynamical System (LDS) smoothing to filter the feature sequences across windows. LDS smoothing inherently requires observing sequences over time, which introduces significant computational latency, memory buffering, and complex matrix operations. The manuscript entirely fails to address how this computationally expensive, latency-inducing smoothing process is executed in real-time on the proposed resource-constrained edge hardware. Ignoring the front-end preprocessing cost renders the "real-time wearable" deployment claims highly questionable.

Response

The reported 18 μs latency and 2.66 μJ energy cover accelerator inference from a preprocessed input tensor to the class output; PSE extraction and trial-wise LDS smoothing are outside this measurement. We implemented PSE and LDS as independent kernels on the same FPGA board and report their measurements in Supplementary Tables S7–S8. The PSE measurement covers one 200-sample call, and the LDS measurement covers 288 lanes over three test steps (864 outputs).

Locations: Abstract; “Hardware Implementation”; Discussion and Conclusion; Supplementary “Hardware Measurement Boundary and Standalone Preprocessing Kernels”, Tables S7–S8.

### R2-4

> The authors acknowledge in the Discussion that long-term wearable deployment faces severe challenges from individual state variations and electrode impedance drift. However, for a system whose primary selling point is enabling "continuous wearable monitoring," the complete absence of any implemented online adaptive or calibration mechanism is a critical functional gap in the proposed framework.

Response

The current prototype uses fixed parameters trained offline and does not implement online learning or recalibration. The Discussion and Conclusion now identify session-level calibration and selective parameter adaptation as future extensions.

Locations: Discussion and Conclusion.

### R2-5

> The Globally Asynchronous Locally Synchronous (GALS) architecture relies on a complex four-phase handshake protocol and Address-Event Representation (AER) routing to cross clock domains. The authors praise the energy reduction from sparse compute activation but completely ignore the significant dynamic power, physical area footprint, and latency overhead inherently introduced by the AER routing logic, threshold filters, and metastability-prevention synchronizers. Without a transparent, component-level breakdown of the GALS interface overhead, the isolated 40 mW dynamic power figure is incomplete and highly misleading.

Response

The revised manuscript provides an interface breakdown covering event-valid filtering, AER routing, address decoding, Req/Ack synchronizers, four-phase handshake state machines, and clock-enable control. Top-level hierarchical synthesis attributes 981 LUTs and 602 FFs to these six components, with their functional latencies reported individually.

Locations: “Hardware Implementation” and Discussion; Supplementary Tables S7, S9–S10, and S12, together with “FPGA Deployment Comparisons”.

### R2-6

> There is a highly noticeable and strange inconsistency in the manuscript's formatting. Specifically, Table 1 and Table 2 are completely different in size, scale, and layout. This glaring visual discrepancy looks highly unprofessional and severely disrupts the reading experience.

Response

We revised both main tables to use the same typographic language: booktabs rules without vertical lines or shading, consistent caption style, unit placement in column headers, abbreviation definitions, numeric precision, and restrained boldface. Table 1 remains wider because it reports 15 metrics across five datasets, whereas Table 2 remains a compact efficiency table; the difference in information density no longer produces unrelated styling.

Locations: Main Tables 1 and 2.

---

## Response to Reviewer 3

We thank Reviewer 3 for the careful and constructive comments. We have revised the manuscript accordingly, as detailed below.

### R3-1

> The manuscript reports only average performance metrics across datasets, without providing measures of variability such as standard deviation. Considering the inherent variability in EEG signals across subjects and trials, including statistical dispersion would improve the credibility and robustness of the reported results.

Response

Main Table 1 and the cross-dataset ablations now report DA-SNN results as mean ± sample standard deviation across random seeds 1–5. The SEED-family LOSO tables report mean ± sample standard deviation across held-out subjects. For DEAP and DREAMER, Supplementary Table S5 reports mean ± sample standard deviation across five fixed subject-holdout splits, using 26/6 and 19/4 train/held-out subjects, respectively. These summaries quantify seed, held-out-subject, or held-out-subject-composition variability; trial-level dispersion was not estimated separately.

Locations: Main Table 1 note; Supplementary “Evaluation Protocols, Model Selection, and Statistics”; Tables S4–S6.

### R3-2

> The manuscript uses terms such as "temporal window," "time window," and "spiking window" interchangeably without clearly distinguishing their meanings. In addition, the model naming (e.g., DA-SNN, ATSNN, adaptive SNN) is not consistent throughout the paper, which may lead to confusion. A more consistent use of terminology would improve the overall readability.

Response

We standardized the terminology across the main text and Supplementary Information. DA-SNN denotes the complete architecture, and ATSNN denotes its temporal spiking classifier. We use “outer window” for EEG segmentation, “PSE temporal bin” for feature-extraction subdivisions, and “layer-wise temporal window” for the B1/ATSNN interval; the generic names “adaptive SNN”, “time window”, and “spiking window” have been replaced where they referred to these defined objects.

Locations: Main text and Supplementary Information throughout; definitions are concentrated in “Neuromorphic framework for EEG emotion recognition”, Fig. 2, and Supplementary Methods.

### R3-3

> Although the manuscript presents results under different conditions (e.g., noise or quantization), these evaluations are not compared against a clear reference baseline under the same settings. Including a simple baseline curve would make the robustness claims more convincing and easier to interpret.

Response

We redesigned Fig. 3a to compare DA-SNN with DH-SNN and EEGNet under matched perturbation conditions on SEED, DEAP, and DREAMER. Within each condition, the models use the same generated noisy data bundle, random window-level 80/20 split, model seed, training schedule, checkpoint-selection rule, and evaluation level. The revised analysis covers Gaussian noise, low-frequency drift, and EMG-like transient bursts at NL values from 0.01 to 0.125, together with the clean condition.

At NL = 0.125, DA-SNN shows the smallest clean-to-noisy accuracy decrease in all nine dataset–perturbation combinations. Because the analysis uses one model seed and noise-matched retraining rather than a fixed clean-trained checkpoint, the curves are interpreted descriptively and no statistical significance or zero-shot robustness is claimed. Fig. 3b separately reports the weight-bit-width sweep; we do not treat that sweep as a cross-model robustness comparison.

Locations: Fig. 3a–b; “Sensitivity to Controlled EEG Perturbations and Quantization”; Supplementary “Controlled EEG Perturbation Protocol”.

### R3-4

> While the overall pipeline is described, the connection between the continuous EEG features, the encoding process, and the spiking neural network is not sufficiently detailed. Providing a clearer description of data transformations at each stage would improve the understanding of the end-to-end system.

Response

We added a stepwise representation description. Continuous EEG is z-score normalized and divided into non-overlapping outer windows; PSE is calculated in temporally contiguous bins; electrode values are projected to a topographic grid; and the maps are stacked into a dense tensor in $\mathbb{R}^{N_f\times H\times W}$. DSGM refines this dense tensor, and DF-TTFS then defines the dense-to-event boundary by mapping it to a shape-matched spike-time representation for ATSNN classification.

Locations: “Neuromorphic framework for EEG emotion recognition”; Fig. 2 legend; Supplementary “EEG Data Preprocessing” and the DSGM dimension descriptions.

### R3-5

> Some important experimental settings, such as training epochs, optimization strategies, or hardware-related configurations, are only briefly mentioned or scattered across sections. Consolidating these details would improve reproducibility.

Response

We consolidated the software environment, optimizer, learning-rate schedule, batch size, maximum epochs, early-stopping settings, initialization, loss, random seeds, FPGA device, and evaluation protocols in the Supplementary Methods. Table S3 additionally reports dataset composition, outer-window/PSE-bin construction, and subject-dependent and subject-independent split definitions.

Locations: Supplementary “Implementation Details” and “Evaluation Protocols, Model Selection, and Statistics”; Tables S2–S3.

### R3-6

> While the manuscript emphasizes potential wearable applications, there is limited discussion on practical constraints such as latency stability, memory footprint in real devices, or deployment scenarios. Expanding this part would strengthen the real-world relevance of the work.

Response

We expanded the Discussion to report the measured 18 μs accelerator latency, 12.50 KB parameter storage, and 13.68 KB runtime memory, together with the standalone PSE and LDS kernel measurements. It also addresses system-integration requirements for EEG acquisition, sensor interfaces, communication, battery operation, preprocessing buffers, and acquisition-to-decision latency. Subject/session shift, naturally occurring artifacts, sensor variability, online adaptation, and the attainable ASIC area and power envelope are identified as deployment questions for future validation.

Locations: Discussion and Conclusion; Supplementary Tables S7–S12.

---

## Response to Reviewer 4

We thank Reviewer 4 for the careful and constructive comments. We have revised the manuscript accordingly, as detailed below.

### R4-1

> The abstract should distinguish EEG sparsity from model-induced SNN sparsity.  
> The current wording suggests that affective EEG is intrinsically event-driven and temporally sparse, and that the hardware directly exploits this raw EEG sparsity. However, the model first transforms EEG into windowed PSE feature maps, applies spatial mapping and LDS smoothing, and only then imposes spike-time sparsity through DF-TTFS encoding. Unless the authors quantify sparsity in raw EEG or pre-TTFS features, the abstract should state more accurately that DA-SNN converts EEG-derived spatial-spectral features into sparse spike-time events for efficient inference.

Response

The revised Abstract states that scalp EEG is acquired continuously, DA-SNN converts EEG-derived features into sparse spike events, and GALS exploits those model-induced events. The Introduction and Results now use the same representation boundary.

Locations: Abstract; Introduction; “Neuromorphic framework for EEG emotion recognition”.

### R4-2

> The prose should be revised carefully before publication.  
> Several parts of the abstract and main text read overly generic and insufficiently polished. I recommend paragraph-by-paragraph language revision to improve specificity, scientific tone, and technical precision. We note that ChatGPTzero identifies 95% as generated by AI.

Response

We performed a paragraph-by-paragraph language revision across the main text and Supplementary Information. Repetitive openings, generic significance statements, promotional modifiers, and absolute wording were replaced with specific descriptions of the evidence, while terminology, paragraph logic, formula integration, captions, and abbreviations were standardized.

Locations: Abstract and manuscript-wide; particularly the Introduction, Results transitions, Discussion, Conclusion, captions, and Supplementary Methods.

### R4-3

> The symbol "@" in Fig. 2 is unclear.  
> The figure repeatedly uses the symbol "@", but its meaning is not defined in the caption or main text. From context, it may refer to a tensor dimension such as $C \times H \times W$, but this should be explicitly clarified.

Response

The Fig. 2 legend now defines the at sign as a compact shape separator rather than an arithmetic operator. A label of the form $C@H\times W$ denotes $C$ feature channels arranged on an $H\times W$ spatial grid. Exact dataset-specific integer dimensions are provided in the Supplementary Information.

Location: Fig. 2 legend.

### R4-4

> The dimensions $C$, $H$, and $W$ should be precisely defined.  
> The text suggests that these are the channel, height, and width dimensions of the model input, but it is not fully clear how the EEG-derived PSE feature map is mapped into this tensor. The relationship between EEG channels, PSE segments, spatial grid size, and the model input dimensions should be stated explicitly.

Response

For the first model input, the revised text defines $C=N_f$ as the number of temporally contiguous PSE maps within one outer window. EEG electrodes do not form the feature-channel axis; each electrode’s PSE value is placed at its montage-defined location on the $H\times W$ topographic grid, and the $N_f$ maps are stacked into one tensor. In later layers, $C$ denotes learned feature channels. The dataset-specific inputs are $4\times8\times9$ for the SEED family, $6\times6\times7$ for DEAP, and $9\times4\times5$ for DREAMER, excluding the batch axis.

Locations: “Neuromorphic framework for EEG emotion recognition”; Fig. 2 legend; Supplementary preprocessing and dataset-specific implementation dimensions.

### R4-5

> Notation for elementwise multiplication should be unified.  
> The main text uses the Hadamard product notation, while Fig. 2 appears to use a different machine-learning notation. The authors should adopt one notation consistently throughout the paper and figures.

Response

The equations now use $\odot$ consistently for the Hadamard product. The circled multiplication node in Fig. 2 is explicitly defined in the legend as the same element-wise operation represented by $\odot$ in the equations.

Locations: DSGM fusion equation and Fig. 2 legend.

### R4-6

> Equation punctuation and typesetting should be standardized.  
> Some equations end without proper punctuation, while others use inconsistent punctuation. For a polished mathematical manuscript, equations should be integrated grammatically with commas or periods where appropriate.

Response

We reviewed the displayed equations in the main text and Supplementary Information and standardized punctuation according to grammatical function. Equations that complete a sentence now end with a period, whereas equations followed by a continuing “where” or “for” clause end with a comma. We also revised the description following the censored B1 forward equations to identify the threshold-crossing expression, active-spike indicator, and upper-bound censoring rule explicitly.

Locations: Main DSGM, B1, DF-TTFS, adaptive-window, and output-readout equations; Supplementary preprocessing, B1, DF-TTFS, gradient, adaptive-window, readout, and quantization equations.

### R4-7

> The DSGM tensor dimensions require clarification.  
> The channel gate is written as $G_{\mathrm{ch}} \in \mathbb{R}^{C\times1\times1}$, while the spatial gate is $G_{\mathrm{sp}} \in \mathbb{R}^{1\times H\times W}$. If the pointwise convolution changes the number of channels or the spatial size, then $F_{\mathrm{DS}} \odot G_{\mathrm{ch}} \odot G_{\mathrm{sp}}$ is not well-defined unless broadcasting, padding, and resizing conventions are explicitly specified.

Response

We revised the DSGM formulation around an aligned tensor $U\in\mathbb{R}^{C_o\times H'\times W'}$. The main path preserves this shape, the channel gate has shape $C_o\times1\times1$ and broadcasts over $H',W'$, and the spatial gate has shape $1\times H'\times W'$ and broadcasts over $C_o$. The Supplementary Information now lists every kernel, stride, padding, group count, input/output shape, and broadcasting axis. No resizing is used at fusion.

Locations: Main DSGM equations and the sentence following the fusion equation; Supplementary operation-level and dataset-specific DSGM dimensions.

### R4-8

> The terminology "B1 spiking neuron model" should be aligned with the original paper.  
> The original authors refer to the model as the "B1-model." I recommend using the same terminology to avoid ambiguity and to make the connection to the reference framework clearer.

Response

We standardized the running-text term to “B1 model” throughout the main text and Supplementary Information. At first mention, we note that the original report terms it the “B1-model”, attribute it to Stanojević et al., and identify it as the inherited neuron-level spike-time substrate used by ATSNN. We use the unhyphenated form consistently thereafter.

Locations: Main B1 model introduction; Supplementary “B1 Model Definition and Forward Semantics”.

### R4-9

> The threshold $\vartheta$ should be defined before first use.  
> The membrane threshold appears in Eq. (6) and later in the paper, but it is not clearly introduced in the main text before its first use. The authors should define its meaning, units, and role in the B1/ATSNN dynamics.

Response

The revised text defines $\vartheta_i^{(n)}$ at first use as the firing threshold of neuron $i$ in layer $n$, expressed in normalized membrane-potential units. It also explains that $\epsilon>0$ converts $\epsilon\vartheta_i^{(n)}$ into the threshold-related temporal offset in the theoretical crossing-time equation.

Locations: Main paragraph following the B1 dynamics equation; Supplementary B1 model definition.

### R4-10

> The B1 reference model should be discussed more substantially.  
> A substantial part of the ATSNN formulation appears to rely on the B1 model of Stanojevic et al. However, the paper only briefly cites it. The authors should explain why B1 was selected, especially because the B1 identity mapping is equivalent to a ReLU network, follows similar learning trajectories, and has known gradient-stability properties. The manuscript should also clarify whether the proposed model relies on these properties or only uses B1 as an inspiration.

Response

The revised text states that ATSNN adopts the B1 model's piecewise-linear constant-slope dynamics, single-spike representation, cascaded layer-wise temporal windows, and identity-mapping rationale. We selected this formulation as a tractable spike-time substrate with a defined latency–ReLU correspondence. The text also distinguishes the inherited B1 formulation from ATSNN's midpoint-referenced signed window update and its integration with DSGM, DF-TTFS, and GALS; the identity mapping is presented as the model-selection rationale.

Locations: Main B1 model introduction and adaptive-window paragraph; Supplementary “B1 Model Definition and Forward Semantics”.

### R4-11

> Basic B1 definitions and assumptions should be added to the supplement.  
> Supplementary Section 2.1 currently gives only a minimal description. It should include the key assumptions of the B1 framework, including the role of the identity mapping, the active/inactive mask, the threshold-crossing slope, and the relation between spike time and ReLU activation.

Response

The Supplementary Information now defines the identity parameterization $A_i^{(n)}=0$, $B_i^{(n)}=1$, the half-open single-spike window, cascaded window boundaries, theoretical crossing time, active/inactive mask, strict upper-bound convention, unit threshold-crossing slope, and latency–ReLU mapping under the assumptions of the original B1 work. It also distinguishes these inherited definitions from the ATSNN window-update rule and the broader DA-SNN integration.

Location: Supplementary “B1 Model Definition and Forward Semantics”.

### R4-12

> Eq. (6) is not entirely the closed-form integral of Eq. (5).  
> Around lines 30–31, the authors state that Eq. (6) is the closed-form solution obtained by integrating Eq. (5). This is not strictly correct. The first expression defining the theoretical threshold-crossing time
>
> can be interpreted as the closed-form threshold-crossing time of a simplified B1-type neuron. However, the second expression,
>
> which defines the clipped or observed time,
>
> is not obtained by direct integration of the ODE. It is an additional hybrid censoring or timeout rule imposed at the upper temporal boundary. The authors should reformulate Eq. (6) as a censored first-passage-time model and introduce an explicit active-spike mask:
>
> The model should propagate the active mask and observed spike time together through the network.

Response

We separated the forward computation into three quantities: the theoretical first-passage time $\tilde{T}_i^{(n)}$, the active mask $M_i^{(n)}=\mathbf{1}[\tilde{T}_i^{(n)}<T_{\max}^{(n)}]$, and the stored time $T_i^{(n)}=M_i^{(n)}\tilde{T}_i^{(n)}+(1-M_i^{(n)})T_{\max}^{(n)}$. The manuscript identifies the first expression as the threshold-crossing solution and the latter two as the censoring/timeout semantics. Algorithm 1 returns both the stored times and the masks.

Locations: Main censored B1 forward equations; Supplementary “B1 Model Definition and Forward Semantics” and Algorithm 1.

### R4-13

> Eq. (8) needs a numerical safeguard.  
> The DF-TTFS scaling factor becomes unstable if $V_{\max} = V_{\min}$. The authors should use a safeguarded expression such as  
> $S_p = 2^{\lceil \log_2(\max(V_{\max} - V_{\min}, \delta)) \rceil}$,  
> with a small $\delta > 0$.

Response

We added the safeguarded scale $S_p=2^{\lceil\log_2(\max(V_{\max}-V_{\min},\delta))\rceil}$ with $\delta=10^{-5}$ in float32 training. If $V_{\max}=V_{\min}$, the scale remains positive, normalized activations become zero, and the encoder returns the boundary code rather than dividing by zero. The exponent is retained as an integer shift count for fixed-point inference.

Locations: Main DF-TTFS equation; Supplementary “Division-Free TTFS Encoding Derivation”.

### R4-14

> Boundary cases should be treated more carefully.  
> The behavior at $T = T_{\max}$ is ambiguous. A neuron firing exactly at $T_{\max}$ and a silent neuron clipped to $T_{\max}$ are represented by the same scalar value. This affects forward propagation, output readout, and gradients. The active-spike mask would resolve this ambiguity.

Response

We adopted a half-open interval: a spike is active only when $\tilde{T}_i^{(n)}<T_{\max}^{(n)}$, and equality belongs to the inactive/censored case. The stored boundary time is therefore a placeholder, while validity is determined by the mask. The cascade condition makes this placeholder equal to the next layer’s reference time, producing zero temporal offset in the forward map; the mask remains explicit for event selection, window adaptation, output-readout equivalence, and gradient analysis.

Locations: Main censored B1 forward equation and output readout; Supplementary B1 model definition, Algorithm 1, and masked readout.

### R4-15

> The gradient-stability argument around Eq. (9) is too weak.  
> Eq. (9) gives only the local derivative of an active neuron's spike time with respect to a synaptic weight. However, vanishing or exploding gradients in a deep TTFS network are controlled by the product of layer-wise spike-time Jacobians, not by this local temporal offset alone. The B1 paper analyzes the full masked Jacobian, whose spectrum depends on the active-neuron mask and the fixed-slope identity condition. The submitted manuscript does not derive the corresponding Jacobian for DA-SNN and does not show that the adaptive window keeps the multilayer Jacobian spectrum bounded.

Response

Equation (9) is now presented as a local active-neuron weight-gradient relation, and the Supplementary Information now gives the corresponding mask-aware layer-wise Jacobian $\mathbf{J}^{(n)}=\mathbf{D}^{(n)}\mathbf{W}^{(n)}$ together with its multilayer chain product. This makes explicit how active neurons determine the feed-forward paths through which spike-time perturbations and gradients propagate in DA-SNN.

Locations: Abstract; main ATSNN temporal-window paragraph; Discussion; Supplementary “Local Weight-Gradient Relation and Adaptive Temporal-Window Regulation”.

### R4-16

> The authors should reproduce a B1-style Jacobian-spectrum experiment.  
> To support the claim that ATSNN stabilizes gradients, the authors should reproduce an analogue of Fig. 2 from the B1 paper under their own DA-SNN/ATSNN conditions. They should initialize weights using standard deep-learning initialization, compute the layer-wise spike-time Jacobian with active-neuron masks, and examine whether eigenvalues remain inside or near the unit circle. This should be shown for both fixed-window and adaptive-window ATSNN. Without this analysis, the stability claim remains heuristic.

Response

Because the revised manuscript does not make a network-level gradient-stability claim, we did not add the requested Jacobian-spectrum experiment. The adaptive-window mechanism is now described through its implemented rule, local derivative, and cross-dataset ablation results.

Locations: Abstract; main ATSNN temporal-window paragraph; Discussion; Supplementary “Local Weight-Gradient Relation and Adaptive Temporal-Window Regulation”.

### R4-17

> Algorithm 1 has an undefined-variable issue.  
> In training mode, the earliest-valid-spike variable is assigned only if the valid-spike set $V$ is nonempty. If all neurons are silent or censored, then $V = \emptyset$, the assignment is skipped, and the later update still uses that variable. The authors should define a fallback rule, such as keeping the current upper boundary or expanding the window when no valid spikes occur.

Response

We revised Algorithm 1 so that the updated boundary is initialized to the current boundary before the valid-spike test. The valid set is defined by the active mask. If it is empty, no earliest-spike variable is formed and the initialized value is retained, giving the explicit fallback $T_{\max}^{(n)\prime}=T_{\max}^{(n)}$. When an update occurs, a minimum width $\delta_T=10^{-4}$ prevents a degenerate interval.

Location: Supplementary adaptive-window definition and Algorithm 1.

### R4-18

> Eq. (11) should include an active-spike mask.  
> The output logit sums over presynaptic spike times, but if silent neurons are represented numerically by $T_{\max}$, they may be treated as valid late spikes. The logit should include a presynaptic mask so that only neurons that actually fired contribute to the readout.

Response

We made the output semantics explicit. The output layer is continuous and nonspiking, with $T_{\min}^{(L)}=T_{\max}^{(L-1)}$. An inactive hidden neuron stores $T_j^{(L-1)}=T_{\min}^{(L)}$ and therefore contributes zero to the observed-time readout. The revised equation displays the algebraic equality between this implementation and an explicitly masked expression, for which the boundary placeholder contributes zero.

Locations: Main output-logit equation; Supplementary “Continuous output readout and inactive-neuron semantics”.

### R4-19

> The INT8 quantization formula should be checked.  
> The signed INT8 quantization uses a factor of 128. Standard symmetric INT8 quantization usually uses 127 to avoid mapping the largest positive value to 128 and then clipping it to 127. The authors should clarify whether the use of 128 is intentional and justify it.

Response

We corrected the signed weight quantizer to use the symmetric range $[-127,127]$, leaving the additional INT8 code $-128$ unused. Nonnegative activations use the unsigned range $[0,255]$ with zero point 0. Both quantizers use per-tensor scales, round-to-nearest, and saturation. The revision also specifies quantization-aware training, activation calibration from the training partition only, and offline batch-normalization folding.

Location: Supplementary “Quantization Strategy”.

### R4-20

> The validation protocol is under-specified and may inflate accuracy.  
> The paper reports high accuracy across SEED, SEED-IV, SEED-V, DEAP, and DREAMER, but it does not clearly state whether splits are subject-dependent, subject-independent, cross-session, cross-trial, or random window-level. This is critical because the preprocessing uses overlapping windows. If adjacent windows from the same trial enter both training and test sets, the reported performance may be inflated.

Response

The outer windows are non-overlapping: the SEED family uses 4 s windows with 4 s stride, and DEAP and DREAMER use 9 s windows with 9 s stride; the shorter 1 s or 1.5 s quantities are PSE temporal bins within an outer window. In the subject-dependent benchmark, LDS smoothing is applied separately to each complete trial before the random window-level split, so different windows from the same trial may enter both partitions. No separate validation subset was used; the held-out evaluation partition serves checkpoint selection and final reporting. The subject-independent evaluations hold out complete subjects and confine LDS smoothing within each trial, with the held-out-subject partition likewise used for checkpoint selection.

Locations: Main Table 1 note and Results; Supplementary “EEG Data Preprocessing” and “Evaluation Protocols, Model Selection, and Statistics”; Tables S1 and S3–S5.

### R4-21

> The DF-TTFS contribution should be framed as hardware efficiency, not accuracy improvement.  
> In the ablation, replacing DF-TTFS with standard min-max normalization slightly improves accuracy from 96.98% to 97.04%. Therefore, DF-TTFS should not be presented as the best-performing encoding method in terms of accuracy. Its contribution is hardware efficiency through division removal.

Response

The original SEED values cited in the comment, 96.98% for DF-TTFS and 97.04% for conventional min–max normalization, were obtained with seed 42. In the revised results across seeds 1–5, the corresponding accuracies are 96.85% and 96.91%; both comparisons give a +0.06 percentage-point difference. Across SEED, DEAP, and DREAMER, conventional min–max normalization changes mean accuracy by +0.06, −1.07, and +0.66 percentage points, respectively. The revised manuscript presents DF-TTFS as a hardware-oriented encoding that replaces floating-point division with power-of-two scaling while preserving competitive accuracy.

Locations: Main cross-dataset ablation paragraph; Supplementary “Ablation Studies” and Table S6.

### R4-22

> The robustness experiment is insufficient for wearable deployment claims.  
> Noise is injected into feature maps after fine-tuning, not into raw EEG before preprocessing. This does not model realistic wearable artifacts such as motion, EMG, EOG, electrode detachment, impedance drift, or sweat. The experiment is useful as a synthetic perturbation test, but it is not sufficient evidence for real wearable robustness.

Response

In the revised experiment, perturbations are applied to time-domain EEG samples after dataset-specific signal conditioning and segmentation but before PSE extraction, spatial mapping, and LDS smoothing; all downstream features are then recomputed. The evaluation covers Gaussian noise, low-frequency drift, and EMG-like transient bursts on SEED, DEAP, and DREAMER with matched DH-SNN and EEGNet baselines. The revised Results and Discussion describe this experiment as a controlled signal-level sensitivity test instead of real-world wearable robustness.

Locations: Fig. 3a and “Sensitivity to Controlled EEG Perturbations and Quantization”; Supplementary “Controlled EEG Perturbation Protocol”; Discussion.

### R4-23

> Robustness should be tested with realistic SNR for common EEG experiments.  
> One reference cites values Relative Noise Level (NL) ranging from 0.05 to 0.125.

Response

The revised evaluation defines the relative noise level per channel as $\mathrm{NL}=\sigma_{\mathrm{noise}}/\sigma_{\mathrm{signal}}$ and evaluates NL = 0.01, 0.03, 0.05, 0.08, 0.10, and 0.125 together with the clean condition. This includes the suggested 0.05–0.125 interval and lower levels that show the onset of degradation. Low-frequency drift and EMG-like bursts supplement the Gaussian condition, with dataset-specific sampling rates and carrier bands constrained below Nyquist.

Locations: Fig. 3a and Results; Supplementary “Controlled EEG Perturbation Protocol”.
