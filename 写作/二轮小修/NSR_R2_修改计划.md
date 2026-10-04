# NSR 第二轮小修修改计划

稿件：NSR_MS-2026-878.R1  
计划日期：2026年9月15日  
状态：修改方案，尚未实施正文、补充材料或图片修改。

## 总体判断

建议按“统一硬件指标口径 → 明确噪声实验协议 → 调整图表版式 → 全文校对 → 编写逐条回复”的顺序完成本轮小修。审稿人 1 和 4 已无进一步意见；审稿人 2 的四条意见主要要求明确现有证据的适用范围并改善呈现。本轮意见没有明确要求新增实验，因此计划以已有结果为基础。

正文和补充材料已经包含不少必要说明。修改重点是把这些信息同步到摘要、图注和结果结论中，让读者在看到指标或图表时就能理解实验条件。按照 nature-response 的逐条映射方式，下面分别记录现状、拟修改动作和验收标准，不把拟做的工作写成已完成。

## 核对依据

- [正文源码 main.tex](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex)
- [补充材料源码 supplement.tex](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/supplement.tex)
- [编辑决定与审稿意见](C:/Users/VECTOR/Desktop/NSR/写作/National_Science_Review_Decision_Bilingual.md)
- 同目录现有正文 PDF：已检查第 2、4、5、7 页，用于定位异常断段、图 2、表 1 和图 3 的版式。现有 PDF 共 11 页；它只能作为当前本地版本的页面依据，不能自动认定与审稿人看到的提交版本完全相同。

下文行号均为检查时的 TeX 源码行号，不是 PDF 行号；实际修改后需要重新生成定位信息。源码含大量 latexdiff 删除内容，以下判断以保留内容和新增内容为准。

## 修改任务总表

| 编号 | 审稿要求 | 当前情况 | 拟采取的动作 | 完成标准 |
|---|---|---|---|---|
| R2.1 | 摘要明确测量范围，统一功耗与能耗口径 | 摘要列出动态功耗 40 mW 和总能耗 2.66 μJ，但没有总功耗 148 mW，也没有测量范围 | 改写摘要末句；正文硬件结果增加范围说明；与补充材料 S9、S13 核对 | 仅看摘要即可知道是预处理张量到分类输出的加速器指标；2.66 μJ 明确对应总功耗 |
| R2.2 | 图 3a 不应暗示干净模型的零样本抗扰能力 | 补充材料明确逐条件训练与模型选择，正文和图注说明不够集中 | 图注、结果、讨论统一使用 matched-noise training and evaluation；解释 Clean 与噪声端点之间的差值 | 读者不会把曲线理解为同一固定模型在未知噪声上的测试 |
| R2.3 | 调整图 2、表 1 尺寸，统一所有正文图表字号 | 图 2、表 1 均有负位移和超宽容器；表 1 为 16 列，文字明显偏小 | 恢复正常版心；重排表 1；按最终印刷尺寸统一图 1–4、表 1–2 的字体层级 | 无越界、无挤压；同类文字字号一致且清晰可读 |
| R2.4 | 修正拼写和排版，包括第 2 页换行 | 现有 PDF 第 2 页存在句中断段，源码保留了相应空行；审稿人所指精确行号尚不能一一对应 | 修复已定位断段；核对提交版定位；清理修订标记引起的间距和排版问题 | 句子连续、词间距正常、引用和公式不越界 |
| R1.1、R4.1 | 无进一步实质修改要求 | 两位审稿人均明确满意 | 回复信分别简短致谢 | 两位审稿人均有对应回复 |

## R2.1 明确硬件指标的测量范围

### 已核实的位置与问题

- [main.tex 第 181 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:181)：摘要末句列出 18 μs、40 mW 动态功耗和 2.66 μJ 总能耗，未说明预处理张量输入边界，也没有列出 148 mW 总功耗。
- [main.tex 第 755 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:755)：Hardware Implementation 已说明输入经过 PSE 和 LDS 预处理，并列出 40/108/148 mW 动态、静态和总功耗，以及 2.66 μJ 总能耗。
- [main.tex 第 790 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:790)：Discussion 已明确 acquisition、sensor front end、communication 和 battery operation 尚未集成。
- [supplement.tex 第 811 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/supplement.tex:811)：已经列出 PL 加速器测量范围，包含片上缓冲、PL SPI、TCE、DF-TTFS、AER/CDC、存储和计算逻辑；不包含 EEG 采集、PSE、LDS、PS、DDR 和板级外设。
- [supplement.tex 第 924 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/supplement.tex:924)：已有明确公式和 Table S13，能耗计算本身一致。

