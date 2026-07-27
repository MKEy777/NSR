# NSR 论文大修项目

> **论文标题**: "An Asynchronous Neuromorphic Architecture for Wearable EEG Emotion Recognition"
> **投稿期刊**: National Science Review (NSR)
> **当前状态**: 大修 (Major Revision)
> **项目路径**: `c:\Users\VECTOR\Desktop\NSR`

---

## 项目结构

```
NSR/
├── .claude/                     # Claude 项目配置与记忆（memory/）
├── .agents/                     # Agent 配置占位目录
├── CLAUDE.md                    # 本文件 — 项目级大纲
├── 大修意见_中英对照.md           # 中英对照版（原文 + 中文凝练大意，用户阅读用）
├── 大修意见.assets/              # 意见中嵌入的图片（wps1-14.png）
│
├── docs/                        # ★ 文档与计划
│   ├── 大修意见.md               #    审稿人意见（英文版，工作以此为准）
│   ├── 大修计划.md               #    修改任务跟踪（逐条应对方案）
│   ├── 3周实验排期计划.md         #    实验排期计划
│   └── 服务器实验运行命令.md      #    服务器实验 CLI 命令速查
│
├── Complete DA-SNN Experiment Code/  # ★ 实验代码（最新，已模块化，5 数据集完整管线）
│   ├── run_experiments.py          #    ★ 统一实验入口（数据集/模型/协议/噪声/消融）
│   ├── train_seed.py               #    薄封装 → run_experiments.main()（其余 4 个同理）
│   ├── train_seed_IV.py            #    薄封装（train_seed_V/deap/dreamer 均为 6 行封装）
│   ├── model/TTFS.py               #    核心模型：DSGM + DF_TTFS_Encoder + SpikingDense + DepthwiseSeparableConv + HardSigmoid + DA_SNN
│   ├── common/                     #    ★ 公共库（重构后抽取的共享模块）
│   │   ├── config.py               #      DatasetConfig / DATASET_CONFIGS / resolve_feature_file
│   │   ├── data_loader.py          #      DatasetBundle/Split/EEGTensorDataset + loso/subject/random 切分
│   │   ├── model_builder.py        #      MODEL_NAMES(10) / build_model / InputShapeAdapter
│   │   ├── trainer.py              #      ExperimentConfig / run_experiment（训练循环 + 动态时间窗）
│   │   ├── metrics.py              #      compute_metrics / summarize_runs / write_csv / write_json
│   │   └── noise_injector.py       #      StandardMinMaxEncoder + inject_noise（推理期特征域噪声）
│   ├── Preprocessing/              #    5 数据集 × 2-stage 预处理管线
│   │   ├── SEED/                   #      processing_seed.py → extract_features.py
│   │   │   ├── feature_core.py     #        共享特征原语（PSE / 8×9 映射 / LDS 平滑）
│   │   │   ├── noise_utils.py      #        T3 原始 EEG 噪声注入（gaussian/drift/emg）
│   │   │   └── extract_features_noise.py  #  T3 鲁棒性：原始域注噪 → 重提特征（按 tag 输出）
│   │   ├── SEEDIV/                 #      preprocessing.py → extraction.py
│   │   ├── SEEDV/                  #      MNE .cnt → preprocessing.py → extraction.py
│   │   ├── DEAP/                   #      preprocessing.py → extraction.py
│   │   └── DREAMER/                #      preprocessing.py → extraction.py
│   ├── analysis/window_evolution.py  #  动态时间窗演化记录（使用 common/ 导入）
│   ├── experiments/jacobian_spectrum.py  # Jacobian 谱分析（占位，待实现）
│   ├── tests/                      #    ★ 测试套件（pytest）
│   │   ├── conftest.py             #      注入项目根到 sys.path
│   │   ├── test_data_loader.py     #      切分与特征加载
│   │   ├── test_model_builder.py   #      10 模型均可构建（含 efficientnet_b3 已移除断言）
│   │   ├── test_run_experiments.py #      dry-run 集成测试
│   │   ├── test_trainer_smoke.py   #      run_experiment 端到端冒烟
│   │   └── test_ttfs.py            #      DA_SNN 前向 / SpikingDense NaN 保护
│   ├── experiment_outputs/         #    实验结果（loso / subject_80_20，及任务码 t2_ablation/t3_noise/t5_random_80_20）
│   ├── preflight_outputs/          #    单被试全模型 GPU 预检结果
│   ├── preflight_splits/           #    LOSO 切分索引缓存
│   └── verify_t6_t7_t8/            #    T6-T8 验证结果（summary_all.csv）
│
├── DA-SNN/                      # ★ 原始开源代码（旧版参考）
│   ├── main.py                  #    统一训练入口
│   ├── model/TTFS.py            #    核心模型
│   ├── common/                  #    训练逻辑 / 评估 / 工具
│   ├── datasets/                #    数据加载
│   ├── preprocessing/           #    特征提取
│   └── experiments/             #    旧版实验脚本
│
├── 对比模型/                    # ★ 对比模型实现（10 个 .py；registry 已移除 efficientnet_b3）
│   ├── Deep ConvNet.py
│   ├── DH-SNN.py
│   ├── EEGNet.py
│   ├── EfficientNet-B0.py
│   ├── EfficientNet-B3.py       #    文件保留，但未在 MODEL_NAMES 注册
│   ├── MobileNetV3-Large.py
│   ├── MobileNetV3-Small.py
│   ├── Shallow ConvNet.py
│   ├── ShuffleNetV2 .py
│   └── SqueezeNetV2.py
│
├── analysis_old/               # ★ 旧版 window_evolution（依赖 DA-SNN/，含 npy/pdf/png 产物）
│
├── FPGA结果/                    # ★ FPGA 综合时序/资源/吞吐分析（.md + .xlsx）
│
├── token-optimizer/            # Token 用量追踪工具（会话数据库 / trends.db）
├── .tmp-token-optimizer/       # token-optimizer 工具仓库暂存副本
│
└── NSR_Author/                  # ★ 论文手稿（LaTeX）
    ├── CLAUDE.md                #    正文/补充材料大纲速查
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
| 深度可分离卷积 | `Complete DA-SNN Experiment Code/model/TTFS.py` → `DepthwiseSeparableConv` |
| 动态时间窗更新机制 | `Complete DA-SNN Experiment Code/common/trainer.py` → `run_experiment()`（公共模块，非各脚本 inline） |
| 模型组装 / 模型注册表 | `Complete DA-SNN Experiment Code/common/model_builder.py` → `build_model()` / `MODEL_NAMES` |
| 数据集配置 / 特征路径解析 | `Complete DA-SNN Experiment Code/common/config.py` → `DATASET_CONFIGS` / `resolve_feature_file()` |
| 评估协议切分（LOSO / 80-20 / random） | `Complete DA-SNN Experiment Code/common/data_loader.py` → `build_splits()` |
| 功率谱熵特征提取 | `Complete DA-SNN Experiment Code/Preprocessing/*/extract_features.py` 或 `extraction.py`（SEED 共享 `feature_core.py`） |
| T3 噪声鲁棒性（原始域注噪） | `Complete DA-SNN Experiment Code/Preprocessing/SEED/extract_features_noise.py` + `noise_utils.py` |
| 预计算特征文件 | `Complete DA-SNN Experiment Code/Preprocessing/*/Feature_*/*.mat` |

---

## 修改工作流

1. **审阅审稿意见** → 读取 `docs/大修意见.md`（已从 docx 转换，4 位审稿人 / 42 条）
2. **制定修改计划** → 参考 `docs/大修计划.md`（逐条应对方案）；实验排期见 `docs/3周实验排期计划.md`
3. **代码修改** → 在 `Complete DA-SNN Experiment Code/` 中实施；统一入口 `run_experiments.py`，公共逻辑改 `common/`
4. **运行实验** → `run_experiments.py --dataset <ds> --model <name|all> --protocol <loso|subject_80_20|random_80_20> ...`（命令见 `docs/服务器实验运行命令.md`）
5. **论文修改** → 在 `NSR_Author/main.tex` 和 `supplement.tex` 中修改正文与补充材料
6. **逐条验证** → 确保每条意见都有对应修改，且代码与论文一致；改动 `common/` 后跑 `tests/`

---

## 注意事项

- 审稿意见工作以英文版 `docs/大修意见.md` 为准（4 位审稿人，42 条）；`大修意见_中英对照.md` 仅供用户阅读
- 论文使用 `nsr` 文档类（NSR 期刊模板），注意 LaTeX 编译兼容性
- `DA-SNN/` 为旧版参考代码，当前实验以 `Complete DA-SNN Experiment Code/` 为准
- **代码已完成模块化重构**：5 个 `train_*.py` 现为 6 行薄封装，统一委托 `run_experiments.py`；共享逻辑集中在 `common/`
- `run_experiments.py` 支持 5 数据集、10 模型（`--model all`）、3 协议，以及 T3 噪声扫描（`--noise gaussian|drift|emg`，6 个 NL 档）和消融开关（`--no-dsgm` / `--no-ttfs-encoder` / `--no-depthwise-separable` / `--no-dynamic-window`）
- 实验产物按任务码组织：`t2_ablation`（T2 消融）、`t3_noise`（T3 噪声）、`t5_random_80_20`（T5）、`verify_t6_t7_t8`（T6-T8）
- `Complete DA-SNN Experiment Code/Preprocessing/*/Feature_*/*.mat` 含预计算特征文件，可直接用于训练，无需重跑预处理；SEED 另有 `*_<noise>_NL*.mat` 噪声特征包
- `efficientnet_b3` 已从 `MODEL_NAMES` 注册表移除（`对比模型/EfficientNet-B3.py` 文件仍保留）
- **自维护规则**: 每次在本项目中创建、删除或重命名文件后，必须同步更新本 CLAUDE.md（尤其是「项目结构」部分），确保文件清单始终反映当前实际状态
