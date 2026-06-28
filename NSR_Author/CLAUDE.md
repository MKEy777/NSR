# NSR_Author — 论文手稿大纲

> **论文标题**: "An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition"
> **正文**: `main.tex` (~41KB, 431 行)
> **补充材料**: `supplement.tex` (~32KB, 632 行)
> **参考文献**: `nsr_sample.bib`

---

## 项目结构

```
NSR_Author/
├── CLAUDE.md              # 本文件 — 正文/补充材料大纲速查
├── main.tex               # 论文正文（nsr 文档类）
├── supplement.tex          # 补充材料（article 文档类）
├── nsr_sample.bib          # 参考文献库
├── Overview.eps            # Fig.1 系统总览图
├── DA-SNN.eps              # Fig.2 模型框架图
├── robustness_quantization_comparison.eps  # Fig.3 鲁棒性/量化/模型对比
├── hardoverview.eps        # Fig.4 硬件架构图
├── timingdiagram.eps       # Fig.S1 握手时序图
└── BNRELUHSigmoid.eps      # Fig.S2 BN+Hard-Sigmoid 硬件实现
```

---

## 正文 `main.tex` 大纲

### 前置元数据 (行 1–69)
| 内容 | 行号 |
|------|------|
| `\documentclass{nsr}` + 导言区 | 1–36 |
| 期刊卷号/DOI/日期占位 | 37–43 |
| 标题、作者 (9人)、单位 (4个) | 47–63 |
| 通讯作者/共同一作脚注 | 65–69 |

### Abstract + Keywords (行 71–86)
| 项目 | 行号 | 说明 |
|------|------|------|
| `\abstract` | 76–78 | 问题→方法→结果 (96.98% Acc, 40mW, 2.66μJ) |
| `\keywords` | 82–83 | affective EEG, asynchronous neuromorphic, SNN, GALS, wearable |

### Section 1: INTRODUCTION (行 89–111)
| 主题 | 行号 |
|------|------|
| 情感与BCI背景、EEG事件驱动稀疏性 | 90 |
| 可穿戴EEG硬件进展（传感器/电极/AFE） | 92 |
| CNN/LSTM/GCN 方法的局限性（同步/密集计算） | 94–97 |
| 模型压缩的不足 | 98 |
| SNN 的事件驱动优势与现有工作的硬件瓶颈 | 108 |
| 本文提出的联合优化异步神经形态架构（DA-SNN + GALS加速器） | 110 |

> **Fig.1** (`Overview.eps`, 行 99–107): 系统总览图 — EEG→DSGM→DF-TTFS→ATSNN→GALS加速器

### Section 2: RESULTS (行 126–403)

#### 2.1 Neuromorphic framework (行 130–275)
| 主题 | 行号 |
|------|------|
| 系统三层框架概述 (DSGM → TTFS → ATSNN) | 132–133 |
| DSGM: 深度可分离卷积 + 通道门 + 空间门 | 134–165 |
| B1 脉冲神经元模型（分段线性动力学） | 218–237 |
| DF-TTFS 除法无关编码器 | 239–255 |
| ATSNN 自适应时间窗更新机制 | 257–267 |
| 输出层积分器 | 269–274 |

> **Fig.2** (`DA-SNN.eps`, 行 113–124): DA-SNN 模型框架图

#### 2.2 Emotion Recognition Performance (行 277–285)
| 主题 | 行号 |
|------|------|
| 五数据集结果总结 | 279–285 |

> **Table 1** (行 167–216): 15模型 × 5数据集 对比表 (Acc/F1/Spe)

#### 2.3 Robustness (行 377–381)
| 主题 | 行号 |
|------|------|
| 高斯噪声鲁棒性 (SD 0.001→0.05) | 379 |
| 权重量化敏感性 (FP32→INT4) | 381 |

> **Fig.3** (`robustness_quantization_comparison.eps`, 行 287–298): 噪声+量化+模型效率三合一图

#### 2.4 Computational Efficiency (行 383–387)
| 主题 | 行号 |
|------|------|
| 参数量、FLOPs、内存、功耗分析 | 385–387 |

> **Table 2** (行 300–363): 效率对比表 (12模型, FP32 + INT8)

