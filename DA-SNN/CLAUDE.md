# DA-SNN

> 论文 "An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition" 的 PyTorch 官方实现。
> 基于 **TTFS (Time-To-First-Spike)** 编码的脉冲神经网络，结合 **DSGM 双重注意力机制**，用于 EEG 情感识别。

---

## 目录结构

```
DA-SNN/
├── main.py                      # 统一训练入口（argparse，支持所有数据集）
├── README.md                    # 项目说明与使用文档
├── requirements.txt             # 依赖清单
├── CLAUDE.md                    # 本文件 — 项目大纲，供代码查找参考
│
├── model/
│   ├── __init__.py
│   └── TTFS.py                  # ***核心*** 模型架构定义
│
├── common/
│   ├── __init__.py
│   ├── trainer.py               # 训练逻辑（动态时间窗更新）
│   ├── metrics.py               # 评估逻辑
│   └── utils.py                 # 工具函数（日志、初始化、保存）
│
├── datasets/
│   ├── __init__.py
│   ├── seed.py                  # SEED 数据集加载（3分类）
│   ├── seed_iv.py               # SEED-IV 数据集加载（4分类）
│   ├── seed_v.py                # SEED-V 数据集加载（5分类）
│   ├── deap.py                  # DEAP 数据集加载（4分类）
│   └── dreamer.py               # DREAMER 数据集加载（4分类）
│
├── preprocessing/               # ★ 新增：数据预处理与特征提取
│   ├── __init__.py
│   ├── processing_seed.py       # 原始EEG → 4秒segment（Z-Score标准化）
│   └── extract_features.py      # segments → 功率谱熵特征 → 8×9网格 → LDS平滑
│
└── experiments/
    ├── __init__.py
    ├── seed/train.py             # SEED 实验脚本（引用 configs.*，未完全迁移）
    ├── seed_iv/train.py          # SEED-IV 实验脚本
    ├── seed_v/train.py           # SEED-V 实验脚本
    ├── deap/train.py             # DEAP 实验脚本
    └── dreamer/train.py          # DREAMER 实验脚本
```

---

## 数据流水线

```
原始 EEG .mat 数据
    ↓
【preprocessing/processing_seed.py】  ← Z-Score基线校正 + 4秒切片(62×800)
    ↓
PerSession_4sZScore_62x800/  (每个session的segment: seg_X, seg_y, segs_per_trial)
    ↓
【preprocessing/extract_features.py】 ← 功率谱熵 + 8×9网格映射 + LDS卡尔曼平滑
    ↓
5Feature_PowerSpectrumEntropy_LDS_Smoothed_4x8x9_AllData/all_features_lds_smoothed.mat
    ↓
【datasets/*.py → load_features_from_mat()】  ← 加载 .mat 特征文件
    ↓
【main.py】  ← 训练 DA-SNN 模型
```

---

## 模块详解

### `model/TTFS.py` — 核心模型

| 类/函数 | 作用 | 关键细节 |
|---------|------|---------|
| `DA_SNN` | 模型容器（nn.ModuleList） | forward 遍历 layers_list，收集中间层 min_ti |
| `DepthwiseSeparableConv` | 深度可分离卷积 | 分组卷积 + 1×1逐点卷积，减少参数量 |
| `DSGM` | 双重注意力门控模块 | 通道注意力（AvgPool+Conv+Sigmoid）× 空间注意力（Conv+Sigmoid） |
| `DF_TTFS_Encoder` | TTFS编码器（带动态归一化） | 训练时维护 running_min/max，2的幂缩放，映射到 [t_min, t_max] |
| `SpikingDense` | 脉冲全连接层 | 核心 TTFS 计算：输入为脉冲时间，输出为下一层脉冲时间；outputLayer 使用 D_i 参数做加权求和 |
| `build_da_snn()` | **模型工厂函数** | 组装完整模型：CNN → DSGM → TTFS Encoder → Flatten → Dropout → SpikingDense×3 |

**模型结构链**:
```
input (4,8,9)
  → DepthwiseSeparableConv (stride=2) + BN + ReLU
  → DSGM (双重注意力)
  → DF_TTFS_Encoder (TTFS编码)
  → Flatten
  → Dropout (可选)
  → SpikingDense (hidden_units_1, 隐藏层)
  → SpikingDense (hidden_units_2, 隐藏层)
  → SpikingDense (output_size, outputLayer=true)
```

