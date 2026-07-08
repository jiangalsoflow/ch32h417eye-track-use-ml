# TFLM 眼动推理引擎 — 实现计划

> **For agentic workers:** Use `superpowers:subagent-driven-development` to implement this plan task-by-task.

**Goal:** 将 eye_tracking_float32.tflite 集成到 CH32H417 TFLM 项目，V5F 独立跑通静态图像推理

**Architecture:** 拷贝 TFLM 项目 → 修复路径 → 建 V3F 空壳 → 替换模型 + 算子 → 生成测试输入 → 编译烧录验证

**Tech Stack:** MounRiver Studio 2, RISC-V GCC12, TensorFlow Lite Micro（float32）

---

### Task 1: 拷贝 TFLM 项目到工作目录

**Files:**
- Copy: `D:\QQ\download\TFLM_TinyML_CH32H417-main\TFLM_TinyML_CH32H417-main\**` → `C:\Users\13228\Desktop\Match\CH32H417\TFLM_EyeTracking\`

- [ ] **Step 1: 拷贝整个 TFLM 项目**

```bash
cp -r "D:/QQ/download/TFLM_TinyML_CH32H417-main/TFLM_TinyML_CH32H417-main" "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking"
```

- [ ] **Step 2: 把已生成的模型 C 文件也拷进去**

```bash
cp "D:/QQ/download/TFLM_TinyML_CH32H417-main/TFLM_TinyML_CH32H417-main/User/tflm/eye_tracking_model_data.cc" "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/User/tflm/"
cp "D:/QQ/download/TFLM_TinyML_CH32H417-main/TFLM_TinyML_CH32H417-main/User/tflm/eye_tracking_model_data.h" "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/User/tflm/"
```

---

### Task 2: 新建 V3F 空壳工程（双核启动需要）

**Files:**
- Create: `CH32H417/TFLM_EyeTracking/V3F/.cproject`
- Create: `CH32H417/TFLM_EyeTracking/V3F/.kernel`
- Create: `CH32H417/TFLM_EyeTracking/V3F/.project`
- Create: `CH32H417/TFLM_EyeTracking/V3F/.template`
- Create: `CH32H417/TFLM_EyeTracking/V3F/CH32H417_TFLM_V3F.wvproj`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/main.c`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/system_ch32h417.c`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/system_ch32h417.h`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/ch32h417_it.c`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/ch32h417_it.h`
- Create: `CH32H417/TFLM_EyeTracking/V3F/User/ch32h417_conf.h`

- [ ] **Step 1: 从 EVT DVP_UART 拷贝 V3F 工程文件作为模板**

```bash
cp -r "c:/Users/13228/Desktop/Match/EVT/EXAM/DVP/DVP_UART/V3F" "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V3F"
```

- [ ] **Step 2: 精简 V3F main.c — 只负责唤醒 V5F 然后休眠**

修改 `CH32H417/TFLM_EyeTracking/V3F/User/main.c` 为：

```c
#include "debug.h"

int main(void)
{
    SystemInit();
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(921600);
    Delay_Ms(1000);
    printf("V3F: waking V5F...\r\n");

    RCC_HB1PeriphClockCmd(RCC_HB1Periph_PWR, ENABLE);
    PWR_VIO18ModeCfg(PWR_VIO18CFGMODE_SW);
    PWR_VIO18LevelCfg(PWR_VIO18Level_MODE3);

    NVIC_WakeUp_V5F(Core_V5F_StartAddr);
    HSEM_ITConfig(HSEM_ID0, ENABLE);
    PWR_EnterSTOPMode(PWR_Regulator_ON, PWR_STOPEntry_WFE);
    HSEM_ClearFlag(HSEM_ID0);
    printf("V3F: woke up\r\n");

    while(1)
    {
        printf("V3F idle...\r\n");
        Delay_Ms(5000);
    }
}
```

- [ ] **Step 3: 精简 ch32h417_it.c — 只保留 HSEM 中断**

```c
#include "ch32h417_it.h"

void NMI_Handler(void) {}
void HardFault_Handler(void) { while(1); }

void HSEM_IRQHandler(void)
{
    if(HSEM_GetITStatus(HSEM_IT_ID0) != RESET)
    {
        HSEM_ClearITPendingBit(HSEM_IT_ID0);
    }
}
```

- [ ] **Step 4: 复制链接脚本**

```bash
mkdir -p "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V3F/Ld"
cp "c:/Users/13228/Desktop/Match/EVT/EXAM/DVP/DVP_UART/Common/Ld/V3F/Link_v3f.ld" "c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/V3F/Ld/"
```

---

### Task 3: 修复 TFLM 项目的路径配置

**Files:**
- Modify: `CH32H417/TFLM_EyeTracking/.mrs/launch.json` — 更新路径

- [ ] **Step 1: 更新 launch.json 中的路径**

把 `e:\WCH\03_Project\...` 改成实际路径 `C:\Users\13228\Desktop\Match\CH32H417\TFLM_EyeTracking\V5F\obj\CH32H417_TFLM_V5F.elf`

