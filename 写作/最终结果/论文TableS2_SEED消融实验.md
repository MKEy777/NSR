# 论文 Table S2: 三数据集消融实验

来源: supplement.tex (tab:supp_ablation)

指标: Acc (Accuracy %), F1 (F1-score %), Spe (Specificity %)，报告 mean ± std

## SEED

| Models | Acc (%) | F1 (%) | Spe (%) |
|--------|---------|--------|---------|
| Full (DA-SNN) | 96.85 ± 1.44 | 96.81 ± 0.92 | 97.08 ± 0.87 |
| No Depthwise Separable | 94.98 ± 0.51 | 94.95 ± 1.06 | 95.17 ± 0.45 |
| No DSGM | 93.65 ± 0.78 | 93.78 ± 1.33 | 93.41 ± 1.00 |
| No TTFS Encoder (Std Min-Max) | 96.91 ± 1.02 | 96.89 ± 1.46 | 97.15 ± 1.08 |
| No Dynamic Window | 91.87 ± 0.54 | 91.82 ± 0.68 | 92.03 ± 1.45 |

## DEAP

| Models | Acc (%) | F1 (%) | Spe (%) |
|--------|---------|--------|---------|
| Full (DA-SNN) | 87.96 ± 5.44 | 86.83 ± 8.53 | 97.62 ± 3.20 |
| No Depthwise Separable | 83.12 ± 6.32 | 81.89 ± 1.79 | 95.75 ± 2.80 |
| No DSGM | 70.38 ± 3.16 | 67.27 ± 3.95 | 91.25 ± 5.70 |
| No TTFS Encoder (Std Min-Max) | 86.89 ± 1.55 | 74.93 ± 5.48 | 93.68 ± 7.96 |
| No Dynamic Window | 77.21 ± 2.46 | 75.18 ± 5.83 | 93.77 ± 5.32 |

## DREAMER

| Models | Acc (%) | F1 (%) | Spe (%) |
|--------|---------|--------|---------|
| Full (DA-SNN) | 94.18 ± 2.20 | 91.73 ± 2.56 | 94.38 ± 4.64 |
| No Depthwise Separable | 88.78 ± 1.42 | 84.99 ± 2.38 | 92.43 ± 4.70 |
| No DSGM | 93.81 ± 5.01 | 90.95 ± 4.52 | 94.27 ± 0.88 |
| No TTFS Encoder (Std Min-Max) | 94.84 ± 2.92 | 92.83 ± 3.63 | 96.31 ± 2.81 |
| No Dynamic Window | 93.35 ± 1.55 | 91.00 ± 3.29 | 95.33 ± 0.78 |

说明:
- Full (DA-SNN): 完整模型（DSGM + DF-TTFS + 自适应时间窗）
- No Depthwise Separable: 移除深度可分离卷积
- No DSGM: 移除双重注意力门控
- No TTFS Encoder (Std Min-Max): 用标准浮点 min-max 归一化替代无除法归一化
- No Dynamic Window: 禁用自适应时间窗，使用固定时间窗
