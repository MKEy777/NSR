# National Science Review Decision Letter

## 国家科学评论稿件决定函

本文件收录稿件 NSR_MS-2026-878.R1 的英文决定邮件及对应中文译文，便于核对编辑决定、修回要求和审稿意见。

| 项目 | 内容 |
|---|---|
| 发件人 From | zhaoweijie@scichina.com |
| 收件人 To | bh@bit.edu.cn |
| 抄送 CC | 无 None |
| 主题 Subject | National Science Review - Decision on Manuscript ID NSR_MS-2026-878.R1 |

## 中文译文

**日期：2026年9月9日**

胡博士：

您提交至《National Science Review》的稿件 NSR_MS-2026-878.R1，题为《面向可穿戴 EEG 情绪识别的异步类脑架构》，现已完成审阅。本函末尾附有审稿人的意见。

审稿人建议发表，但同时建议您对稿件进行一些小幅修改。因此，现邀请您回复审稿人的意见并修改稿件。

如需修改稿件，请登录 <https://mc.manuscriptcentral.com/nsr_ms>，进入 Author Centre。您将在“Manuscripts with Decisions”栏目下看到稿件标题。请在“Actions”下点击“Create a Revision”。您的稿件编号后面已添加修回标识。

您也可以点击下方链接开始修回流程；如果您已经开始修回，也可以通过该链接继续操作。使用下方链接时，无需登录 ScholarOne Manuscripts。

**请注意：这是一个两步流程。点击链接后，您将被引导至网页进行确认。**

修回链接：<https://mc.manuscriptcentral.com/nsr_ms?URL_MASK=620999692825489c89e349f0e815b151>

您无法直接在最初提交的稿件版本上进行修改。请使用文字处理软件修改稿件，并将文件保存到您的计算机中。同时，请在文档中标出修改之处：可以使用 MS Word 的修订模式，也可以使用粗体或彩色文字。

修回稿准备完成后，您可以通过 Author Centre 上传并提交。

提交修回稿时，系统会提供用于回复审稿人意见的文本框。您可以在其中记录对原稿所做的修改。为加快修回稿的处理，请尽可能具体地说明您的回复。

**重要提示：**上传修回稿时，您仍可使用原始文件。完成提交前，请删除所有多余文件。

由于我们希望加快发表投至《National Science Review》的稿件，您的修回稿应尽快上传。我们预计在 30 天内收到您的修回稿。

再次感谢您向《National Science Review》投稿，期待收到您的修回稿。

此致

敬礼！

赵伟杰博士  
执行编辑  
zhaoweijie@scichina.com

谨代表：

郭雷博士  
副主编，《National Science Review》  
lguo@iss.ac.cn

## 审稿人意见

### 审稿人 1

**对作者的意见**

我的疑虑已经得到充分解决。

### 审稿人 4

**对作者的意见**

我对所有回复完全满意。祝贺各位作者。

### 审稿人 2

**对作者的意见**

本文提出了一种面向可穿戴 EEG 情绪识别的异步类脑架构。其主要组成部分包括深度可分离门控模块（DSGM）、无除法的首次脉冲时间编码（DF-TTFS）、自适应时序脉冲神经网络（ATSNN），以及全局异步、局部同步（GALS）FPGA 加速器。该框架将经过 PSE、空间映射和 LDS 平滑处理的 EEG 特征转换为稀疏脉冲事件，然后利用事件驱动的计算和数据传输来降低硬件推理成本。该方法在五个公开 EEG 情绪数据集上进行了评估，并在 Zynq-7020 FPGA 上完成了实现。总体而言，作者已经充分回应了此前的审稿意见。

修订稿对输入构建和评估方案进行了更清晰的说明，并补充了被试独立结果、跨数据集消融实验、量化实验以及合成噪声测试。在同一 FPGA 上对相同 INT8 模型进行同步实现尤其有帮助，因为这比先前的跨平台比较更直接地评估了 GALS 组织方式。新增的 PSE 和 LDS 测量结果也有助于界定文中所报告硬件结果的适用范围。

**小修意见：**

1. 摘要中对硬件测量边界的说明仍不够清晰。文中报告的 18 μs 延迟、40 mW 动态功耗和 2.66 μJ 能耗，仅涵盖从预处理输入张量开始的加速器推理过程，不包括 EEG 采集、PSE、LDS、通信和电池运行。此外，2.66 μJ 是根据 148 mW 的总功耗计算得到的，而摘要只报告了 40 mW 的动态功耗。因此，这些数值并不是在同一测量口径下呈现的。
2. 图 3a 展示的是匹配噪声训练条件下的性能，而不是固定模型对未见过的扰动的鲁棒性，因为针对每一种扰动类型和噪声水平都重新进行了训练和模型选择。图注及相关讨论应明确说明这一点，不应暗示该模型仅在干净数据上训练，却具备零样本鲁棒性。
3. 图 2 和表 1 相对于页面以及正文中的其他图表，尺寸似乎不协调。应调整其尺寸，使版式更加一致。还应统一正文所有图表的字号，包括面板标签、坐标轴标签、图例和表注。
4. 应修改一些拼写和格式错误。例如，第 2 页第 2 至第 3 行不应出现换行。