```json
"executableFile": "C:\\Users\\13228\\Desktop\\Match\\CH32H417\\TFLM_EyeTracking\\V5F\\obj\\CH32H417_TFLM_V5F.elf",
"symbolFile": "C:\\Users\\13228\\Desktop\\Match\\CH32H417\\TFLM_EyeTracking\\V5F\\obj\\CH32H417_TFLM_V5F.elf",
```

---

### Task 4: 修改 person_detection_test.cc → eye_tracking_test.cc

**Files:**
- Create: `CH32H417/TFLM_EyeTracking/User/tflm/eye_tracking_test.cc`
- Modify: `CH32H417/TFLM_EyeTracking/User/tflm/eye_tracking_test.cc`

- [ ] **Step 1: 编写眼动推理测试代码**

关键改动：
1. `#include` 换成 `eye_tracking_model_data.h`
2. OpResolver 改为：`Conv2D, MaxPool2D, Reshape, FullyConnected, Softmax`
3. 输入尺寸：`32×32×3 float32` (12,288 bytes)
4. 输出尺寸：`1×6 float32`
5. Tensor Arena: 120KB
6. 用 g_eye_tracking_model_data 替代 g_person_detect_model_data

完整代码：

```cpp
#include "debug.h"
#include "tensorflow/lite/core/c/common.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "eye_tracking_model_data.h"
#include <string.h>
#include <math.h>

namespace {
using EyeTrackOpResolver = tflite::MicroMutableOpResolver<5>;

constexpr int kTensorArenaSize = 120 * 1024;
uint8_t tensor_arena[kTensorArenaSize] __attribute__((section(".bss")));

TfLiteStatus RegisterOps(EyeTrackOpResolver& op_resolver) {
  TF_LITE_ENSURE_STATUS(op_resolver.AddConv2D());
  TF_LITE_ENSURE_STATUS(op_resolver.AddMaxPool2D());
  TF_LITE_ENSURE_STATUS(op_resolver.AddReshape());
  TF_LITE_ENSURE_STATUS(op_resolver.AddFullyConnected());
  TF_LITE_ENSURE_STATUS(op_resolver.AddSoftmax());
  return kTfLiteOk;
}
}

// 6 classes: blind=0, center=1, down=2, left=3, right=4, up=5
const char* class_names[] = {"blind", "center", "down", "left", "right", "up"};

int main(int argc, char* argv[]) {
  SystemAndCoreClockUpdate();
  Delay_Init();
  USART_Printf_Init(115200);

  MicroPrintf("=== Eye Tracking TFLM Test ===");
  Delay_Ms(500);

  tflite::InitializeTarget();

  const tflite::Model* model = ::tflite::GetModel(g_eye_tracking_model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    MicroPrintf("ERROR: Model schema mismatch!");
    MicroPrintf("  Model: %d, TFLM: %d", model->version(), TFLITE_SCHEMA_VERSION);
    while(1) { Delay_Ms(1000); }
  }
  MicroPrintf("Model loaded OK (%d bytes)", g_eye_tracking_model_data_size);

  static EyeTrackOpResolver op_resolver;
  if (RegisterOps(op_resolver) != kTfLiteOk) {
    MicroPrintf("ERROR: Op registration failed!");
    while(1) { Delay_Ms(1000); }
  }
  MicroPrintf("Ops registered OK");

  static tflite::MicroInterpreter interpreter(model, op_resolver, tensor_arena, kTensorArenaSize);
  if (interpreter.AllocateTensors() != kTfLiteOk) {
    MicroPrintf("ERROR: AllocateTensors failed! Arena too small?");
    while(1) { Delay_Ms(1000); }
  }
  MicroPrintf("Tensors allocated OK");

  TfLiteTensor* input = interpreter.input(0);
  TfLiteTensor* output = interpreter.output(0);

  MicroPrintf("Input: %d x %d x %d x %d (%d bytes, %s)",
              input->dims->data[0], input->dims->data[1],
              input->dims->data[2], input->dims->data[3],
              input->bytes,
              input->type == kTfLiteFloat32 ? "float32" : "other");
  MicroPrintf("Output: %d x %d (%d bytes)",
              output->dims->data[0], output->dims->data[1],
              output->bytes);

  // Fill input with test pattern (mid-gray = 0.5)
  for (int i = 0; i < input->bytes / 4; i++) {
    input->data.f[i] = 0.5f;
  }
  MicroPrintf("Input filled with 0.5 (test pattern)");

  // Run inference
  uint32_t start = SysTick->CNT;
  TfLiteStatus status = interpreter.Invoke();
  uint32_t elapsed = SysTick->CNT - start;

  if (status != kTfLiteOk) {
    MicroPrintf("ERROR: Invoke failed!");
    while(1) { Delay_Ms(1000); }
  }

  // Read output
  MicroPrintf("=== Inference Result ===");
  int best_class = 0;
  float best_score = output->data.f[0];
  for (int i = 0; i < 6; i++) {
    float score = output->data.f[i];
    MicroPrintf("  %s: %.4f", class_names[i], score);
    if (score > best_score) {
      best_score = score;
      best_class = i;
    }
  }
  MicroPrintf("Best: %s (%.4f)", class_names[best_class], best_score);
  MicroPrintf("Inference time: %d ms", elapsed / (SystemCoreClock / 1000));
  MicroPrintf("=== TEST PASSED ===");

  while(1) {
    Delay_Ms(5000);
    MicroPrintf("TFLM eye tracking ready.");
  }
}
```

