# Response Letter — Revision Group 2

## Fig. 2 and the EEG-to-feature-to-tensor-to-spike data flow

### Overview of the revision

We thank the reviewers for identifying places where the end-to-end data transformation and DSGM tensor operations were insufficiently explicit. The original manuscript already presented the intended DSGM backbone, dual-gate modulation, and element-wise fusion. We have retained both the original Fig. 2 schematic and the main-text DSGM formulation. The revision instead reorganizes the explanation at two levels: the main text and expanded Fig. 2 legend now provide the reader-facing data flow and symbol definitions, whereas the Supplementary Information provides implementation-level tensor dimensions, convolution parameters, and broadcasting rules.

The revised description now distinguishes four representations: continuous EEG recordings, temporally binned PSE topographic tensors, DSGM-refined dense feature tensors, and DF-TTFS spike-time representations. It also clarifies that the input feature-channel axis contains temporally contiguous PSE maps, while EEG electrodes are embedded as locations on the two-dimensional topographic grid.

---

## Reviewer 3, Comment 4

> While the overall pipeline is described, the connection between the continuous EEG features, the encoding process, and the spiking neural network is not sufficiently detailed. Providing a clearer description of data transformations at each stage would improve the understanding of the end-to-end system.

**Response:**

We agree that the original description distributed the relevant information across the preprocessing, model, and encoding sections, which made the interfaces between these stages difficult to follow. We have therefore added a stepwise description in the subsection **“Neuromorphic framework for EEG emotion recognition.”** The revised text explains that continuous EEG is Z-score normalized and divided into non-overlapping outer windows; PSE is calculated over temporally contiguous bins; the electrode values from each bin are projected onto an electrode-topographic grid; and the resulting maps are stacked to form a dense tensor in \(\mathbb{R}^{N_f\times H\times W}\). DSGM operates on this dense representation, after which DF-TTFS maps the refined activations to a shape-matched spike-time representation for ATSNN classification.

The Supplementary Information now extends this reader-facing overview with the complete transformation chain and dataset-specific dimensions. This separates the physical EEG preprocessing steps from the model-induced tensor-to-event conversion and makes clear that DF-TTFS, rather than the raw EEG input, defines the dense-to-spike-time boundary.

**Locations revised:**

- Main text, **“Neuromorphic framework for EEG emotion recognition”**;
- Fig. 2 legend and alt text;
- Supplementary Information, **“EEG Data Preprocessing”**, under **“Composite DSGM tensor dimensions and broadcasting.”**

---

## Reviewer 4, Comment 3

> The symbol "@" in Fig. 2 is unclear. The figure repeatedly uses the symbol "@", but its meaning is not defined in the caption or main text. From context, it may refer to a tensor dimension such as C × H × W, but this should be explicitly clarified.

**Response:**

Thank you for noting this ambiguity. The at sign in Fig. 2 is not a matrix multiplication, convolution, or other arithmetic operator. It is used only as a compact shape separator: a label of the form “C at H by W” denotes \(C\) feature channels arranged on an \(H\times W\) spatial grid. We have added this definition directly to the Fig. 2 legend and clarified that the exact dataset-specific integer dimensions are provided in the Supplementary Information.

We retained the original schematic because the symbol was intended only as dimension notation; the revision resolves the ambiguity through an explicit legend rather than changing the architecture or graphical layout.

**Location revised:** Fig. 2 legend.

---

## Reviewer 4, Comment 4

> The dimensions C, H, and W should be precisely defined. The text suggests that these are the channel, height, and width dimensions of the model input, but it is not fully clear how the EEG-derived PSE feature map is mapped into this tensor. The relationship between EEG channels, PSE segments, spatial grid size, and the model input dimensions should be stated explicitly.

**Response:**

