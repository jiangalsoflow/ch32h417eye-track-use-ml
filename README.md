# 基于 CH32H417 的轻量级眼动 AI 识别边缘部署

> 2026 嵌入式芯片与系统设计竞赛（集创赛 / 沁恒杯）— 芯片应用赛道

## 作品简介

基于沁恒 CH32H417 双核 RISC-V MCU，采用主动红外摄像头采集眼部图像，通过轻量级 CNN 在边缘端本地完成眼球方向与眨眼状态的实时推理，驱动 UI 交互演示（电梯面板）。全程无云端依赖。

**6 类识别**：blind（闭眼）、center（看中间）、down（看下）、left（看左）、right（看右）、up（看上）

## 系统架构

```
┌─────────────┐    DVP (320×240 JPEG)    ┌─────────────────────────────┐
│ OV2640 红外  │ ──────────────────────→ │ CH32H417 双核 RISC-V MCU    │
│ 摄像头       │                         │                             │
└─────────────┘                         │ V3F 核 (120 MHz)            │
                                        │   DVP 采集 + 40×40 ROI 裁剪  │
                                        │         ↓ 共享 SRAM           │
                                        │ V5F 核 (240 MHz)            │
                                        │   JPEG 解码 → 32×32 CNN 推理 │
                                        │   → Softmax 6 类 → UART 输出│
                                        │         ↓ UART 460800 bps    │
                                        └─────────────────────────────┘
                                                      ↓
                                        ┌─────────────────────────────┐
                                        │ PC 端可视化 (Python + OpenCV) │
                                        │   Demo 1: 实时分类结果展示    │
                                        │   Demo 2: 眼控电梯交互       │
                                        └─────────────────────────────┘
```

**所有推理在 MCU 本地完成，PC 端仅做可视化展示，不执行任何分类推理。**

## 硬件规格

| 组件 | 规格 |
|------|------|
| 主控 | WCH CH32H417 (RISC-V 双核, V3F 120MHz + V5F 240MHz, 320KB SRAM) |
| 摄像头 | OV2640 红外 (800×600 → DVP 320×240 JPEG) |
| 开发板 | XPU Labs CH32H417 系列 |
| 外设 | DVP 接口, USART1 |
| 调试器 | WCH-Link |

## CNN 模型规格

| 项目 | 参数 |
|------|------|
| 输入 | 32×32 单通道灰度（复制为 3 通道） |
| 架构 | Conv2D(8, 3×3) + BN + ReLU + MaxPool(4) + Flatten + Dense(6, Softmax) |
| 参数量 | ~3,334 |
| 权重体积 | ~123 KB (float32) / ~4 KB (INT8) |
| 测试准确率 | 96.5% |
| 推理耗时 | ~2 ms/帧 (MCU float32) |
| 帧率 | 3~4 FPS |

## 目录结构