- [ ] **Step 2: 排除 person_detection 测试文件编译**

在 MounRiver 中：右键 `person_detection_test.cc` → Exclude from build

- [ ] **Step 3: 添加 eye_tracking_model_data.cc 到编译**

在 MounRiver 中：右键 `eye_tracking_model_data.cc` → 确保勾选 Include in build

---

### Task 5: 生成真实测试输入

**Files:**
- Create: `CH32H417/TFLM_EyeTracking/User/tflm/test_eye_data.cc`（可选，先不集成）

先用灰度测试跑通（Task 4 的 0.5 填充），验证推理管线正常后，再生成真实测试数据。

- [ ] **Step 1: 从训练集导出测试图像为 float32 C 数组**

```bash
python -c "
import cv2, numpy as np, os

# Load a test image from training set
test_dir = 'D:/AI Module/Eye_Tracking/dataset/test/center'
imgs = [f for f in os.listdir(test_dir) if f.endswith('.jpg')]
if imgs:
    img = cv2.imread(os.path.join(test_dir, imgs[0]))
    img = cv2.resize(img, (32, 32))
    img = img.astype(np.float32) / 255.0
    # NHWC format
    data = img.flatten()
    print(f'Image: {imgs[0]}, shape: {img.shape}, range: [{data.min():.3f}, {data.max():.3f}]')
    # Generate C array header
    with open('c:/Users/13228/Desktop/Match/CH32H417/TFLM_EyeTracking/User/tflm/test_center_data.h', 'w') as f:
        f.write(f'// Test image: center class, {img.shape}\n')
        f.write(f'const float g_test_center_data[{len(data)}] = {{\n')
        for i in range(0, len(data), 8):
            chunk = data[i:i+8]
            f.write('  ' + ', '.join(f'{v:.6f}f' for v in chunk) + ',\n')
        f.write('};\n')
    print(f'Generated test data ({len(data)} floats)')
"
```

---

### Task 6: 编译、烧录、验证

- [ ] **Step 1: 编译 V3F**
在 MounRiver 打开 V3F 项目 → Clean → Build

- [ ] **Step 2: 编译 V5F**
在 MounRiver 打开 V5F 项目 → Clean → Build → 确认生成 Merge.bin

- [ ] **Step 3: 烧录**
用 WCH-Link 烧录 Merge.bin，先断电再上电

- [ ] **Step 4: 验证串口输出**
打开串口助手 115200 baud，预期输出：
```
V3F: waking V5F...
=== Eye Tracking TFLM Test ===
Model loaded OK (95384 bytes)
Ops registered OK
Tensors allocated OK
Input: 1 x 32 x 32 x 3 (12288 bytes, float32)
Output: 1 x 6 (24 bytes)
=== Inference Result ===
  blind: x.xxxx
  center: x.xxxx
  ...
Inference time: XX ms
=== TEST PASSED ===
```

- [ ] **Step 5: 成功标准**
- [x] 无 Model schema mismatch 错误
- [x] 无 AllocateTensors failed 错误
- [x] 无 Invoke failed 错误
- [x] 6 个分类分数正常输出
- [x] 推理时间 < 200ms

---

### Task 7: 生成对比验证

- [ ] **Step 1: PC 端用同一输入跑 Python TFLite 推理**

```bash
python -c "
import tensorflow as tf, numpy as np

# Load model
interpreter = tf.lite.Interpreter(model_path='D:/AI Module/Eye_Tracking/models/eye_tracking_float32.tflite')
interpreter.allocate_tensors()
input_data = np.full((1, 32, 32, 3), 0.5, dtype=np.float32)
interpreter.set_tensor(interpreter.get_input_details()[0]['index'], input_data)
interpreter.invoke()
output = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])
labels = ['blind', 'center', 'down', 'left', 'right', 'up']
for name, val in zip(labels, output[0]):
    print(f'  {name}: {val:.4f}')
"
```

- [ ] **Step 2: 对比 MCU 和 PC 输出**
期望：两组分数一致（容差 < 0.001），确认为同一模型

---

### Task 8: 提交

- [ ] **Step 1: Git add + commit**

```bash
cd c:/Users/13228/Desktop/Match
git add CH32H417/TFLM_EyeTracking/
git commit -m "feat: add TFLM eye tracking inference project (V5F float32)"
```
