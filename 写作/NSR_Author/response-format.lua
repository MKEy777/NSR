local current_comment = nil

local response_openers = {
  ["R1-1"] = "We sincerely thank the reviewer for identifying this important ambiguity in the evaluation protocol. We fully agree that the reported accuracy is not interpretable without an explicit split definition.",
  ["R1-2"] = "We sincerely thank the reviewer for this constructive suggestion. We agree that the roles of the adaptive temporal window and the dual-stream gating module should be demonstrated empirically rather than supported only by theoretical discussion.",
  ["R1-3"] = "We sincerely thank the reviewer for pointing out the limited scope of the original ablation study. We fully agree that cross-dataset ablations are needed to determine whether the observed gains persist under different signal statistics and channel layouts.",
  ["R1-4"] = "We sincerely thank the reviewer for highlighting that the original hardware description did not make the dataflow or the source of the energy reduction sufficiently clear. We have therefore made the synchronous--asynchronous boundary and each efficiency mechanism explicit.",
  ["R1-5"] = "We sincerely thank the reviewer for this careful observation. We agree that inconsistent terminology and undefined metrics can obscure both the method and the evaluation, and we have corrected these issues throughout the manuscript and Supplementary Information.",
  ["R1-6"] = "We sincerely thank the reviewer for identifying this ambiguity in Fig. 4. We agree that the figure must state exactly where dense tensors end and spike events begin.",
  ["R1-7"] = "We sincerely thank the reviewer for this valuable suggestion. We agree that the manuscript should state the specific model-to-hardware gap directly, rather than leaving the motivation implicit in a general discussion of SNNs and wearable EEG.",
  ["R2-1"] = "We sincerely thank the reviewer for raising this important fairness concern. We agree that measurements from an FPGA accelerator and a Raspberry Pi cannot, by themselves, isolate the architectural benefit of the GALS clock organization.",
  ["R2-2"] = "We sincerely thank the reviewer for emphasizing subject dependence in affective EEG. We fully agree that subject-dependent and subject-independent results must be clearly separated and that wearable relevance requires an explicit cross-subject evaluation.",
  ["R2-3"] = "We sincerely thank the reviewer for identifying the missing preprocessing boundary in the original efficiency claim. We agree that accelerator-only latency must not be presented as end-to-end acquisition-to-decision latency.",
  ["R2-4"] = "We thank the reviewer for drawing attention to this important deployment limitation. We agree that continuous long-term use will ultimately require calibration or adaptation; however, the present work evaluates a fixed-parameter inference prototype rather than an online-learning system.",
  ["R2-5"] = "We sincerely thank the reviewer for requesting a transparent accounting of the GALS interface overhead. We fully agree that the routing, handshake, filtering, and synchronization logic must be included when evaluating the claimed efficiency.",
  ["R2-6"] = "We sincerely thank the reviewer for noting this presentation inconsistency. We agree that tables serving the same manuscript should use a coherent typographic language even when their information densities differ.",
  ["R3-1"] = "We sincerely thank the reviewer for this important statistical suggestion. We fully agree that point estimates alone are insufficient for evaluating the stability of results across seeds or held-out subjects.",
  ["R3-2"] = "We sincerely thank the reviewer for identifying the terminology and naming inconsistencies. We agree that each temporal scale and model component should have one unambiguous name.",
  ["R3-3"] = "We sincerely thank the reviewer for this constructive suggestion. We agree that perturbation curves are substantially more informative when the proposed model and reference baselines are evaluated under identical conditions.",
  ["R3-4"] = "We sincerely thank the reviewer for requesting a clearer end-to-end representation description. We agree that the transformations from continuous EEG to dense features and then to spike events should be explicit at every stage.",
  ["R3-5"] = "We sincerely thank the reviewer for emphasizing reproducibility. We fully agree that optimization, training, data-splitting, and hardware settings should be consolidated rather than scattered across the manuscript.",
  ["R3-6"] = "We sincerely thank the reviewer for encouraging a more realistic discussion of deployment. We agree that latency, memory, preprocessing, sensing, and subject/session shift must be considered together when assessing wearable use.",
  ["R4-1"] = "We sincerely thank the reviewer for identifying this conceptual imprecision. We fully agree that continuously sampled scalp EEG should not be described as intrinsically sparse and that the sparsity exploited by the hardware is introduced by the model's spike-time encoder.",
  ["R4-2"] = "We appreciate the reviewer's concern about specificity, scientific tone, and technical precision. We agree that these observable qualities should be improved throughout the paper, and we have revised the prose on that basis.",
  ["R4-3"] = "We sincerely thank the reviewer for identifying this undefined symbol. We agree that the at sign must be explained because it denotes a tensor-shape separator rather than an arithmetic operation.",
  ["R4-4"] = "We sincerely thank the reviewer for requesting precise tensor definitions. We agree that the relationship among EEG electrodes, PSE maps, the spatial grid, and learned feature channels must be stated explicitly.",
  ["R4-5"] = "We sincerely thank the reviewer for this notation correction. We agree that the figure and equations should use one consistent symbol for element-wise multiplication.",
  ["R4-6"] = "We sincerely thank the reviewer for this careful typesetting observation. We agree that displayed equations should be integrated grammatically into their surrounding sentences.",
  ["R4-7"] = "We sincerely thank the reviewer for identifying this dimensional ambiguity. We agree that the fusion equation is only well defined when the aligned tensor shape, broadcasting axes, padding, and absence of resizing are explicitly specified.",
  ["R4-8"] = "We sincerely thank the reviewer for this terminology suggestion. We agree that using the original authors' term, B1 model, makes the relationship to the reference framework clearer.",
  ["R4-9"] = "We sincerely thank the reviewer for identifying the missing definition. We agree that the threshold must be defined before it appears in the B1 dynamics.",
  ["R4-10"] = "We sincerely thank the reviewer for this important request. We agree that the manuscript should distinguish which B1 properties are inherited, why that substrate was selected, and which parts are specific to ATSNN.",
  ["R4-11"] = "We sincerely thank the reviewer for specifying the missing B1 assumptions. We agree that the Supplementary Information should be self-contained with respect to the identity mapping, mask, threshold crossing, and latency--ReLU correspondence.",
  ["R4-12"] = "We sincerely thank the reviewer for this technically precise correction. We fully agree that clipping at the upper temporal boundary is a censoring rule, not a consequence of integrating the neuron dynamics.",
  ["R4-13"] = "We sincerely thank the reviewer for identifying this numerical edge case and for suggesting a concrete safeguard. We agree and have adopted the safeguarded scale.",
  ["R4-14"] = "We sincerely thank the reviewer for highlighting this boundary ambiguity. We agree that a stored boundary time cannot, by itself, distinguish a valid late spike from a censored neuron.",
  ["R4-15"] = "We sincerely thank the reviewer for this rigorous distinction between a local derivative and a network-level Jacobian claim. We fully agree that the former does not establish bounded gradients through a multilayer TTFS network.",
  ["R4-16"] = "We sincerely thank the reviewer for proposing a rigorous experiment that would be necessary to support a network-level gradient-stability claim. We agree with the scientific standard underlying the request, while taking a more conservative revision path for the present manuscript.",
  ["R4-17"] = "We sincerely thank the reviewer for identifying this undefined-variable case and for suggesting an appropriate fallback. We agree that the all-censored case must be explicitly defined.",
  ["R4-18"] = "We sincerely thank the reviewer for raising this important readout-semantics issue. We agree that inactive hidden neurons must be excluded either by an explicit mask or by a demonstrably equivalent zero-contribution representation.",
  ["R4-19"] = "We sincerely thank the reviewer for catching this quantization error. We agree that symmetric signed INT8 weights should use the range from -127 to 127 unless the asymmetric use of -128 is explicitly intended.",
  ["R4-20"] = "We sincerely thank the reviewer for identifying this major evaluation concern. We agree that the original description was under-specified and that random window-level splitting can overstate generalization when windows from the same trial occur in both partitions.",
  ["R4-21"] = "We sincerely thank the reviewer for this accurate interpretation of the ablation result. We fully agree that DF-TTFS should be justified by hardware-oriented division removal and competitive accuracy, not by an unsupported claim of superior accuracy.",
  ["R4-22"] = "We sincerely thank the reviewer for distinguishing controlled perturbation sensitivity from real wearable robustness. We agree that synthetic noise tests cannot establish robustness to the full range of motion, physiological, electrode, and environmental artifacts encountered in deployment.",
  ["R4-23"] = "We sincerely thank the reviewer for recommending a concrete and interpretable range of relative noise levels. We agree that the experiment should include the suggested interval and define the noise level mathematically.",
}