```
eyetrackmain/
├── CH32H417/                              # MCU 固件
│   ├── sdk_ch32h417/
│   │   ├── SRC/                           # 共享 SDK 库 (Core/Debug/Peripheral/Startup/Ld)
│   │   │   ├── Core/      core_riscv.c/h
│   │   │   ├── Debug/     debug.c/h
│   │   │   ├── Peripheral/ 38 个外设驱动 (ch32h417_*.c/h)
│   │   │   ├── Startup/   双核启动文件 (v3f/v5f .S)
│   │   │   └── Ld/        双核链接脚本 (Link_v3f.ld / Link_v5f.ld)
│   │   └── DVP/                            # DVP 摄像头工程 (19 个迭代版本)
│   │       ├── DVP_UART_Step7_Preproc/     # ★ 最终主力工程
│   │       │   ├── Common/                 # 核心模块
│   │       │   │   ├── hardware.c/h        # DVP + 时钟 + UART 初始化
│   │       │   │   ├── inference.c/h       # float32 CNN 手写推理引擎
│   │       │   │   ├── jpeg_dec.c/h        # MCU 整数 JPEG 解码器
│   │       │   │   ├── ov2640.c/h          # OV2640 摄像头驱动
│   │       │   │   └── weights_simple.c    # 导出的 CNN 权重 (float32)
│   │       │   ├── V3F/User/               # V3F 核 (DVP 采集)
│   │       │   │   ├── main.c
│   │       │   │   ├── ch32h417_conf.h
│   │       │   │   ├── ch32h417_it.c/h
│   │       │   │   └── system_ch32h417.c/h
│   │       │   └── V5F/User/               # V5F 核 (CNN 推理 + UART 输出)
│   │       │       └── (同 V3F 文件结构)
│   │       ├── DVP_UART_Step6_Bilinear/    # 双线性插值版本
│   │       ├── DVP_UART_Step4_Fast/        # 定点数快速版本
│   │       ├── DVP_UART_Step1/ ~ Step5/    # 早期迭代版本
│   │       ├── DVP_UART_Test1.2 ~ Test5/   # 测试验证版本
│   │       ├── DVP_UART/                   # WCH 官方 SDK 基线
│   │       ├── DVP_LTDC/                   # LTDC 显示测试
│   │       └── DVP_TFTLCD/                 # TFT LCD 显示测试
│   ├── TFLM_EyeTracking/                   # TensorFlow Lite Micro 实验
│   └── docs_ch32h417/                      # 芯片数据手册 / 参考手册
│
├── code/                                   # PC 端 Python 工具
│   ├── edge_inference_viewer.py            # ★ Demo 1: MCU CNN 分类结果展示
│   ├── elevator_edge_control.py            # ★ Demo 2: 眼控电梯交互演示
│   ├── pc_infer.py                         # PC 端 Keras 实时推理 (验证)
│   ├── serial_viewer.py                    # 数据采集 (实时预览 + 按类保存)
│   ├── train_combined.py                   # 模型训练 (合并数据 + 平衡增强)
│   ├── test_models.py                      # 多模型架构准确率对比
│   ├── export_simple_weights.py            # Keras → C float32 权重
│   ├── export_int8_weights.py              # Keras → C INT8 量化权重
│   ├── eye_tracker.py                      # 终端 MCU 推理结果监控
│   ├── classify_latest.py                  # 手动标注工具
│   ├── label_tool.py                       # 手动标注工具
│   └── crop_coords.json                    # 裁剪坐标配置
│
├── ai/                                     # AI 模型与数据集
│   ├── models/eye_tracking_simple.h5       # 训练好的 Keras 模型
│   ├── dataset/train/  test/              # 训练/测试集 (6 类)
│   └── scripts/                           # 训练辅助脚本
│
├── images/                                 # 旧训练数据 (64×64 灰度)
├── images_new/                             # 主力训练数据 (40×40 灰度)
├── images_latest/                          # 最新采集 (32×32)
├── images_newest/                          # 最新带预测标注 (32×32)
└── docs/                                   # 竞赛文档
```

## 快速开始

### 环境依赖

PC 端 (Python):
```bash
pip install tensorflow opencv-python pyserial numpy
```

MCU 端:
- MounRiver Studio (Eclipse + RISC-V GCC)
- WCH-Link 调试器

### 工作流程

```bash
# 1. 采集训练数据（MCU 需运行推流固件）
python code/serial_viewer.py

# 2. 训练模型
python code/train_combined.py

# 3. PC 端推理验证（接收 MCU JPEG → Keras 推理）
python code/pc_infer.py

# 4. 导出权重到 C 代码（MCU 部署用）
python code/export_simple_weights.py      # float32
python code/export_int8_weights.py        # INT8 量化
```

### 演示工具

```bash
# Demo 1: MCU CNN 推理结果实时展示
python code/edge_inference_viewer.py --port COM6 --baud 460800

# Demo 2: 眼控电梯交互演示
python code/elevator_edge_control.py --port COM6 --baud 460800
```

## MCU 固件

### 编译与烧录

1. MounRiver Studio 打开 `CH32H417/sdk_ch32h417/DVP/DVP_UART_Step7_Preproc/DVP_UART.wvsln`
2. 分别编译 V3F 工程和 V5F 工程
3. V5F 编译时会自动合并 V3F 固件，生成 `Merge.bin`
4. 通过 WCH-Link 烧录 `Merge.bin`

