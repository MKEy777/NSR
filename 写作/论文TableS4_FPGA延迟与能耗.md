# 论文 Table S4: FPGA延迟与能耗测量

来源: supplement.tex (tab:power_comparison)

平台: Xilinx Zynq-7020 SoC, 100 MHz, 1.0 V core supply

| Metric | Value | Unit |
|--------|-------|------|
| Latency | 0.018 | ms |
| Dynamic Power | 40 | mW |
| Static Power | 108 | mW |
| Total Power | 148 | mW |
| Energy / Inference | 2.66 | μJ |

## EEGNet 基线对比 (eegnet_top)

来源: `FPGA结果/综合时序资源与实际吞吐分析.md` (吞吐分析, XC7Z020, xc7z020clg400-2)

| Metric | Value | Unit |
|--------|-------|------|
| Latency / Inference ([4,8,9] EEGNet) | 0.77 | ms |
| Clock | 50 | MHz |
| Cycles / Inference | 38600 | cycles |
| Timing | PASS | — |

说明: 上述为 eegnet_top 模块级综合吞吐（38600 cycles @ 50MHz = 0.77ms/inference），使用 dummy weights，仅反映吞吐而非模型精度。FPGA结果文件中无 eegnet_top 的功耗/能量测量数据，故未补充功率项。
