# Response Letter: Fig. 4 Dataflow and GALS Control

## R1-4. Synchronous/Asynchronous Interaction, Handshake, and Efficiency Mechanisms

**Reviewer comment:** *"The hardware section is not very easy to follow. In Fig. 4(a), the interaction between the synchronous and asynchronous parts is not clearly illustrated, and the handshake mechanism is only briefly mentioned. It is also not very clear how the claimed energy efficiency of the GALS design is achieved, for example, how it relates to event sparsity or clock gating."*

**Response:**

We thank the reviewer for identifying this presentation gap. We have revised Fig. 4(a), its legend, the Hardware Implementation section, and the Supplementary hardware-control description to make the GALS boundary explicit. The architecture contains two independent locally synchronous islands: the input/feature buffers, tensor compute engine, multi-branch fusion path, and DF-TTFS encoder belong to `clk_TCE`, whereas the lower weight memory, CU/PE arrays, spike collector, and final-layer state belong to `clk_SNN`; the downstream comparator-tree decision unit consumes the final membrane potentials. The AER block is a composite boundary containing sender-side event formation, Req/Ack clock-domain crossing, and SNN-side routing and address decoding. Because adding large clock-domain frames would obscure the already dense paths in panel (a), the two island boundaries are stated in the revised legend and text, while the figure uses five line encodings for tensor data, spike events, Req/Ack, control/status, and memory access.

We also added the complete causal sequence of the bundled-data four-phase protocol. The sender stabilizes the address/timestamp payload and asserts Req; synchronized Req enables the required SNN array; the receiver asserts Ack after the event update is complete; the sender then deasserts Req; and the receiver finally deasserts Ack, after which the payload may change. Req and Ack each use a two-stage synchronizer in the receiving clock domain, while the multi-bit payload remains stable over the full transfer rather than being synchronized bit by bit. The resulting stall behavior supplies backpressure without a dual-clock event FIFO.

Finally, the revision distinguishes three mechanisms instead of attributing efficiency to GALS alone: model-induced spike sparsity reduces the number of event transfers, weight reads, and membrane updates; event-triggered execution limits routing, memory access, and CU/PE updates to valid events; and local register clock enables reduce unnecessary dynamic switching while modules are idle. We do not claim that clock-enable control reduces static power or that total power is strictly proportional to event rate.

---

## R1-6. Tensor and Spike-Event Representations in Fig. 4

**Reviewer comment:** *"Fig. 4 does not clearly indicate whether the data is represented as tensors or spike events, which makes the processing pipeline difficult to follow."*

**Response:**

We agree and have revised Fig. 4(a) to expose the representation boundary directly. Blue solid lines denote dense/INT8 tensor data from the SPI and feature buffers through the TCE and multi-branch fusion path to DF-TTFS. DF-TTFS is the tensor-to-event conversion point. Orange solid lines then denote sparse AER spike events carrying an address and timestamp through the AER interface and CU/PE arrays. Hidden-layer events follow the CU/PE--spike-collector--AER--CU/PE recirculation path for time-multiplexed execution of subsequent layers. The final layer does not produce a spike-count or firing-rate class vector: its 32-bit membrane potentials are passed to a separate comparator-tree decision unit, which outputs the argmax class label.

The revised legend also defines purple dashed Req/Ack handshaking, green dash-dotted control/status, and black memory-access paths. These additions make the tensor, event, control, and weight-data semantics distinguishable without requiring the reader to infer them from module names.

---

## R2-5a. GALS Interface Semantics and the Boundary of the Quantitative Overhead Analysis

**Reviewer comment:** *"The Globally Asynchronous Locally Synchronous (GALS) architecture relies on a complex four-phase handshake protocol and Address-Event Representation (AER) routing to cross clock domains. The authors praise the energy reduction from sparse compute activation but completely ignore the significant dynamic power, physical area footprint, and latency overhead inherently introduced by the AER routing logic, threshold filters, and metastability-prevention synchronizers. Without a transparent, component-level breakdown of the GALS interface overhead, the isolated 40 mW dynamic power figure is incomplete and highly misleading."*

**Response:**

We agree that the GALS interface must not be presented as cost-free. In the revised main text and Supplementary Information, we explicitly identify the non-zero interface components: event-valid filtering, AER routing/broadcast and hidden-layer recirculation, address decoding, two-stage Req/Ack synchronizers, four-phase handshake state machines, and local clock-enable control. The text now states that these components consume logic and add transfer latency, and that every accepted event incurs routing and protocol work even when the event stream is sparse. We have removed the unsupported numerical MTBF statement and the claim that this overhead is negligible.

The quantitative analysis is now resolved from the top-level hierarchical synthesis. The event-valid filter, AER router, address decoder, Req/Ack synchronizers, four-phase handshake FSM, and clock-enable controller account for a gross budget of 981 LUTs and 602 FFs; their individual functional latencies are reported in the Supplementary Information and are explicitly treated as non-additive. Component-level dynamic power is not separately resolved, so we do not assign an unsupported fraction of the 40 mW top-level dynamic power to any interface block.

We also added a matched synchronous implementation of the same INT8 DA-SNN on the same Zynq-7020 device using the same input tensor and clock-enable policy. Relative to this synchronous implementation, GALS adds 172 LUTs and 139 FFs and increases latency from 16.5 to 18 microseconds, while reducing total energy from 3.35 to 2.66 microjoules per inference. The Hardware Implementation section reports the concise power/latency comparison, and the Supplementary Information provides the complete resource, timing, interface-latency, and system-inclusion tables. We therefore limit the conclusion to a net energy advantage for this matched implementation.