### 串口输出协议 (FW: STEP7_PREPROC v1)

```
FRAME_START
  FRAME_NUM:N
  JPEG_SIZE:S
  DECODE_OK:WxH
  CLASS:direction
  SCORES: blind=p1 center=p2 down=p3 left=p4 right=p5 up=p6
  Infer time:T ticks
  Decode time:D ticks
  JPEG_START
    [JPEG binary data]
  JPEG_END
FRAME_END
```

### 关键注意事项

- **修改 .h 文件后必须删除 `obj/` 目录重建**（MounRiver 增量编译 bug）
- V5F 无 FPU，float32 全由软件模拟，累加精度在 Dense 层会放大
- V5F `printf` 不可用，须用 `send_str()` / `send_u32()` 通过 `USART_SendData()` 输出
- V3F 和 V5F 通过共享 SRAM (`0x20140000`) 交换帧数据
- DVP 摄像头只能在 V3F 核心驱动（V5F 收不全行数据）
- 所有 DVP 工程通过 linked resources 引用共享 `SRC/` 目录，不可删除

### 开发迭代链

DVP 目录下保留了完整的开发迭代记录：

| 工程 | 说明 |
|------|------|
| `DVP_UART/` | WCH 官方 SDK 基线 |
| `DVP_UART_Step1/` ~ `Step4_Fast/` | 逐步集成 JPEG 解码、CNN 推理、UART 输出 |
| `DVP_UART_Step6_Bilinear/` | LUT 优化的双线性插值版本 |
| `DVP_UART_Step7_Preproc/` | **最终版本** — 最近邻重采样，完整推理管线 |
| `DVP_UART_Test*/` | 各阶段测试验证工程 |
| `DVP_LTDC/` `DVP_TFTLCD/` | 显示接口测试 |

## PC 端工具

| 脚本 | 功能 | 依赖 MCU |
|------|------|---------|
| `edge_inference_viewer.py` | **Demo 1**: MCU CNN 分类结果展示 | 是 (推理固件) |
| `elevator_edge_control.py` | **Demo 2**: 眨眼驱动电梯面板交互 | 是 (推理固件) |
| `eye_tracker.py` | 终端文字显示 MCU 分类方向 | 是 (推理固件) |
| `pc_infer.py` | PC 端 Keras 模型实时推理验证 | 是 (推流固件) |
| `serial_viewer.py` | 实时预览 + 按类保存训练图片 | 是 (推流固件) |
| `train_combined.py` | 数据合并 + 平衡增强训练 | 否 |
| `test_models.py` | 多模型架构准确率对比 | 否 |
| `classify_latest.py` | 手动标注图片到分类目录 | 否 |
| `label_tool.py` | 手动标注工具 | 否 |
| `export_simple_weights.py` | Keras 模型 → C float32 权重 | 否 |
| `export_int8_weights.py` | Keras 模型 → C INT8 量化权重 | 否 |

## 数据集

| 目录 | 尺寸 | 每类数量 | 说明 |
|------|------|---------|------|
| `images_new/` | 40×40 灰度 | 25~68 | 主力训练数据 |
| `images/` | 64×64 灰度 | 47~58 | 早期训练数据 |
| `images_latest/` | 32×32 | ~20/类 | 最新采集数据 |
| `images_newest/` | 32×32 | ~8/类 | 带预测标注的采集数据 |

数据增强策略：仅使用**亮度和对比度增强**，不使用平移/旋转/翻转（会破坏瞳孔位置信息）。

## 已知问题

- **MCU float32 推理精度**：V5F 无 FPU，软件 float32 累加误差在 Dense 层的 512 次乘加中被放大
- **INT8 量化对齐**：TFLite 导出的量化参数与手写 C 推理引擎的 scale/zero_point 需逐层精确对齐
- **JPEG 解码器偏差**：MCU 整数 IDCT 与 OpenCV 浮点 IDCT 有约 3.7 灰度级的平均偏差
