#include "inference.h"
#include <math.h>

extern const float w_conv[216];
extern const float b_conv[8];
extern const float bn_gamma[8];
extern const float bn_beta[8];
extern const float bn_mean[8];
extern const float bn_var[8];
extern const float w_dense[3072];
extern const float b_dense[6];

static float w_fused[216];
static float b_fused[8];

#define CONV_BUF_ADDR  0x20103000
#define POOL_BUF_ADDR  0x2010B000

static float *conv_buf = (float *)CONV_BUF_ADDR;
static float *pool_buf = (float *)POOL_BUF_ADDR;

void inference_init(void) {
    for (int oc = 0; oc < 8; oc++) {
        float scale = bn_gamma[oc] / sqrtf(bn_var[oc] + 1e-3f);
        b_fused[oc] = (b_conv[oc] - bn_mean[oc]) * scale + bn_beta[oc];
        for (int ic = 0; ic < 3; ic++) {
            for (int ky = 0; ky < 3; ky++) {
                for (int kx = 0; kx < 3; kx++) {
                    int idx = oc * 27 + ic * 9 + ky * 3 + kx;
                    w_fused[idx] = w_conv[idx] * scale;
                }
            }
        }
    }
}

void inference_run(const float *input, float *output) {
    for (int oc = 0; oc < 8; oc++) {
        for (int y = 0; y < 32; y++) {
            for (int x = 0; x < 32; x++) {
                float sum = b_fused[oc];
                for (int ic = 0; ic < 3; ic++) {
                    for (int ky = 0; ky < 3; ky++) {
                        for (int kx = 0; kx < 3; kx++) {
                            int iy = y + ky - 1;
                            int ix = x + kx - 1;
                            if (iy >= 0 && iy < 32 && ix >= 0 && ix < 32) {
                                int in_idx = iy * 96 + ix * 3 + ic;
                                int w_idx = oc * 27 + ic * 9 + ky * 3 + kx;
                                sum += input[in_idx] * w_fused[w_idx];
                            }
                        }
                    }
                }
                sum = sum > 0.0f ? sum : 0.0f;
                conv_buf[oc * 1024 + y * 32 + x] = sum;
            }
        }
    }

    for (int py = 0; py < 8; py++) {
        for (int px = 0; px < 8; px++) {
            for (int oc = 0; oc < 8; oc++) {
                float max_val = -1e30f;
                for (int dy = 0; dy < 4; dy++) {
                    for (int dx = 0; dx < 4; dx++) {
                        int y = py * 4 + dy;
                        int x = px * 4 + dx;
                        float val = conv_buf[oc * 1024 + y * 32 + x];
                        if (val > max_val) max_val = val;
                    }
                }
                pool_buf[py * 64 + px * 8 + oc] = max_val;
            }
        }
    }

    for (int c = 0; c < 6; c++) {
        float sum = b_dense[c];
        for (int i = 0; i < 512; i++) {
            sum += pool_buf[i] * w_dense[c * 512 + i];
        }
        output[c] = sum;
    }

    float max_val = output[0];
    for (int i = 1; i < 6; i++) {
        if (output[i] > max_val) max_val = output[i];
    }
    float exp_sum = 0.0f;
    for (int i = 0; i < 6; i++) {
        output[i] = expf(output[i] - max_val);
        exp_sum += output[i];
    }
    for (int i = 0; i < 6; i++) {
        output[i] /= exp_sum;
    }
}