### 建议修改

1. 将摘要最后一句改为两句：先交代输入与输出边界，再报告同一口径的指标，最后说明未纳入系统集成的部分。
2. 建议同时保留总功耗和动态功耗，但用括号或从句明确二者关系。摘要不必再增加动态能耗 0.72 μJ，避免数字堆积；补充材料保留完整分项。
3. Hardware Implementation 在首次报告 18 μs 的段落中补一句排除范围，并指向补充材料测量范围和 Table S13。Discussion 已有的系统局限说明保留，必要时只统一术语。
4. Supplement 中将“通信”的层级写清楚：PL 内部 SPI/AER/CDC 属于已列入的逻辑；外部传感器链路、无线传输等系统通信尚未集成。不要笼统改成所有 communication 都不计入，否则会与现有包含项冲突。
5. 保留 PSE、LDS 为独立 kernel 的说明。其测试工作量不同且独立测量，不能把 Table S9 的能耗直接与 2.66 μJ 相加，称为完整系统的单次推理能耗。

摘要建议用语，供后续实施时调整篇幅：

> On a Zynq-7020 FPGA, inference from a preprocessed EEG feature tensor to the class output takes 18 μs, with a total power of 148 mW, including 40 mW of dynamic power, and a total energy of 2.66 μJ per inference. These accelerator-level measurements exclude EEG acquisition, PSE extraction, LDS smoothing, external communication, and battery-powered system operation.

需要统一保留的数值关系：

| 指标 | 数值 | 说明 |
|---|---|---|
| 加速器推理延迟 | 18 μs | 预处理张量输入到类别输出 |
| 动态功耗 | 40 mW | 动态部分 |
| 静态功耗 | 108 mW | 静态部分 |
| 总功耗 | 148 mW | 40 + 108 |
| 动态能耗 | 0.72 μJ | 40 mW × 18 μs |
| 总能耗 | 2.66 μJ | 148 mW × 18 μs = 2.664 μJ，按现有精度报告 |

验收时检查摘要、硬件结果、讨论、结论和 Supplement 的相应表述；每次使用“total”都应明确它是该加速器测量范围内的总量。

## R2.2 明确图 3a 是匹配噪声条件下的训练与评估

### 已核实的位置与问题

- [main.tex 第 560 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:560)：图 3 图注交代了噪声添加位置、NL 定义及 ΔAcc，但没有直接写明每个噪声类型和水平都独立训练、独立选择模型。
- [main.tex 第 715 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:715)：正文已有“trained and evaluated for each noise condition”，还需明确重复的是 training 和 model selection，而不是只改变测试输入。
- [main.tex 第 769 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:769)：讨论将结果概括为受控扰动下较小的精度下降，没有在同一句中限定 matched-noise 条件。
- [main.tex 第 787 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:787)：局限性已经说明模型按每种 synthetic noise condition 分别训练，可补足“并非 clean-only 模型的零样本测试”。
- [supplement.tex 第 276 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/supplement.tex:276)：明确每种类型和 NL 都有独立训练及模型选择，轨迹仅使用一个 model seed，结果为描述性比较。

### 建议修改

1. 将结果小节标题改为 “Performance under Matched-Noise Training and Weight Quantization”，或在保留原小节标题时，将首句明确改为 matched-noise 评估。
2. 图 3 总图注标题可改为 “Matched-noise performance, weight quantization, and model complexity”。在 panel a 说明中紧接数据集和噪声类型加入下列限定。
3. 正文首次描述协议时同步写出 separately trained and selected for each corruption type and noise level。所有模型保持现有数据分割和模型选择规则，不把这些结果改称独立测试集结果。
4. Discussion 对九组 dataset–perturbation 的比较加上 “under matched-noise training and evaluation”。局限性增加 clean-only/zero-shot 的区别。
5. 明确 Clean 点和不同 NL 点可以对应各自训练、选择出的模型；ΔAcc 比较的是条件匹配结果，不能解释成同一固定模型受到扰动后的性能下降。
6. 保留现有曲线、数据和差值，不补造误差条或显著性结论。审稿意见要求澄清现有实验，未要求补充 clean-trained/frozen-model 实验。若今后仍要主张对未知噪声的零样本鲁棒性，则需单独开展支持该主张的实验。