local function display_comment_id(id)
  return id:gsub("^R", ""):gsub("-", ".")
end

function Header(el)
  if el.level == 1 then
    return {}
  end

  if el.level == 2 then
    local reviewer = pandoc.utils.stringify(el.content):gsub("Response to ", "")
    current_comment = nil
    local page_break = reviewer == "Reviewer 1" and "" or "\\newpage\n\\clearpage\n"
    return pandoc.RawBlock("latex", page_break .. "\\begin{center}\n\\underline{Responses to Comments of " .. reviewer .. "}\n\\end{center}\n\\vspace{3mm}")
  end

  if el.level == 3 then
    current_comment = pandoc.utils.stringify(el.content)
    local display_id = display_comment_id(current_comment)
    return pandoc.RawBlock("latex", "\\vspace{4mm}\n\\noindent {\\bf Comment " .. display_id .. ":}")
  end
end

function BlockQuote(el)
  local quote = pandoc.write(pandoc.Pandoc(el.content), "latex")
  quote = quote:gsub("\\n$", "")
  return pandoc.RawBlock("latex", "``{\\it " .. quote .. "}''\n\\vspace{1mm}")
end

function Para(el)
  local text = pandoc.utils.stringify(el)
  if text == "Response" then
    local display_id = display_comment_id(current_comment)
    local opener = response_openers[current_comment] or "We sincerely thank the reviewer for this constructive comment."
    return {
      pandoc.RawBlock("latex", "\\noindent {\\bf Response to Comment " .. display_id .. ":}"),
      pandoc.Para({pandoc.Str(opener)})
    }
  end
  if text:match("^We have revised the manuscript in response") then
    return pandoc.RawBlock("latex", "We sincerely thank the Editor and all reviewers for their careful evaluation and constructive comments. Their suggestions helped us improve the methodological transparency, empirical support, reproducibility, hardware accounting, and presentation of the manuscript.\\par\\medskip\n\nWe have addressed every comment point by point and incorporated the corresponding revisions into the main manuscript and Supplementary Information. To make this response self-contained, each answer below states the evaluation setting, principal evidence, limitation, or exact revision needed to understand our response without repeatedly consulting the manuscript.")
  end
  if text:match("^We thank Reviewer %d") then
    local reviewer_number = text:match("Reviewer (%d)")
    return pandoc.RawBlock("latex", "We sincerely thank Reviewer " .. reviewer_number .. " for the careful and constructive comments. We have addressed each point below and revised the manuscript and Supplementary Information accordingly.")
  end
  if text:match("^Locations?:") then
    local content = pandoc.write(pandoc.Pandoc({el}), "latex")
    content = content:gsub("^Locations?:", "\\textbf{Locations:}")
    content = content:gsub("\\n$", "")
    return pandoc.RawBlock("latex", "\\smallskip\\noindent " .. content .. "\\par")
  end
end

function HorizontalRule()
  return {}
end
