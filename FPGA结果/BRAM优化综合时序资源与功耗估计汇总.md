# 优化版综合、时序与功耗估计汇总

器件：Xilinx Zynq-7020 `xc7z020clg400-2`

## 结论

- 三个模块均已完成独立综合，综合状态均为 PASS。
- BRAM 已成功映射：EEGNet 5.5 tile，PSE 33.5 tile，LDS 1 tile。
- 按已通过时序的频率估计功耗：EEGNet 50MHz，PSE 2MHz，LDS 4MHz。
- 功耗报告为 post-synthesis vectorless estimation，未导入 SAIF/VCD，Confidence Level 为 Low，适合作为不上板阶段估计，不能写成实测功耗。
- 静态功耗约 0.105W，是当前估计中的主要部分；动态功耗分别约为 EEGNet 0.015W、PSE 0.007W、LDS 0.005W。

## 资源与时序汇总

| Module | SynthesisStatus | LUT_Used | LUT_UtilPct | FF_Used | FF_UtilPct | BRAM_Tile_Used | BRAM_UtilPct | DSP_Used | DSP_UtilPct | WNS_100MHz_ns | TNS_100MHz_ns | Timing100MHz | RelaxedFreq_MHz | RelaxedWNS_ns | RelaxedTiming | Simulation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eegnet_top | PASS | 1120 | 2.11 | 239 | 0.22 | 5.5 | 3.93 | 5 | 2.27 | -3.716 | -408.022 | FAIL | 50 | 6.284 | PASS | PASS: logits=(0,0,-1), pred=0 |
| pse_top | PASS | 13550 | 25.47 | 479 | 0.45 | 33.5 | 23.93 | 44 | 20 | -430.179 | -16790.396 | FAIL | 2 | 59.821 | PASS | PASS: pse_q16=33612, pse_float=0.512878 |
| lds_kalman_top | PASS | 4797 | 9.02 | 374 | 0.35 | 1 | 0.71 | 8 | 3.64 | -190.346 | -18175.254 | FAIL | 4 | 49.654 | PASS | PASS: 864 outputs match golden |

## 功耗估计汇总

| Module | Frequency_MHz | Period_ns | Total_OnChip_W | Dynamic_W | Static_W | Clock_W | Logic_W | Signal_W | BRAM_W | DSP_W | IO_W | Confidence | Activity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| eegnet_top | 50 | 20 | 0.12 | 0.015 | 0.105 | 0.001 | 0.004 | 0.004 | 0.003 | 0.003 | <0.001 | Low | Vectorless/default switching; no SAIF/VCD |
| pse_top | 2 | 500 | 0.113 | 0.007 | 0.106 | <0.001 | 0.004 | 0.002 | <0.001 | <0.001 | <0.001 | Low | Vectorless/default switching; no SAIF/VCD |
| lds_kalman_top | 4 | 250 | 0.109 | 0.005 | 0.105 | <0.001 | 0.003 | 0.002 | <0.001 | <0.001 | <0.001 | Low | Vectorless/default switching; no SAIF/VCD |

## 功耗口径说明

- Static Power / Device Static：芯片漏电和静态偏置相关，不随单次输入数据大幅变化。
- Dynamic Power：由时钟和信号翻转导致，本次未导入真实活动文件，因此依赖 Vivado 默认翻转率。
- Clock Power：时钟网络功耗；低频模块会明显降低时钟动态功耗。
- Logic / Signal / BRAM / DSP / IO Power：按资源类别估计的动态功耗贡献。
- 若要提升可信度，应在实现后导入 SAIF/VCD，或最终以上板电流实测为准。
