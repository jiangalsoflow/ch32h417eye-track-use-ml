# 手写推理引擎实现计划

> **For agentic workers:** Use inline execution — follow every step, verify each checkpoint.

**Goal:** 用纯 C 语言在 CH32H417 V5F 上实现眼动追踪推理（Conv2D/BN/ReLU/MaxPool/Dense/Softmax），float32 精度，与 PC 端 Python 推理结果一致。

**Architecture:** 权重 int8 → 初始化解量化为 float32 → 全 float32 推理 → 6 类 softmax 输出。所有代码纯 C（`.c` 文件），MounRiver C 编译器直接编译，零 C++ 依赖。

**Tech Stack:** C (GNU99), float32, CH32H417 V5F (240MHz + HW FPU), 已有 `model_weights_6class.c`

---

## 文件结构

```
DVP_UART/Common/
├── inference.h          ← 推理引擎头文件（新建）
├── inference.c          ← 推理引擎实现（新建，~400行）
└── hardware.c           ← 修改：FRM_DONE 后调用推理（1行改动）

PC端验证：
code/verify_inference.py  ← PC端对比验证脚本（新建）
```

---

### Task 1: 创建推理引擎头文件

**Files:**
- Create: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.h`

- [ ] **Step 1: 写头文件**

```c
#ifndef INFERENCE_H
#define INFERENCE_H

#include <stdint.h>

#define NUM_CLASSES 6

extern const char* class_names[NUM_CLASSES];

// 初始化：调用一次，将 int8 权重量化为 float32
void inference_init(void);

// 推理：输入 32x32x3 float32 RGB，输出 6 类分数
void inference_run(const float* input, float* output);

// 释放推理内存
void inference_deinit(void);

#endif
```

- [ ] **Step 2: 验证** — 检查 MounRiver 能否找到此头文件（include path `${project}/Common` 已存在）

---

### Task 2: 写出 PC 端 Python 对比脚本

**Files:**
- Create: `code/verify_inference.py`

先写 PC 端验证，确保每一层的实现和 TensorFlow 输出一致。

- [ ] **Step 1: 写 PC 端推理参考实现**

```python
import numpy as np
import tensorflow as tf

# 加载原始模型
interpreter = tf.lite.Interpreter(
    model_path='D:/AI Module/Eye_Tracking/models/eye_tracking_float32.tflite')
interpreter.allocate_tensors()

# 用随机输入跑推理
np.random.seed(42)
test_input = np.random.randn(1, 32, 32, 3).astype(np.float32)

interpreter.set_tensor(interpreter.get_input_details()[0]['index'], test_input)
interpreter.Invoke()
ref_output = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])

print("Reference output:")
labels = ['blind', 'center', 'down', 'left', 'right', 'up']
for i, name in enumerate(labels):
    print(f"  {name}: {ref_output[0][i]:.6f}")

# 保存输入和参考输出供 C 代码测试
test_input.tofile('code/test_input.bin')
ref_output.tofile('code/ref_output.bin')
print("\nSaved test_input.bin and ref_output.bin")
```

- [ ] **Step 2: 运行验证**

```bash
python code/verify_inference.py
```

期望：打印 6 个分类分数，生成两个 bin 文件。

---

### Task 3: 实现推理引擎 — 基础框架 + 权重加载

**Files:**
- Create: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.c`（第一版）

- [ ] **Step 1: 写框架代码**

```c
#include "inference.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>

const char* class_names[NUM_CLASSES] = {"blind", "center", "down", "left", "right", "up"};

// ======== 从 model_weights_6class.c 导入的权重 ========
// 所有 int8 权重的 scale 和原始数组（extern 声明，link 时合并）
extern const float conv2d_kernel_scale;
extern const int8_t conv2d_kernel[];        // shape: (3,3,3,16) size: 432
extern const float conv2d_bias_scale;
extern const int8_t conv2d_bias[];           // shape: (16,)

extern const float batch_normalization_kernel_scale;
extern const int8_t batch_normalization_kernel[]; // BN gamma: (16,)
// ... (各层权重类似)

// ======== 推理所需 float32 权重（init 时分配）========
static float *w_conv1, *b_conv1, *bn1_gamma, *bn1_beta, *bn1_mean, *bn1_var;
// ... 每一层同理

void inference_init(void) {
    // 分配并解量化 Conv1 权重
    w_conv1 = malloc(3*3*3*16 * sizeof(float));
    for (int i = 0; i < 3*3*3*16; i++)
        w_conv1[i] = conv2d_kernel[i] * conv2d_kernel_scale;
    // ... 每一层同理
}

void inference_deinit(void) {
    free(w_conv1);
    // ... 释放所有
}
```

