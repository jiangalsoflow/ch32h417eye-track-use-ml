# TFLM 眼动推理引擎设计

## 目标
在 CH32H417 V5F 核上，用 TFLM 框架跑 eye_tracking_float32.tflite（95KB），通过串口输出 6 类眼球方向。

## 架构

```
V3F: OV2640采集 → DVP DMA → SRAM
V5F: SRAM取图 → 裁剪32×32 → TFLM推理 → 串口输出结果
```

## 改动范围

基于 TFLM_TinyML_CH32H417 项目，修改：

1. 新增 eye_tracking_model_data.cc/.h — 模型 C 数组（已生成）
2. op_resolver: DepthwiseConv2D→MaxPool2D, AvgPool2D→FullyConnected
3. 输入: 96×96灰度int8 → 32×32×3 float32
4. 输出: 2类int8 → 6类float32
5. Tensor Arena: 136KB → 120KB

## 测试标准
- 用训练集图像验证：MCU 输出和 PC 端推理输出一致（容差 0.01）
- 推理耗时 < 100ms
- RAM 峰值 < 200KB

## 后续
验证通过后接入 DVP 实时采集 + PC GUI
