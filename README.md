# 基于CH32H417的轻量级眼动AI识别边缘部署

> 2026 嵌入式芯片与系统设计竞赛（集创赛 / 沁恒杯）— 芯片应用赛道

## 作品简介

本作品基于沁恒 CH32H417 平台，采用主动红外采集、轻量级 AI 图像识别、边缘端本地推理，实现纯本地部署的眼动交互系统。系统通过红外摄像头（OV2640）采集眼部图像，完成眼球方向与眨眼状态的实时识别，输出光标移动与确认指令，全程无云端依赖。

**6 类识别**：blind（闭眼）、center（看中间）、down（看下）、left（看左）、right（看右）、up（看上）

## 系统架构

```
┌─────────────┐    DVP(320×240 JPEG)    ┌────────────────────────────────┐
│ OV2640 红外  │ ──────────────────────→ │ CH32H417 双核 RISC-V MCU       │
│ 摄像头       │                         │                                │
└─────────────┘                         │ V3F 核 (120MHz)                │
                                        │   DVP 采集 + 40×40 ROI 裁剪镜像 │
                                        │           ↓ 共享 SRAM           │
                                        │ V5F 核 (240MHz)                │
                                        │   JPEG 解码 → 32×32 CNN 推理    │
                                        │   → Softmax 6 类 → UART 输出   │
                                        │           ↓ UART 460800bps      │
                                        └────────────────────────────────┘
                                                       ↓
                                        ┌────────────────────────────────┐
                                        │ PC 端可视化 (Python + OpenCV)   │
                                        │   实时显示分类结果 + UI 交互演示  │
                                        └────────────────────────────────┘
```

**所有推理在 MCU 本地完成，PC 端仅做可视化展示，不执行任何推理。**

## 硬件规格

| 组件 | 规格 |
|------|------|
| MCU | CH32H417 (RISC-V 双核, V3F 120MHz + V5F 240MHz, 320KB SRAM) |
| 摄像头 | OV2640 (800×600 → DVP 320×240 JPEG) |
| 开发板 | XPU Labs CH32H417 系列 |
| 外设 | DVP 接口、USART1 (115200/460800 Baud) |

## CNN 模型规格

| 项目 | 参数 |
|------|------|
| 输入 | 32×32 单通道灰度 |
| 架构 | Conv2D(8, 3×3) + BN + ReLU + MaxPool(4) + Flatten + Dense(6, Softmax) |
| 参数量 | ~3,334 |
| 权重体积 | ~123.2 KB (float32) |
| 测试准确率 | **96.5%** |
| MCU 推理耗时 | ~2ms/帧 |
| 帧率 | 3~4 FPS |

## 目录结构

```
eyetrackmain/
├── CH32H417/                     # MCU 固件工程
│   ├── sdk_ch32h417/DVP/
│   │   └── DVP_UART_Step7_Preproc/  # 主力固件
│   │       ├── Common/              # 共享模块
│   │       │   ├── hardware.c/h     # DVP 驱动 + ISR
│   │       │   ├── inference.c/h    # float32 CNN 推理引擎
│   │       │   ├── jpeg_dec.c/h     # MCU JPEG 解码器
│   │       │   ├── ov2640.c/h       # OV2640 摄像头驱动
│   │       │   └── weights_simple.c # 导出 CNN 权重
│   │       ├── V3F/User/main.c      # V3F 核入口（DVP 采集）
│   │       └── V5F/User/main.c      # V5F 核入口（推理 + UART 输出）
│   └── docs_ch32h417/               # 芯片数据手册 & 参考手册
│
├── code/                          # PC 端 Python 工具
│   ├── train_combined.py          # 模型训练脚本
│   ├── pc_infer.py                # PC 端 Keras 实时推理（验证用）
│   ├── serial_viewer.py           # 数据采集工具
│   ├── export_simple_weights.py   # float32 权重 → C 代码
│   ├── export_int8_weights.py     # INT8 量化权重 → C 代码
│   ├── edge_inference_viewer.py   # ★ Demo 1: MCU CNN 分类结果展示
│   ├── elevator_edge_control.py   # ★ Demo 2: 眼控电梯交互演示
│   ├── eye_tracker.py             # 终端 MCU 推理结果监控
│   ├── classify_latest.py         # 手动标注工具
│   └── test_models.py             # 模型准确率对比
│
├── ai/                            # AI 模型与数据集
│   ├── models/eye_tracking_simple.h5   # 训练好的 Keras 模型
│   ├── dataset/train/  test/           # 训练/测试集
│   └── scripts/                        # 训练辅助脚本
│
├── images/          images_new/   # 训练数据集 (6 类, 32×32~64×64)
├── images_latest/   images_miss/  # 补充训练数据
├── collected_data/                # 采集数据
├── docs/                          # 竞赛文档
├── WORK_PLAN.md                   # 工作清单
└── PROJECT_STATUS.md              # 项目状态 & 踩坑记录
```