- [ ] **Step 2: 编译验证** — Build V3F + V5F，确认 `inference.c` 能成功编译（链接错误 OK，函数还没写完）

---

### Task 4: 实现 Conv2D + BatchNorm 融合算子

**Files:**
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.c`

由于 BN 可以在推理时融合进 Conv2D 权重（`w_fused = w * gamma / sqrt(var+eps)`, `b_fused = (b - mean) * gamma / sqrt(var+eps) + beta`），在 `inference_init()` 里一次算好，推理时只需做 Conv2D。

- [ ] **Step 1: 实现 conv2d_reference 函数**

```c
// NCHW 格式：input[C][H][W], kernel[OC][IC][KH][KW], output[OC][OH][OW]
static void conv2d_same_pad(
    const float* input,  int H,  int W,  int IC,
    const float* weight, int KH, int KW, int OC,
    const float* bias,
    float* output)
{
    int OH = H, OW = W;  // same padding, stride=1
    int pad_h = KH / 2, pad_w = KW / 2;

    // 零初始化输出然后累加 bias
    for (int oc = 0; oc < OC; oc++)
        for (int oh = 0; oh < OH; oh++)
            for (int ow = 0; ow < OW; ow++)
                output[(oc * OH + oh) * OW + ow] = bias[oc];

    for (int oc = 0; oc < OC; oc++)
        for (int ic = 0; ic < IC; ic++)
            for (int kh = 0; kh < KH; kh++)
                for (int kw = 0; kw < KW; kw++)
                    for (int oh = 0; oh < OH; oh++)
                        for (int ow = 0; ow < OW; ow++)
                        {
                            int ih = oh + kh - pad_h;
                            int iw = ow + kw - pad_w;
                            if (ih >= 0 && ih < H && iw >= 0 && iw < W)
                            {
                                float w = weight[((oc * IC + ic) * KH + kh) * KW + kw];
                                float v = input[(ic * H + ih) * W + iw];
                                output[(oc * OH + oh) * OW + ow] += w * v;
                            }
                        }
}
```

- [ ] **Step 2: 用 PC 验证** — 写一个小 Python 脚本，用 numpy 跑同样的 conv 操作，和 TensorFlow 中间层输出对比。确保数值误差 < 0.001。

---

### Task 5: 实现 ReLU + MaxPool

**Files:**
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.c`

- [ ] **Step 1: 实现 ReLU**

```c
static void relu_inplace(float* data, int N) {
    for (int i = 0; i < N; i++)
        if (data[i] < 0.0f) data[i] = 0.0f;
}
```

- [ ] **Step 2: 实现 MaxPool 2×2**

```c
// input: [OC][H][W], output: [OC][H/2][W/2]
static void maxpool2d(const float* input, int H, int W, int OC, float* output) {
    int OH = H / 2, OW = W / 2;
    for (int oc = 0; oc < OC; oc++)
        for (int oh = 0; oh < OH; oh++)
            for (int ow = 0; ow < OW; ow++) {
                float m = input[(oc * H + oh*2) * W + ow*2];
                for (int dh = 0; dh < 2; dh++)
                    for (int dw = 0; dw < 2; dw++) {
                        float v = input[(oc * H + oh*2+dh) * W + ow*2+dw];
                        if (v > m) m = v;
                    }
                output[(oc * OH + oh) * OW + ow] = m;
            }
}
```

- [ ] **Step 3: PC 验证** — numpy vs C 对比

---

### Task 6: 实现 Dense (FullyConnected)

**Files:**
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.c`

- [ ] **Step 1: 实现 Dense 层**

```c
// input: [N_in], weight: [N_in][N_out], bias: [N_out], output: [N_out]
static void dense(const float* input, int N_in,
                  const float* weight, const float* bias,
                  float* output, int N_out) {
    for (int o = 0; o < N_out; o++) {
        float sum = bias[o];
        for (int i = 0; i < N_in; i++)
            sum += input[i] * weight[o * N_in + i];
        output[o] = sum;
    }
}
```

---

### Task 7: 实现 Softmax

- [ ] **Step 1: 实现 Softmax**

```c
static void softmax(float* data, int N) {
    // Find max for numerical stability
    float max_val = data[0];
    for (int i = 1; i < N; i++)
        if (data[i] > max_val) max_val = data[i];
    
    float sum = 0.0f;
    for (int i = 0; i < N; i++) {
        data[i] = expf(data[i] - max_val);
        sum += data[i];
    }
    for (int i = 0; i < N; i++)
        data[i] /= sum;
}
```

---

### Task 8: 组装 inference_run()

**Files:**
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/inference.c`

- [ ] **Step 1: 实现完整推理流程**

