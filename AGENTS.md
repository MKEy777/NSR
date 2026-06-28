# NSR 论文大修项目

> **论文标题**: "An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition"
> **投稿期刊**: National Science Review (NSR)
> **当前状态**: 大修 (Major Revision)
> **项目路径**: `c:\Users\VECTOR\Desktop\NSR`

---

## 项目结构

```
NSR/
├── .Codex/                     # Codex 项目配置
├── .gitignore                   # Git 忽略规则（数据/缓存/实验输出/构建产物）
├── AGENTS.md                    # 本文件 — 项目级大纲
├── 大修意见.docx                 # 审稿人意见（原始文件）
├── 大修意见.md                   # 审稿人意见（已转 Markdown，42 条）
├── 大修意见_中英对照.md           # 中英对照版（原文 + 中文凝练大意）
├── 大修意见.assets/              #    意见中嵌入的图片
├── 大修计划.md                   # 修改任务跟踪（逐步填充）
├── 论文大修进度.md                # 大修进度文档（20 任务组，逐步状态跟踪）
├── 服务器实验运行命令.md           # 服务器端预检与正式实验 Linux 命令清单
│
├── Complete DA-SNN Experiment Code/  # ★ 实验代码（最新，5 数据集完整管线）
│   ├── model/TTFS.py               #    核心模型：DSGM + DF_TTFS_Encoder + SpikingDense
│   ├── common/                      #    统一实验组件：配置、数据拆分、模型构建、训练、指标、噪声注入
│   │   ├── config.py                #    数据集配置与默认特征路径
│   │   ├── data_loader.py           #    feature bundle 加载、LOSO / subject_80_20 / random_80_20 split
│   │   ├── model_builder.py         #    DA-SNN 与基线模型统一构建入口
│   │   ├── trainer.py               #    统一训练、验证、测试与结果保存
│   │   ├── metrics.py               #    指标计算与 CSV/JSON 写出
│   │   └── noise_injector.py        #    StandardMinMaxEncoder 与 T3 噪声注入
│   ├── Preprocessing/              #    5 数据集 × 2-stage 预处理管线；数据目录用 .gitkeep 保留结构，真实数据由 .gitignore 排除
│   │   ├── SEED/                   #    processing_seed.py → extract_features.py
│   │   ├── SEEDIV/                 #    preprocessing.py → extraction.py
│   │   ├── SEEDV/                  #    MNE .cnt → preprocessing.py → extraction.py
│   │   ├── DEAP/                   #    preprocessing.py → extraction.py
│   │   └── DREAMER/               #    preprocessing.py → extraction.py
│   ├── train_seed.py               #    SEED 训练（3-class，含动态时间窗更新）
│   ├── train_seed_IV.py            #    SEED-IV 训练（4-class）
│   ├── train_seed_V.py             #    SEED-V 训练（5-class，subject-independent）
│   ├── train_deap.py               #    DEAP 训练（4-class valence×arousal）
│   ├── train_dreamer.py            #    DREAMER 训练（4-class valence×arousal）
│   ├── run_experiments.py          #    统一 CLI：数据集 / 模型 / 协议 / seed / 噪声配置
│   └── tests/                      #    统一实验代码的 pytest 回归测试
│
├── DA-SNN/                      # ★ 原始开源代码（旧版参考）
│   ├── main.py                  #    统一训练入口
│   ├── model/TTFS.py            #    核心模型
│   ├── common/                  #    训练逻辑 / 评估 / 工具
│   ├── datasets/                #    数据加载
│   ├── preprocessing/           #    特征提取
│   └── experiments/             #    旧版实验脚本
│
├── 对比模型/                    # ★ 对比模型实现
│   ├── Deep ConvNet.py
│   ├── DH-SNN.py
│   ├── EEGNet.py
│   ├── EfficientNet-B0.py
│   ├── EfficientNet-B3.py
│   ├── MobileNetV3-Large.py
│   ├── MobileNetV3-Small.py
│   ├── Shallow ConvNet.py
│   ├── ShuffleNetV2 .py
│   └── SqueezeNetV2.py
│
└── NSR_Author/                  # ★ 论文手稿（LaTeX）
    ├── AGENTS.md                #    正文/补充材料大纲速查
    ├── main.tex                 #    正文（~41KB）
    ├── supplement.tex           #    补充材料（~32KB）
    └── nsr_sample.bib           #    参考文献
```

---

## 关键关系

> 当前实验以 `Complete DA-SNN Experiment Code/` 为准，`DA-SNN/` 为旧版参考。

| 论文概念 | 代码位置 |
|---------|---------|
| DSGM 双重注意力门控 | `Complete DA-SNN Experiment Code/model/TTFS.py` → `DSGM` |
| TTFS 编码器 | `Complete DA-SNN Experiment Code/model/TTFS.py` → `DF_TTFS_Encoder` |
| 脉冲全连接层 / 自适应时间窗 | `Complete DA-SNN Experiment Code/model/TTFS.py` → `SpikingDense` |
| 动态时间窗更新机制 | `Complete DA-SNN Experiment Code/common/trainer.py` → `_update_time_windows()` |
| 深度可分离卷积 | `Complete DA-SNN Experiment Code/model/TTFS.py` → `DepthwiseSeparableConv` |
| 功率谱熵特征提取 | `Complete DA-SNN Experiment Code/Preprocessing/*/extract_features.py` 或 `extraction.py` |
| 模型组装 | `Complete DA-SNN Experiment Code/common/model_builder.py` → `build_model()` / `build_da_snn()` |
| 噪声注入与 StandardMinMaxEncoder | `Complete DA-SNN Experiment Code/common/noise_injector.py` |
| 预计算特征文件 | `Complete DA-SNN Experiment Code/Preprocessing/*/Feature_*/*.mat` |

---

## 修改工作流

1. **审阅审稿意见** → 读取 `大修意见.md`（已从 docx 转换，4 位审稿人 / 42 条）
2. **制定修改计划** → 参考 `大修计划.md`（7 大类，逐条应对方案）
3. **代码修改** → 在 `Complete DA-SNN Experiment Code/` 中实施实验/代码层面的修改
4. **论文修改** → 在 `NSR_Author/main.tex` 和 `supplement.tex` 中修改正文与补充材料
5. **逐条验证** → 确保每条意见都有对应修改，且代码与论文一致

---

## 注意事项

- `大修意见.docx` 已转为 `大修意见.md`（4 位审稿人，42 条意见），所有修改工作以此英文版为准
- `大修意见_中英对照.md` 是给用户阅读用的，Codex 工作时只看英文版 `大修意见.md`
- 论文使用 `nsr` 文档类（NSR 期刊模板），注意 LaTeX 编译兼容性
- `DA-SNN/` 为旧版参考代码，当前实验以 `Complete DA-SNN Experiment Code/` 为准
- `Complete DA-SNN Experiment Code/` 中训练脚本高度重复（5 个 95% 相同），消融实验统一运行时需先做模块化重构
- `Complete DA-SNN Experiment Code/Preprocessing/*/Feature_*/*.mat` 含预计算特征文件，可直接用于训练，无需重跑预处理
- **自维护规则**: 每次在本项目中创建、删除或重命名文件后，必须同步更新本 AGENTS.md（尤其是「项目结构」部分），确保文件清单始终反映当前实际状态