#### 2.5 Hardware Implementation (行 391–403)
| 主题 | 行号 |
|------|------|
| INT8量化 + 异步事件驱动架构 | 393 |
| 流式+事件混合流水线 | 395–396 |
| 硬件优化: TCE可重构、多bank缓冲、融合数据路径 | 397–398 |
| DF-TTFS 移位器编码硬件 | 399 |
| 内存中心化SNN阵列 (16×4 PE) | 401 |
| FPGA 实现结果 (Zynq-7020, 100MHz) | 403 |

> **Fig.4** (`hardoverview.eps`, 行 366–375): 硬件架构总览 (a)系统级 (b)行缓冲 (c)DF-TTFS编码器 (d)PE微架构

### Section 3: DISCUSSION (行 406–413)
| 主题 | 行号 |
|------|------|
| 跨层协同设计是核心优势 | 407–408 |
| DSGM/DF-TTFS/ATSNN 各组件互补作用 | 409 |
| 稀疏性在算法层和硬件层的双重收益 | 411 |
| 局限性: 公开数据集/FPGA原型 → 实际部署差距 | 413 |

### Section 4: CONCLUSION (行 415–418)
- 端到端神经形态协同设计总结
- 关键数字: 12.50KB 存储, 13.68KB 内存, 261.21μJ (Pi5), 0.018ms/2.66μJ (FPGA)

### 尾部 (行 420–431)
| 内容 | 行号 |
|------|------|
| METHODS (指向补充材料) | 421 |
| DATA AND CODE AVAILABILITY | 424 |
| FUNDING | 427 |
| 参考文献 | 430 |

---

## 补充材料 `supplement.tex` 大纲

### 前置 (行 1–84)
- `\documentclass[12pt]{article}`, A4, 1in margins
- 图/表/公式编号前缀 `S` (行 17–19)
- 标题页 + 作者 + 单位 (行 21–78)
- `\tableofcontents` (行 82)

---

### Supplementary Methods (行 87–136)

#### S1.1 Dataset Description (行 89–96)
| 数据集 | 被试 | 通道 | 标签数 | 说明 |
|--------|------|------|--------|------|
| SEED | 15×3session | 62 | 3 | positive/neutral/negative |
| SEED-IV | 15×3session | 62 | 4 | happy/sad/fear/neutral |
| SEED-V | 20×3session | 62 | 5 | +disgust |
| DEAP | 32 | 32 (512→128Hz) | 4 | valence×arousal (1-9→二值化) |
| DREAMER | 23 | 14 (128Hz) | 4 | valence×arousal (1-5→二值化) |

#### S1.2 EEG Preprocessing (行 97–125)
- Z-score → 窗口分割 → PSE提取 → 空间映射 → LDS平滑
- **Table S1** (行 98–118): 各数据集预处理参数 (H×W, Nf, window/sliding duration)

#### S1.3 Implementation Details (行 127–135)
- 服务器: Xeon 8255C + RTX 2080 Ti, Ubuntu 22.04, PyTorch 2.3.0
- 训练: AdamW, lr=1e-4, batch=8, max 200 epochs, early stopping
- 推理部署: Raspberry Pi 5 (ARM Cortex-A76) + Zynq-7020 FPGA

---

### Supplementary Notes (行 137–498)

#### S2.1 B1 Neuron Model 详解 (行 139–146)
- vs. Hodgkin-Huxley / LIF: 去除指数衰减和乘法
- 级联时间窗 + 分段线性 + 闭式解

#### S2.2 DF-TTFS 推导 (行 147–169)
- 标准TTFS: 浮点除法归一化
- DF-TTFS: 幂次缩放 $S_p = 2^{\lceil \log_2(V_{\max}-V_{\min}) \rceil}$
- 硬件: 桶形移位器 + 阈值过滤 → AER 包

#### S2.3 ATSNN 梯度稳定性分析 (行 171–410)
| 内容 | 行号 |
|------|------|
| Definition 1: 理论放电时间 | 173–184 |
| Definition 2: 突触前时间偏移 $\Delta T_{ij}^{(n)}$ | 228–232 |
| Proposition 1: 权重梯度 | 195–226 |
| Proposition 2: 时间偏移界 $[-W_t^{(n-1)}, 0]$ | 248–280 |
| Proposition 3: 梯度界 | 282–298 |
| 自适应窗口调节 (负反馈回路) | 302–324 |

> **Algorithm S1** (行 326–410): 前向传播 + 自适应时间窗更新伪代码

#### S2.4 Quantization Strategy (行 413–437)
- INT8 对称量化: 权重 $Q_s$ (有符号) + 激活 $Q_u$ (无符号)
- QAT 训练 + BN折叠