```c
void inference_run(const float* input, float* output) {
    // 动态分配临时缓冲区（最大中间层尺寸）
    int max_buf = 32*32*128;  // Conv1 激活 or Conv4 激活
    float *buf1 = malloc(max_buf * sizeof(float));
    float *buf2 = malloc(max_buf * sizeof(float));
    float *buf3 = malloc(max_buf * sizeof(float));

    // Conv1: 32x32x3 → 32x32x16
    conv2d_same_pad(input, 32, 32, 3, w_conv1_fused, 3, 3, 16, b_conv1_fused, buf1);
    relu_inplace(buf1, 32*32*16);
    maxpool2d(buf1, 32, 32, 16, buf2);  // → 16x16x16

    // Conv2: 16x16x16 → 16x16x32
    conv2d_same_pad(buf2, 16, 16, 16, w_conv2_fused, 3, 3, 32, b_conv2_fused, buf1);
    relu_inplace(buf1, 16*16*32);
    maxpool2d(buf1, 16, 16, 32, buf2);  // → 8x8x32

    // Conv3: 8x8x32 → 8x8x64
    conv2d_same_pad(buf2, 8, 8, 32, w_conv3_fused, 3, 3, 64, b_conv3_fused, buf1);
    relu_inplace(buf1, 8*8*64);
    maxpool2d(buf1, 8, 8, 64, buf2);  // → 4x4x64

    // Conv4: 4x4x64 → 4x4x128
    conv2d_same_pad(buf2, 4, 4, 64, w_conv4_fused, 3, 3, 128, b_conv4_fused, buf1);
    relu_inplace(buf1, 4*4*128);
    maxpool2d(buf1, 4, 4, 128, buf2);  // → 2x2x128

    // Flatten: 2x2x128 = 512
    // (buf2 already contains the flattened data)

    // Dense 1: 512→128 + BN + ReLU
    dense(buf2, 512, w_dense1_fused, b_dense1_fused, buf1, 128);
    relu_inplace(buf1, 128);

    // Dense 2: 128→64 + BN + ReLU
    dense(buf1, 128, w_dense2_fused, b_dense2_fused, buf2, 64);
    relu_inplace(buf2, 64);

    // Dense 3: 64→6
    dense(buf2, 64, w_dense3, b_dense3, output, 6);

    // Softmax
    softmax(output, 6);

    free(buf1); free(buf2); free(buf3);
}
```

- [ ] **Step 2: 编译** — 确认用 MounRiver C 编译器能通过

---

### Task 9: PC 端逐层验证

**Files:**
- Create: `code/verify_layers.py`

- [ ] **Step 1: 逐层对比 MCU C 代码 vs TensorFlow TFLite**

用之前保存的 test_input.bin，跑每一层的 MCU C 代码（在 PC 上编译验证），和 TFLite 的中间层输出对比。如果每层误差 < 0.01，则推理引擎正确。

```python
# 用 ctypes 或 subprocess 调 C 代码，逐层验证
```

---

### Task 10: 集成到 DVP_UART 硬件

**Files:**
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/Common/hardware.c` — 在 FRM_DONE 中断后调用推理
- Modify: `CH32H417/sdk_ch32h417/DVP/DVP_UART/V5F/User/main.c` — 添加 `inference_init()` 调用
- 添加 `model_weights_6class.c` 到 V5F 编译列表

- [ ] **Step 1: 在 V5F Hardware() 中添加推理初始化**

在 `Hardware()` 函数起始处添加 `inference_init();`

- [ ] **Step 2: FRM_DONE 后推理**

在 FRM_DONE 的 UART 发送循环之后（V3F core），改为：裁剪图像区域 → 缩放到 32×32 → 拷贝到 V5F 共享内存 → HSEM 通知 V5F 推理 → V5F 推理完成后串口输出结果。

**简化版**：第一版在 V3F FRM_DONE 里直接调推理（因为 V3F 120MHz 也能跑，耗时 < 100ms）。后续优化再拆到 V5F。

- [ ] **Step 3: 编译 → 烧录 → 串口验证**

串口 921600 baud，预期输出类似：
```
V3F: SystemClk=400000000
JPEG Mode
=== Eye Tracking Inference ===
blind: 0.123456
center: 0.789012
down: 0.012345
left: 0.023456
right: 0.045678
up: 0.006789
Best: center (78.9%)
```

---

### Task 11: 最终验证与清理

- [ ] **Step 1: PC vs MCU 对比**

用同一张测试图片（训练集里的），PC TensorFlow 推理和 MCU 推理结果对比，6 个分类分数误差 < 0.01。

- [ ] **Step 2: 推理耗时测量**

在 `inference_run()` 前后加定时器，串口打印耗时。预期 < 200ms。

- [ ] **Step 3: 清理 TFLM 工程**

删除 `CH32H417/TFLM_EyeTracking/` 目录。