## 快速开始

### 环境依赖

**PC 端 (Python)**:
```
pip install tensorflow opencv-python pyserial numpy
```

**MCU 端**:

- MounRiver Studio (Eclipse + RISC-V GCC)
- WCH-Link 调试器

### PC 端工作流

```bash
# 1. 采集训练数据（MCU 需运行推流固件）
python code/serial_viewer.py

# 2. 训练模型
python code/train_combined.py

# 3. PC 端推理验证（接收 MCU JPEG → Keras 推理）
python code/pc_infer.py

# 4. 导出权重到 C 代码（MCU 推理用）
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

## MCU 固件说明

### 编译 & 烧录

1. 用 MounRiver Studio 打开 `CH32H417/sdk_ch32h417/DVP/DVP_UART_Step7_Preproc/DVP_UART.wvsln`
2. 分别编译 V3F 和 V5F 工程
3. 生成合并固件 `Merge.bin`，通过 WCH-Link 烧录

### 注意事项

- **修改 .h 文件后必须删除 `obj/` 目录重建**（MounRiver 增量编译 bug）
- V5F 无 FPU，float32 推理需注意累加精度
- V5F `printf` 不可用，使用 `send_str()` / `send_u32()` 通过 `USART_SendData()` 输出
- V3F 和 V5F 通过共享 SRAM (`0x20140000`) 交换帧数据
- DVP 摄像头只能在 V3F 核心驱动（V5F 收不全行数据）

### MCU 串口输出协议 (STEP7_PREPROC v1)

```
FRAME_START
  FRAME_NUM:N
  JPEG_SIZE:S
  DECODE_OK:320x240
  CLASS:direction
  SCORES: blind=0.01 center=0.92 down=0.01 left=0.02 right=0.02 up=0.02
  Infer time:T ticks
  PREPROC_START
    [1024 bytes 32x32 NN input data]
  PREPROC_END
FRAME_END
```

## 已知问题

- **MCU float32 推理不可靠**：V5F 无 FPU，float32 软件累加误差在 Dense 层被放大，导致分类偶尔错误
- **INT8 量化对齐困难**：TFLite 导出参数与手写 C 推理引擎的逐层 scale/zero_point 对齐需要精确调试
- **JPEG 解码器差异**：MCU 整数 IDCT 与 OpenCV 浮点 IDCT 有约 3.7 灰度级的平均偏差

## PC 端工具一览

| 脚本 | 功能 | 依赖 MCU |
|------|------|---------|
| `train_combined.py` | 数据合并 + 平衡增强训练 | 否 |
| `test_models.py` | 多模型架构准确率对比 | 否 |
| `pc_infer.py` | 接收 MCU JPEG → Keras 推理 | 是（推流固件） |
| `serial_viewer.py` | 实时预览 + 按类别采集训练图片 | 是（推流固件） |
| `classify_latest.py` | 手动标注采集图片到分类目录 | 否 |
| `edge_inference_viewer.py` | **Demo 1**: MCU CNN 分类结果展示 | 是（推理固件） |
| `elevator_edge_control.py` | **Demo 2**: 眨眼驱动电梯面板交互 | 是（推理固件） |
| `eye_tracker.py` | 终端文字显示 MCU 分类方向 | 是（推理固件） |
| `export_simple_weights.py` | Keras 模型 → C float32 权重 | 否 |
| `export_int8_weights.py` | Keras 模型 → C INT8 量化权重 | 否 |

## 数据集

| 目录 | 图像尺寸 | 每类数量 | 说明 |
|------|---------|---------|------|
| `images_new/` | 40×40 灰度 | 25~68 张 | 主力训练数据 |
| `images/` | 64×64 灰度 | 47~58 张 | 旧训练数据 |
| `images_latest/` | 32×32 | ~20 张/类 | 最新采集 |
| `images_miss/` | 32×32 | 4~12 张 | 补充样本 |
| `collected_data/` | 40×40 | - | 原始采集数据 |

数据增强策略：**仅用亮度和对比度增强**，不使用平移/旋转（会破坏瞳孔位置信息）。