图注建议增加的英文句子：

> For each corruption type and noise level, each model was trained and selected separately under the corresponding noise condition. The curves therefore show performance under matched-noise training and evaluation, rather than zero-shot robustness of a fixed model trained only on clean data. Endpoint differences compare condition-specific models with the clean-condition baseline.

Supplement 的最小改动：在第 276 行现有协议后增加一句与以上解释一致的实验范围说明；保留单 seed 和描述性比较的披露。

另需保留 [supplement.tex 第 353 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/supplement.tex:353) 对 checkpoint selection 的现有说明：没有单独验证集，模型选择和最终报告使用同一 held-out partition。此次文字澄清不能将其改写为 untouched independent test set。

验收标准：摘要之外，图注、Results、Discussion 和 Supplement 对“每个条件重新训练并选模型”的表述一致；全文不再由图 3a 推导未经测试的零样本抗扰能力。

## R2.3 恢复图表尺寸并统一字体

### 图 2

[main.tex 第 279 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:279)附近实际采用：

```latex
\hspace*{-2.8cm}
\begin{minipage}{\dimexpr\textwidth+2.8cm\relax}
...
\includegraphics[width=\textwidth]{figures/DA-SNN.eps}
```

这使图及图注超出正常正文版心，现有 PDF 第 4 页也可直接看到左边界不一致。

计划删除负位移和超宽 minipage，使用正常 `figure*` 双栏浮动体，宽度限制在正文 `\textwidth` 内。建议结构：

```latex
\begin{figure*}[t]
\centering
\includegraphics[width=\textwidth]{figures/DA-SNN.eps}
\caption{...}
\label{fig:DA-SNN}
\end{figure*}
```

缩回版心后，检查 `DA-SNN.eps` 中卷积参数、图例和节点说明的最终字号。如仍过小，应从图源调整排布、裁减空白和增大文字，保持连接关系与方法内容一致。

### 表 1

[main.tex 第 357 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:357)附近包含 `\hspace*{-2.8cm}`、`\begin{minipage}{1.2\textwidth}` 和 `\resizebox{\textwidth}{!}`。表格为方法列加 15 个指标列；现有 PDF 第 5 页中数字和均值±标准差很拥挤。

首选方案：保留 Table 1 的编号、全部方法、数据集和三个指标，在同一个双栏表中上下排列两个区块：

- 上半区：Method + SEED、SEED-IV、SEED-V，各含 Acc、F1、Spe，共 10 列。
- 下半区：Method + DEAP、DREAMER，各含 Acc、F1、Spe，共 7 列。

每个区块重复方法名和清晰的分组表头，字号一致，不对上下区块分别做比例缩放。删除超宽容器，先通过列宽、列间距、表头换行解决宽度。若仍拥挤，可将均值和标准差分两行显示，但二者必须都保留，精度和加粗含义也应保持。

这一方案增加表格高度，需要编译检查浮动位置。最终选择应以版心内可读性为依据，不能靠继续压缩字体满足宽度。

### 正文全部图表的同步规范

范围为图 1–4 和表 1–2；不能只处理审稿人举例的两项。

- 在最终插入尺寸下统一面板标签、坐标轴标题、刻度、图例和图内说明的各自字号。建议起点为面板标签 9–10 pt、图中文字 8–9 pt、表体 8 pt 左右；这是本次排版建议，不是期刊硬性规定。
- 同类文字字号应一致，不要求所有文字都采用同一个大小。图注沿用模板样式。
- 图 1 使用 `Overview.eps`；图 2 使用 `DA-SNN.eps`；图 3 使用 `robustness_quantization_comparison.png`；图 4 使用 `hardoverview.png`。调整 LaTeX 正文字号不会自动统一这些图片里的文字。
- 图 3a 有可用绘图脚本 `figures/figure3a_noise_robustness.py`，但正文当前引用的是合成 PNG。后续需确保重绘结果真正进入合成图，并同步检查 b、c 面板字号。
- [main.tex 第 650 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:650)的表 2 也被缩放到单栏。按最终尺寸检查它与表 1 的字号；如单栏无法容纳，则考虑改为双栏排版。
- 对图片源的编辑能力先做确认：已有绘图脚本或可编辑矢量资源优先；若只有栅格图，单纯放大不会改变图中文字相对大小，也不会恢复清晰度。