#### S2.5 Handshake Protocol (行 439–453)
- 四相异步握手: Req→Ack→Req↓→Ack↓
- 背压机制 + FIFO溢出防护

> **Fig. S1** (`timingdiagram.eps`, 行 444–449): 握手时序图

#### S2.6 Hierarchical Clock Gating (行 455–457)
- 统一门控协调器: 主线/通道门/空间门路径各自完成即关断时钟
- 异步域: 逐层循环折叠 + 空闲阵列时钟关断

#### S2.7 Streaming Line Buffer (行 459–464)
- 移位寄存器级联重构滑窗卷积窗口
- 多bank缓冲: 1写 + 3读 / pipeline stage

#### S2.8 BN + Hard-Sigmoid 硬件实现 (行 475–477)
> **Fig. S2** (`BNRELUHSigmoid.eps`, 行 466–473): (a)BN折叠量化 (b)Hard-Sigmoid移位电路

#### S2.9 PE Microarchitecture (行 478–484)
- 本地FSM控制: 默认休眠→AER事件到达→时钟开启→时间调制MAC→完成→关断

#### S2.10 Memory-Centric SNN Array (行 486–493)
- SRAM 32-bit→4×INT8 权重→4 PE并行
- AER广播 + 层间循环 + 决策单元(比较器树)

#### S2.11 Barrier Synchronization (行 495–498)
- 每阵列轻量屏障同步器(计数器)
- PE完成→计数=激活神经元数→全局完成信号

---

### Supplementary Experiments (行 500–575)

#### S3.1 Ablation Studies (行 501–527)
| 实验 | 配置 | Acc (%) |
|------|------|---------|
| Exp.1 | 完整 DA-SNN | 96.98 |
| Exp.2 | 去除门控 | 93.80 |
| Exp.3 | 标准 Min-Max 归一化 | 97.04 |
| Exp.4 | 固定时间窗 | 92.02 |

> **Table S2** (行 508–527): 消融实验结果

#### S3.2 FPGA Resource (行 529–550)
> **Table S3** (行 533–550): LUT 20.34% / FF 7.67% / BRAM 15.71% / DSP 14.55%

#### S3.3 FPGA Latency & Energy (行 552–574)
> **Table S4** (行 552–570): 0.018ms / 40mW dynamic / 108mW static / 148mW total / 2.66μJ

---

### 补充材料参考文献 (行 578–630)
独立 bibliography (10条): ref65/48/49/50/51/PSE/43/26/conv/ref64

---

## 论文 <-> 代码 关键映射

| 论文概念 | 正文位置 | 补充材料 | 代码位置 |
|---------|---------|---------|---------|
| DSGM | §2.1 (行 134–165) | — | `DA-SNN/model/TTFS.py` → `DSGM` |
| DF-TTFS 编码器 | §2.1 (行 239–255) | S2.2 (行 147–169) | `DA-SNN/model/TTFS.py` → `DF_TTFS_Encoder` |
| ATSNN / B1 神经元 | §2.1 (行 218–267) | S2.1 (行 139), S2.3 (行 171) | `DA-SNN/model/TTFS.py` → `SpikingDense` |
| 自适应时间窗更新 | §2.1 (行 257–267) | S2.3 (行 302–410) | `DA-SNN/common/trainer.py` → `update_snn_time_params()` |
| 深度可分离卷积 | §2.1 (行 136) | — | `DA-SNN/model/TTFS.py` → `DepthwiseSeparableConv` |
| PSE 特征提取 | — | S1.2 (行 120) | `DA-SNN/preprocessing/extract_features.py` |
| 模型组装 | — | — | `DA-SNN/model/TTFS.py` → `build_da_snn()` |
| 量化策略 | §2.4 (行 385–387) | S2.4 (行 413–437) | — |
| FPGA 加速器 | §2.5 (行 391–403) | S2.5–S2.11 (行 439–498) | — |

---

## 注意事项

- 正文用 `nsr` 文档类, 补充材料用 `article` 文档类 — 编译环境不同
- 正文 `\bibliographystyle{nsr}` / 补充材料用 `thebibliography` 环境手动列出
- 正文 METHODS 节为空壳, 实际方法全在补充材料
- Figure/Table 编号: 正文不带前缀, 补充材料带 `S` 前缀
- 正文所有实验数据 (5数据集/15模型) 集中在 Table 1, 效率数据在 Table 2
- 补充材料 Fig. S1/S2 + Table S1–S4 均在本文件内
