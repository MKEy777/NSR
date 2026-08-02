# Response Letter — Group 3: B1-model, Censored TTFS, Active Mask, and Output Readout

## Revision status

The manuscript changes for Reviewer 4, Comments 8–14, 17, and 18 have been implemented in the main text and Supplementary Information. The responses below are ready for integration into the full response letter. Reviewer 4, Comments 15 and 16 are addressed in the completed Group 4 response.

## Overview of the revision

We thank the reviewer for prompting a clearer separation between the established B1 framework and the contributions of DA-SNN. The revised manuscript now identifies the B1-model as the inherited neuron-level substrate, states its minimum assumptions and forward semantics, and avoids presenting either the B1-model or the general idea of adaptive temporal windows as our invention. We clarify that DA-SNN inherits the B1 piecewise-linear, constant-slope, single-spike, cascaded-window formulation, whereas the present method uses a midpoint-referenced bidirectional window-update rule and integrates it with EEG-specific DSGM processing, power-of-two DF-TTFS encoding, and a GALS accelerator.

We also reformulated the spike-time equation as a theoretical threshold-crossing time followed by an explicit censoring rule, introduced an active-spike mask, fixed the upper-boundary convention, safeguarded DF-TTFS against a zero dynamic range, defined the empty-valid-set fallback in Algorithm 1, and made the output readout's inactive-neuron semantics explicit.

---

## Reviewer 4, Comment 8

> The terminology “B1 spiking neuron model” should be aligned with the original paper. The original authors refer to the model as the “B1-model.”

**Response:**

We agree and have standardized the terminology to **B1-model** throughout the revised main text and Supplementary Information. The first mention now attributes the model directly to Stanojevic et al. and describes it as the neuron-level spike-time substrate adopted by ATSNN.

**Locations revised:** Main text, first B1-model paragraph; Supplementary Information, “B1-model Definition and Forward Semantics.”

---

## Reviewer 4, Comment 9

> The threshold \(\vartheta\) should be defined before first use, including its meaning, units, and role in the B1/ATSNN dynamics.

**Response:**

We have defined \(\vartheta_i^{(n)}\) at its first occurrence as the firing threshold of neuron \(i\) in layer \(n\), expressed in normalized membrane-potential units. We also clarify that \(\epsilon>0\) maps the threshold term \(\epsilon\vartheta_i^{(n)}\) to a temporal offset in the theoretical threshold-crossing equation. The accompanying notation now defines the presynaptic index, synaptic weight, presynaptic spike time, membrane potential, and layer-window boundaries.

**Locations revised:** Main text, paragraph following the B1 dynamics equation; Supplementary Information, “B1-model Definition and Forward Semantics.”

---

## Reviewer 4, Comment 10

> The B1 reference model should be discussed more substantially. The manuscript should explain why B1 was selected and clarify whether the proposed model relies on the B1 properties or only uses B1 as an inspiration.

**Response:**

We agree that the previous attribution and contribution boundary were too compressed. The revision now states explicitly that ATSNN **adopts rather than introduces** the B1-model. From the original framework, we inherit the piecewise-linear dynamics, the \(A_i^{(n)}=0\), \(B_i^{(n)}=1\) constant-slope parameterization, the single-spike TTFS representation, the cascaded layer windows, and the identity-mapping rationale under the assumptions of the original B1 analysis.

We have also clarified the boundary of the present contribution. Stanojevic et al. already adapt the upper temporal boundary during training; therefore, we do not claim the general concept of an adaptive temporal window as new. The ATSNN rule used here is different in form: it is a signed, midpoint-referenced update based on the earliest valid spike and can contract or expand the window. The broader innovation of DA-SNN lies in integrating this temporal regulation with the EEG-specific DSGM, power-of-two DF-TTFS encoding, and the GALS accelerator. This framing acknowledges the theoretical foundation without allowing the inherited neuron model to obscure the algorithm–hardware co-design contribution.

We use the original B1 identity mapping as a rationale for selecting a tractable spike-time substrate. We do not treat that neuron-level correspondence alone as a proof of the complete DA-SNN's network-level gradient behaviour; the latter issue is addressed separately in our response to Comments 15 and 16.

**Locations revised:** Main text, B1-model introduction and adaptive-window paragraph; Supplementary Information, “B1-model Definition and Forward Semantics.”

---

## Reviewer 4, Comment 11

> Basic B1 definitions and assumptions should be added to the supplement, including the identity mapping, active/inactive mask, threshold-crossing slope, and relation between spike time and ReLU activation.

**Response:**

We have replaced the previous extended and partly inaccurate historical description with a compact definition-focused subsection. It now specifies: (i) the B1 identity parameterization \(A_i^{(n)}=0\) and \(B_i^{(n)}=1\); (ii) the half-open single-spike window \([T_{\min}^{(n)},T_{\max}^{(n)})\); (iii) the cascade condition \(T_{\min}^{(n)}=T_{\max}^{(n-1)}\); (iv) the threshold and scaling terms; (v) the theoretical threshold-crossing time; (vi) the active/inactive mask and strict boundary convention; (vii) the unit threshold-crossing slope; and (viii) the latency–ReLU correspondence under the parameter and mapping assumptions of the original B1 work.

To keep the Supplementary Information proportionate to the present paper, we provide the definitions needed to interpret and reproduce our forward computation and direct readers to the original paper for the complete B1 theory. We also state explicitly that the ReLU correspondence is a model-selection rationale rather than an automatic network-level guarantee for DA-SNN.