### `common/trainer.py` — 训练逻辑

| 函数 | 作用 |
|------|------|
| `train_epoch()` | 单epoch训练：前向→损失→反向→动态时间窗更新 |
| `update_snn_time_params()` | 根据脉冲发放时间动态调整下一层时间窗 [t_min, t_max] |
| `apply_time_params()` | 将更新后的时间参数写入 SpikingDense 层 |

**关键机制**: 训练过程中，根据 SpikingDense 层实际脉冲发放的最小时间 t_e，通过 gamma_ttfs 动态调整该层的 t_max，实现时间窗自适应。

### `common/metrics.py` — 评估逻辑

| 函数 | 作用 |
|------|------|
| `evaluate_model()` | 验证集评估，返回 loss、accuracy、所有标签和预测 |

### `common/utils.py` — 工具函数

| 函数 | 作用 |
|------|------|
| `setup_logger()` | 配置控制台+文件双输出日志 |
| `custom_weight_init()` | 自定义权重初始化（SpikingDense: 正态分布; Conv2d: kaiming） |
| `save_model_torch()` | 保存模型权重 .pth 文件 |

### `datasets/*.py` — 数据集加载

所有数据集文件统一接口：

```python
def load_features_from_mat(feature_dir: str) -> Tuple[np.ndarray, np.ndarray]:
    # 加载 all_features.mat，返回 (features, labels)

class NumericalEEGDataset(Dataset):
    # PyTorch Dataset 封装，__getitem__ 返回 (features_tensor, label_tensor)
```

各数据集差异：

| 文件 | 标签处理 | 分类数 |
|------|---------|--------|
| `seed.py` | map {-1→0, 0→1, 1→2} | 3 |
| `seed_iv.py` | 直接使用已有标签 | 4 |
| `seed_v.py` | 直接使用已有标签 | 5 |
| `deap.py` | 直接使用已有标签 | 4 |
| `dreamer.py` | 直接使用已有标签 | 4 |

### `preprocessing/` — 数据预处理

| 文件 | 作用 |
|------|------|
| `processing_seed.py` | 从 Preprocessed_EEG/ 读取原始 .mat，做 Z-Score 基线校正，切片为 4 秒段(62×800)，输出 PerSession_4sZScore_62x800/ |
| `extract_features.py` | 从 segment 数据逐帧计算功率谱熵，映射到 8×9 电极拓扑网格，应用 LDS 卡尔曼平滑，输出特征 .mat |

---

## 关键路径速查

| 需求 | 入口/位置 |
|------|----------|
| 训练模型 | `python main.py --dataset seed` |
| 修改模型结构 | `model/TTFS.py` → `build_da_snn()` |
| 修改TTFS编码 | `model/TTFS.py` → `DF_TTFS_Encoder`、`SpikingDense` |
| 修改注意力机制 | `model/TTFS.py` → `DSGM` |
| 修改训练超参 | `main.py` 的 argparse 参数 |
| 修改时间窗更新 | `common/trainer.py` → `update_snn_time_params()` |
| 添加新数据集 | 在 `datasets/` 新建文件，实现 `load_features_from_mat` + `NumericalEEGDataset`，在 `main.py` 的 `DATASET_DEFAULTS` 注册 |
| 数据预处理 | `preprocessing/processing_seed.py` |
| 特征提取 | `preprocessing/extract_features.py` |

---

## 默认数据集配置（main.py 中 DATASET_DEFAULTS）

| 数据集 | 默认特征目录 | 输入形状 | 分类数 |
|--------|-------------|---------|-------|
| SEED | `Feature_SEED_AllData` | (4, 8, 9) | 3 |
| SEED-IV | `Feature_SEEDIV_AllData` | (4, 8, 9) | 4 |
| SEED-V | `Feature_SEEDV_AllData` | (4, 8, 9) | 5 |
| DEAP | `Feature_DEAP_AllData` | (6, 7, 5) | 4 |
| DREAMER | `Feature_DREAMER_AllData` | (9, 4, 5) | 4 |

---

## 注意事项

- **experiments/ 下的 train.py** 引用 `from configs.seed import CONFIG`，该项目中 **不存在 configs/ 模块**，属于未完全迁移的旧版本代码。当前训练应统一走根目录的 `main.py`。
- `preprocessing/extract_features.py` 的输出路径与 `main.py`/`datasets/*.py` 期望的默认路径不一致，如需自动衔接需要手动调整。