## English Original

**09-Sep-2026**

Dear Dr. Hu,

Manuscript ID NSR_MS-2026-878.R1 entitled "An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition" which you submitted to the National Science Review, has been reviewed. The comments of the reviewer(s) are included at the bottom of this letter.

The reviewer(s) have recommended publication, but also suggested some minor revisions to your manuscript. Therefore, I invite you to respond to the reviewer(s)' comments and revise your manuscript.

To revise your manuscript, log into <https://mc.manuscriptcentral.com/nsr_ms> and enter your Author Centre, where you will find your manuscript title listed under "Manuscripts with Decisions." Under "Actions," click on "Create a Revision." Your manuscript number has been appended to denote a revision.

You may also click the below link to start the revision process (or continue the process if you have already started your revision) for your manuscript. If you use the below link you will not be required to login to ScholarOne Manuscripts.

*** PLEASE NOTE: This is a two-step process. After clicking on the link, you will be directed to a webpage to confirm. ***

<https://mc.manuscriptcentral.com/nsr_ms?URL_MASK=620999692825489c89e349f0e815b151>

You will be unable to make your revisions on the originally submitted version of the manuscript. Instead, revise your manuscript using a word processing program and save it on your computer. Please also highlight the changes to your manuscript within the document by using the track changes mode in MS Word or by using bold or colored text.

Once the revised manuscript is prepared, you can upload it and submit it through your Author Centre.

When submitting your revised manuscript, you will be able to respond to the comments made by the reviewer(s) in the space provided. You can use this space to document any changes you make to the original manuscript. In order to expedite the processing of the revised manuscript, please be as specific as possible in your response to the reviewer(s).

**IMPORTANT:** Your original files are available to you when you upload your revised manuscript. Please delete any redundant files before completing the submission.

Because we are trying to facilitate timely publication of manuscripts submitted to the National Science Review, your revised manuscript should be uploaded as soon as possible. We expect to receive your revision within 30 days.

Once again, thank you for submitting your manuscript to the National Science Review and I look forward to receiving your revision.

Sincerely,

Dr. Weijie Zhao  
Managing Editor  
zhaoweijie@scichina.com

On behalf of:

Dr. Lei Guo  
Associate Editor, National Science Review  
lguo@iss.ac.cn

## Reviewer Comments to Author

### Reviewer 1

**Comments to the Author**

My concerns have been well resolved.

### Reviewer 4

**Comments to the Author**

I am completely satisfied with all the responses. Congratulations to the authors.

### Reviewer 2

**Comments to the Author**

This manuscript presents an asynchronous neuromorphic architecture for wearable EEG emotion recognition. Its main components include a depthwise separable gating module (DSGM), division-free time-to-first-spike encoding (DF-TTFS), an adaptive temporal spiking neural network (ATSNN), and a globally asynchronous, locally synchronous (GALS) FPGA accelerator. The framework converts EEG features processed through PSE, spatial mapping, and LDS smoothing into sparse spike events, and then uses event-driven computation and data transfer to reduce hardware inference costs. The method is evaluated on five public EEG emotion datasets and implemented on a Zynq-7020 FPGA. Overall, the authors have responded adequately to the previous review comments.

The revised manuscript now describes the input construction and evaluation protocols more clearly, and they have added subject-independent results, cross-dataset ablations, quantization experiments, and synthetic-noise tests. The synchronous implementation of the same INT8 model on the same FPGA is particularly useful, as it provides a more direct assessment of the GALS organization than the earlier cross-platform comparison. The additional PSE and LDS measurements also help define the scope of the reported hardware results.

**Minor Comments:**

1. The Abstract still leaves the hardware measurement boundary somewhat unclear. The reported latency of 18 μs, dynamic power of 40 mW, and energy of 2.66 μJ cover only accelerator inference from a preprocessed input tensor. EEG acquisition, PSE, LDS, communication, and battery operation are not included. Moreover, the 2.66 μJ value is calculated from the total power of 148 mW, whereas the Abstract reports only the dynamic power of 40 mW. These figures are therefore not presented on the same basis.
2. Fig. 3a shows performance under matched-noise training rather than the robustness of a fixed model to unseen corruption, because training and model selection were repeated for each corruption type and noise level. The caption and related discussion should make this distinction explicit and should not imply zero-shot robustness of a model trained only on clean data.
3. Fig. 2 and Table 1 appear out of scale relative to the page and to the other figures and tables in the main text. Their dimensions should be adjusted for a more consistent layout. Font sizes should also be standardized across all main-text figures and tables, including panel labels, axis labels, legends, and table notes.
4. Some typos and formatting errors should be revised. For instance, in lines 2- 3 of page 2, there should be no line break.