**Location revised:** Supplementary Information, “B1-model Definition and Forward Semantics.”

---

## Reviewer 4, Comment 12

> Eq. (6) is not entirely the closed-form integral of Eq. (5). The upper-bound clipping is an additional censoring or timeout rule, and an explicit active-spike mask should be introduced.

**Response:**

We agree and have reformulated the equation into three distinct quantities. First, \(\tilde{T}_i^{(n)}\) is the theoretical threshold-crossing time obtained from the constant-slope dynamics. Second,

\[
M_i^{(n)}=\mathbf{1}[\tilde{T}_i^{(n)}<T_{\max}^{(n)}]
\]

identifies whether that crossing is an active spike. Third, the observed time is

\[
T_i^{(n)}=M_i^{(n)}\tilde{T}_i^{(n)}+(1-M_i^{(n)})T_{\max}^{(n)}.
\]

The revised text now describes the latter two expressions as an explicit censoring/timeout rule, rather than as part of the direct ODE integration. Algorithm 1 likewise computes and returns both \(T^{(n)}\) and \(M^{(n)}\).

**Locations revised:** Main text, censored B1 forward equation; Supplementary Information, “B1-model Definition and Forward Semantics” and Algorithm 1.

---

## Reviewer 4, Comment 13

> Eq. (8) needs a numerical safeguard when \(V_{\max}=V_{\min}\).

**Response:**

We have added the safeguarded power-of-two scale

\[
S_p=2^{\lceil\log_2(\max(V_{\max}-V_{\min},\delta))\rceil},\qquad \delta>0.
\]

The Supplementary Information specifies \(\delta=10^{-5}\) for the float32 training implementation and explains that the exponent is retained as an integer shift count for fixed-point inference. When \(V_{\max}=V_{\min}\), the scale remains positive, the normalized activations are zero, and the encoder returns the boundary code \(T_{\mathrm{spike}}=T_{\max}\) instead of encountering division by zero.

**Locations revised:** Main text, DF-TTFS equation; Supplementary Information, “Division-Free TTFS Encoding Derivation.”

---

## Reviewer 4, Comment 14

> The behaviour at \(T=T_{\max}\) is ambiguous because a boundary spike and a silent neuron clipped to \(T_{\max}\) share the same scalar value.

**Response:**

We have adopted a single half-open-window convention. A spike is active only if \(\tilde{T}_i^{(n)}<T_{\max}^{(n)}\); equality is assigned to the inactive/censored case. The stored value \(T_i^{(n)}=T_{\max}^{(n)}\) is therefore a numerical placeholder, and event validity is determined by \(M_i^{(n)}\), not by the scalar time alone.

We additionally explain why the placeholder does not create a false forward contribution: the cascade condition makes \(T_{\max}^{(n)}=T_{\min}^{(n+1)}\), so an inactive neuron produces a zero temporal offset in the next layer. The mask remains explicit for valid-event selection, temporal-window updates, output-readout equivalence, and subsequent analysis.

**Locations revised:** Main text, censored B1 forward equation and output readout; Supplementary Information, “B1-model Definition and Forward Semantics,” Algorithm 1, and “Continuous output readout and inactive-neuron semantics.”

---

## Reviewer 4, Comment 17

> Algorithm 1 has an undefined-variable issue when the valid-spike set is empty. A fallback rule should be defined.

**Response:**

We agree and have revised Algorithm 1 so that \(T_{\max}^{(n)\prime}\) is initialized to the current boundary before the valid-spike test. The valid set is now defined directly by the mask,

\[
\mathcal{V}^{(n)}=\{T_i^{(n)}\mid M_i^{(n)}=1\}.
\]

The earliest-spike variable \(T_e^{(n)}\) is formed only when \(\mathcal{V}^{(n)}\neq\emptyset\). If no valid spike is present, the initialized value is retained, giving the explicit fallback \(T_{\max}^{(n)\prime}=T_{\max}^{(n)}\). We also state the minimum-width safeguard \(\delta_T=10^{-4}\) used after an update to preserve a non-degenerate temporal interval.

**Location revised:** Supplementary Information, adaptive-window definition and Algorithm 1.

---

## Reviewer 4, Comment 18

> Eq. (11) should include an active-spike mask so that silent neurons represented by \(T_{\max}\) are not treated as valid late spikes.

**Response:**

We have made the output semantics explicit. The output layer is a continuous, nonspiking readout, and its reference time satisfies \(T_{\min}^{(L)}=T_{\max}^{(L-1)}\). Consequently, an inactive hidden neuron has \(T_j^{(L-1)}=T_{\min}^{(L)}\) and contributes zero to the implemented observed-time readout. The revised equation displays the algebraic equivalence

\[
\sum_j W_{ij}^{(L)}\bigl(T_{\min}^{(L)}-T_j^{(L-1)}\bigr)
=
\sum_j W_{ij}^{(L)}M_j^{(L-1)}\bigl(T_{\min}^{(L)}-\tilde{T}_j^{(L-1)}\bigr).
\]

Thus, the existing continuous readout is explicitly mask-equivalent, and a censored boundary placeholder cannot be interpreted as a valid late spike.

**Locations revised:** Main text, output-logit equation; Supplementary Information, “Continuous output readout and inactive-neuron semantics.”

---

## Author-side integration note

This response segment should be merged with the completed Group 4 response for Reviewer 4, Comments 15 and 16.