验收标准：图表及图注均在正常版心内；读者无需特别放大即可读出指标、图例和关键方法标签；表 1 的全部数值与改动前逐项一致。

## R2.4 修复断段并做针对性校对

### 已确认的问题

现有 PDF 第 2 页左栏中，`power and latency` 与 `as monitoring duration grows` 被拆成了两个段落，形成句中断段。

对应 [main.tex 第 227 行](C:/Users/VECTOR/Desktop/NSR/写作/marked_revision/main.tex:227)至第 231 行：旧稿删除内容之间残留空行，尤其第 229 行，需要结合 `\DIFdel` 和 `\DIFadd` 的包裹范围处理。恢复后的句子应连续包含：

> ... increasing power and latency as monitoring duration grows. Model compression techniques ...

现有 PDF 没有正文行号，因此尚不能确认这个问题就是审稿人所说的“第 2 页第 2–3 行”。计划修复这个已确认异常，并用实际提交给审稿人的 PDF 再对照指定位置，不在回复信中提前声称完成了精确行号核对。

### 具体处理

1. 去掉造成句中 `\par` 的空行或段落命令，核对连续文本中的必要空格。正常 TeX 源码单换行通常只是空白，不应机械删除所有换行。
2. 核对 latexdiff 边界附近的粘连词、标点前多余空格、异常缩进、引文换行及正文和公式之间的空白。
3. `pathand`、`energysavings`、`ASICimplementation` 等检索命中位于旧稿删除内容，不能直接列为当前可见正文错误。校对应以最终可见文字和 PDF 为准。
4. 检查图注大小写、缩写首次定义、`18 μs` 与 `0.018 ms` 的一致性、percentage points 与百分比变化的区别，以及图表交叉引用。
5. 当前日志含多处 Overfull 警告。对涉及图表、公式和段落的警告逐项看实际输出，重点检查第 4–5 页公式及图注边界；不把每个 Underfull 警告都视为必须改文义的问题。

## 编辑要求与提交材料计划

以下要求来自此次决定邮件：

| 编号 | 编辑要求 | 对应动作 |
|---|---|---|
| E.1 | 回复审稿意见并修订稿件 | 按 R2.1–R2.4 逐条记录变更，保留原始评论；R1.1、R4.1 分别致谢 |
| E.2 | 在稿件中标明修改 | 检查本轮修改是否清晰可辨，避免旧轮次标记使新修改难以定位 |
| E.3 | 回复应尽量具体 | 修改完成后再填写新稿的页码、行号或节名，并提供关键修改句 |
| E.4 | 上传时清理重复文件 | 本地可保留版本记录；正式上传包只纳入需要提交的文件 |
| E.5 | 尽快修回，预计 30 天内收到 | 按决定函的时限安排提交，最终以投稿系统显示的截止时间为准 |

两份输入文件已经是 latexdiff 标记稿。实施时需要先固定本次收到意见所对应的 R1 基线，再生成本轮修改标记。`NSR_Author` 目录存在另一套源文件，但在核实内容和版本前，不应默认其就是正确基线。

## 实施顺序与验收

1. 固定当前版本及图源，确认本轮修改标记的比较基线。
2. 完成 R2.1 的摘要和测量边界统一，再完成 R2.2 的图注、结果和讨论改写。
3. 完成图 2、表 1 重排，统一所有正文图表的最终字号。
4. 修复断段和排版问题，编译正文、补充材料，重新核对图表编号及引用。
5. 逐页检查最终 PDF；核对摘要数字、表 1 原始数值、图 3 曲线与数据是否保持一致。
6. 最后编写英文逐条回复，使用完成后的实际变更和定位信息。最终稿与修改标记稿都应便于核对。

计划目前可以据此实施；以下信息影响最终回复措辞或交付验证，需要在执行时核实：

- 硬件计时起点是否包含外部输入传输，以及 PL SPI 计入功耗与计入延迟的具体范围。现有文字足以界定加速器逻辑，但不能据此推断外部链路已计入。
- 审稿人看到的 PDF 与当前本地 PDF 是否同版，以准确定位 R2.4 的页码和行号。
- 图 1、2、4 是否有更上游的可编辑图源，便于统一图内字号。

以上核实事项不影响先完成摘要、匹配噪声表述及已定位排版问题的修改方案；本计划不把未核实的测量或实验细节写成事实。
