#ifndef __INFERENCE_H__
#define __INFERENCE_H__

#include "ch32h417.h"

#define INF_INPUT_SIZE  (32 * 32 * 3)
#define INF_CONV_OUT_SIZE  (32 * 32 * 8)
#define INF_POOL_OUT_SIZE  (8 * 8 * 8)
#define INF_NUM_CLASSES  6

void inference_init(void);
void inference_run(const float *input, float *output);

#endif