We have clarified the physical meaning of each axis in both the main text and Supplementary Information. For the first model input, \(C=N_f\) is the number of temporally contiguous PSE maps within one outer window. The EEG electrodes do not form this feature-channel axis. Instead, the PSE value associated with each electrode is placed at its montage-defined location on an \(H\times W\) topographic grid, with empty grid positions set to zero. Stacking the \(N_f\) maps yields one dense input tensor in \(\mathbb{R}^{N_f\times H\times W}\). In subsequent layers, \(C\) denotes the learned feature-channel count.

The Supplementary Information lists the exact model inputs as \(4\times8\times9\) for the SEED-family datasets, \(6\times6\times7\) for DEAP, and \(9\times4\times5\) for DREAMER, excluding the batch axis. These definitions make the relationship between the temporal PSE bins, electrode montage, and model tensor explicit.

**Locations revised:**

- Main text, first definition of the DSGM input tensor;
- Fig. 2 legend;
- Supplementary Information, **“EEG Data Preprocessing”** and the new implementation-dimension table.

---

## Reviewer 4, Comment 5

> Notation for elementwise multiplication should be unified. The main text uses the Hadamard product notation, while Fig. 2 appears to use a different machine-learning notation. The authors should adopt one notation consistently throughout the paper and figures.

**Response:**

The main text continues to use \(\odot\) consistently for the Hadamard product. Because Fig. 2 uses a circled multiplication mark as a graphical operation node, we have now defined that mark explicitly in the figure legend as the same element-wise multiplication represented by \(\odot\) in the equations. Thus, the graphical node and mathematical notation now have one unambiguous meaning without requiring a change to the schematic.

**Locations revised:** Fig. 2 legend and the explanatory sentence following the DSGM fusion equation.

---

## Reviewer 4, Comment 7

> The DSGM tensor dimensions require clarification. The channel gate is written as G_ch ∈ R^{C×1×1}, while the spatial gate is G_sp ∈ R^{1×H×W}. If the pointwise convolution changes the number of channels or the spatial size, then F_DS ⊙ G_ch ⊙ G_sp is not well-defined unless broadcasting, padding, and resizing conventions are explicitly specified.

**Response:**

We agree that the original functional formulation did not provide the implementation-level dimensions needed to verify the fusion directly. We have retained the original DSGM equations and added a dedicated tensor-dimension and broadcasting description in the Supplementary Information.

For shape bookkeeping, the aligned feature tensor is written as

\[
U\in\mathbb{R}^{B\times C_o\times H'\times W'}.
\]

The main feature path preserves this shape. The channel gate has shape

\[
G_{\mathrm{ch}}\in\mathbb{R}^{B\times C_o\times1\times1}
\]

and is broadcast over \(H'\) and \(W'\). The spatial gate has shape

\[
G_{\mathrm{sp}}\in\mathbb{R}^{B\times1\times H'\times W'}
\]

and is broadcast over the \(C_o\) feature-channel axis. Their element-wise product therefore has shape \(B\times C_o\times H'\times W'\), and the subsequent batch-normalization and ReLU operations do not alter the dimensions.

The new tensor-dimension table in the Supplementary Information also specifies the kernel, stride, padding, and groups for every stage and branch. In particular, the stride-2, \(3\times3\), padding-1 operation gives

\[
H'=\left\lfloor\frac{H+2p-k}{s}\right\rfloor+1=\left\lceil\frac{H}{2}\right\rceil,
\qquad
W'=\left\lceil\frac{W}{2}\right\rceil.
\]

This is important for the odd grid widths used by the datasets: the aligned DSGM feature dimensions are \(8\times4\times5\) for the SEED family, \(12\times3\times4\) for DEAP, and \(18\times2\times3\) for DREAMER. No additional resizing operation is used at the fusion stage.

We emphasize that this revision clarifies the existing composite DSGM implementation; it does not change the model architecture or the main-text DSGM formulation.

**Locations revised:**

- Main text, sentence following the DSGM fusion equation;
- Supplementary Information, **“Composite DSGM tensor dimensions and broadcasting”** and its implementation-dimension tables.