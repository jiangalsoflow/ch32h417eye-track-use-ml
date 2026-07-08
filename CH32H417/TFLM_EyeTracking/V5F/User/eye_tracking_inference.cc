#include "eye_tracking_inference.h"
#include "debug.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "eye_tracking_model_data.h"

static const char* kClassNames[] = {"blind", "center", "down", "left", "right", "up"};

void EyeTrackingInference(void)
{
  MicroPrintf("\r\n=== Eye Tracking TFLM ===");
  tflite::InitializeTarget();

  /* Load model */
  const tflite::Model* model = ::tflite::GetModel(g_eye_tracking_model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    MicroPrintf("FATAL: schema mismatch (model=%d tflm=%d)",
                model->version(), TFLITE_SCHEMA_VERSION);
    while(1) { Delay_Ms(1000); }
  }
  MicroPrintf("Model: %d bytes OK", g_eye_tracking_model_data_size);

  /* Register ops */
  static tflite::MicroMutableOpResolver<5> op_resolver;
  op_resolver.AddConv2D();
  op_resolver.AddMaxPool2D();
  op_resolver.AddReshape();
  op_resolver.AddFullyConnected();
  op_resolver.AddSoftmax();
  MicroPrintf("Ops OK");

  /* Allocate tensors */
  constexpr int kArenaSize = 120 * 1024;
  static uint8_t arena[kArenaSize] __attribute__((section(".bss")));
  static tflite::MicroInterpreter interpreter(model, op_resolver, arena, kArenaSize);
  if (interpreter.AllocateTensors() != kTfLiteOk) {
    MicroPrintf("FATAL: AllocTensors failed (arena=%dKB)", kArenaSize / 1024);
    while(1) { Delay_Ms(1000); }
  }

  TfLiteTensor* input  = interpreter.input(0);
  TfLiteTensor* output = interpreter.output(0);
  MicroPrintf("In: %dx%dx%dx%d %s %dB  Out: %dx%d %dB",
              input->dims->data[0], input->dims->data[1],
              input->dims->data[2], input->dims->data[3],
              input->type == kTfLiteFloat32 ? "f32" : "??", input->bytes,
              output->dims->data[0], output->dims->data[1], output->bytes);

  /* Fill input with 0.5 (mid-gray) and run inference */
  int n = input->bytes / sizeof(float);
  for (int i = 0; i < n; i++) input->data.f[i] = 0.5f;

  if (interpreter.Invoke() != kTfLiteOk) {
    MicroPrintf("FATAL: Invoke failed");
    while(1) { Delay_Ms(1000); }
  }

  int best = 0;
  float bestVal = output->data.f[0];
  MicroPrintf("=== Results ===");
  for (int i = 0; i < 6; i++) {
    float s = output->data.f[i];
    MicroPrintf("  %-6s: %+.4f", kClassNames[i], s);
    if (s > bestVal) { bestVal = s; best = i; }
  }
  MicroPrintf("Best: %s (%.1f%%)", kClassNames[best], bestVal * 100.0f);
  MicroPrintf("=== PASSED ===");
}
