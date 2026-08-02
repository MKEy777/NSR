# 论文 Table S3: FPGA资源利用率

来源: supplement.tex (tab:fpga_resource)

平台: Xilinx Zynq-7020 SoC (XC7Z020, speed grade -2, CLG400)


| Resource | Used  | Available | Utilization (%) |
| -------- | ----- | --------- | --------------- |
| LUT      | 10822 | 53200     | 20.34           |
| FF       | 8164  | 106400    | 7.67            |
| BRAM     | 22    | 140       | 15.71           |
| DSP      | 32    | 220       | 14.55           |

## EEGNet 基线对比 (eegnet_top)

来源: `FPGA结果/综合时序资源与实际吞吐分析.md` (综合报告, XC7Z020, xc7z020clg400-2)


| Resource | Used  | Available | Utilization (%) |
| -------- | ----- | --------- | --------------- |
| LUT      | 10977 | 53200     | 28.15           |
| FF       | 37097 | 106400    | 34.87           |
| BRAM     | 22    | 140       | 15.71           |
| DSP      | 5     | 220       | 2.27            |
| IOB      | 120   | 200       | 60.00           |

说明: eegnet_top 综合 PASS；BRAM 为 0 表示数组被 Vivado 综合为寄存器/LUT 结构，而非 BRAM 推断；此表为综合资源，不反映模型精度。
