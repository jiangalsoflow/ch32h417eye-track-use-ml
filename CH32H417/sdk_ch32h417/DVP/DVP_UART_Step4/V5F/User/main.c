#include "debug.h"
#include "hardware.h"
#include "jpeg_dec.h"
#include "inference.h"

#define JPEG_BUF_ADDR   0x20140000
#define INPUT_BUF_ADDR  0x20100000

static float *input_buf = (float *)INPUT_BUF_ADDR;

static void send_byte(UINT8 b) {
    while(USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
    USART_SendData(USART1, b);
}

static void send_bytes(const UINT8 *buf, UINT32 len) {
    for (UINT32 i = 0; i < len; i++) {
        send_byte(buf[i]);
    }
}

static void send_str(const char *s) {
    while (*s) {
        send_byte(*s++);
    }
}

static void send_u32(UINT32 v) {
    char buf[12];
    int i = 0;
    if (v == 0) {
        send_byte('0');
        return;
    }
    while (v > 0) {
        buf[i++] = '0' + (v % 10);
        v /= 10;
    }
    while (i > 0) {
        send_byte(buf[--i]);
    }
}

static void send_i32(INT32 v) {
    if (v < 0) {
        send_byte('-');
        v = -v;
    }
    send_u32((UINT32)v);
}

static void send_score(float val) {
    UINT32 score_int = (UINT32)(val * 10000);
    send_u32(score_int / 10000);
    send_byte('.');
    UINT32 frac = score_int % 10000;
    if (frac < 1000) send_byte('0');
    if (frac < 100) send_byte('0');
    if (frac < 10) send_byte('0');
    send_u32(frac);
}

int main(void)
{
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOB, ENABLE);
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_4;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_High;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);

    for (int i = 0; i < 6; i++) {
        GPIO_WriteBit(GPIOB, GPIO_Pin_4, (i % 2 == 0) ? Bit_SET : Bit_RESET);
        Delay_Ms(200);
    }

    send_str("V5F SystemCoreClk:");
    send_u32(SystemCoreClock);
    send_str("\r\n");

    inference_init();
    send_str("Inference init done\r\n");

    jpeg_dec_init();
    send_str("JPEG decoder init done\r\n");

    Delay_Ms(500);

    Hardware();

    send_str("FW: STEP4 v1\r\n");
    send_str("Waiting for frames...\r\n");

    UINT8 *jpeg_buf = (UINT8 *)JPEG_BUF_ADDR;
    static const char *class_names[] = {"blind", "center", "down", "left", "right", "up"};
    static float output[6];
    UINT32 frame_num = 0;

    while(1) {
        if (!frame_ready) continue;

        UINT32 t0 = SysTick1->CNT;

        UINT32 cur_jpeg_size = jpeg_size;

        int ret = jpeg_dec_decode(jpeg_buf, cur_jpeg_size);
        UINT32 t1 = SysTick1->CNT;
        UINT32 decode_time = (t1 >= t0) ? (t1 - t0) : (0xFFFFFFFF - t0 + t1);

        send_str("FRAME_START\r\n");
        send_str("FRAME_NUM:");
        send_u32(frame_num);
        send_str("\r\n");
        send_str("JPEG_SIZE:");
        send_u32(cur_jpeg_size);
        send_str("\r\n");

        if (ret == JPEG_DEC_OK) {
            int src_w = jpeg_dec_width;
            int src_h = jpeg_dec_height;

            send_str("DECODE_OK:");
            send_i32(src_w);
            send_byte('x');
            send_i32(src_h);
            send_str("\r\n");
            send_str("Decode time:");
            send_u32(decode_time);
            send_str(" ticks\r\n");

            // Preprocessing pipeline to match training: flip → crop → resize
            // Training parameters from pc_infer.py
            #define EYE_CX 412
            #define EYE_CY 312
            #define CROP_SZ 40
            #define INPUT_SZ 32
            
            int half = CROP_SZ / 2;
            int x1 = EYE_CX - half;  // 392
            int y1 = EYE_CY - half;  // 292
            int x2 = EYE_CX + half;  // 432
            int y2 = EYE_CY + half;  // 332
            
            // Step 1: Horizontal flip + crop + resize (bilinear interpolation)
            // We combine all operations to avoid intermediate buffers
            for (int dst_y = 0; dst_y < INPUT_SZ; dst_y++) {
                for (int dst_x = 0; dst_x < INPUT_SZ; dst_x++) {
                    // Map destination pixel to source crop coordinates
                    float src_x_f = (dst_x + 0.5f) * CROP_SZ / INPUT_SZ - 0.5f;
                    float src_y_f = (dst_y + 0.5f) * CROP_SZ / INPUT_SZ - 0.5f;
                    
                    // Clamp to crop bounds
                    if (src_x_f < 0) src_x_f = 0;
                    if (src_y_f < 0) src_y_f = 0;
                    if (src_x_f >= CROP_SZ - 1) src_x_f = CROP_SZ - 1 - 0.001f;
                    if (src_y_f >= CROP_SZ - 1) src_y_f = CROP_SZ - 1 - 0.001f;
                    
                    int x0 = (int)src_x_f;
                    int y0 = (int)src_y_f;
                    int x1_crop = x0 + 1;
                    int y1_crop = y0 + 1;
                    
                    float wx = src_x_f - x0;
                    float wy = src_y_f - y0;
                    
                    // Get crop pixel coordinates (before flip)
                    int crop_x0 = x1 + x0;
                    int crop_y0 = y1 + y0;
                    int crop_x1 = x1 + x1_crop;
                    int crop_y1 = y1 + y1_crop;
                    
                    // Apply horizontal flip: flip_x = (src_w - 1) - x
                    int flip_x0 = (src_w - 1) - crop_x0;
                    int flip_x1 = (src_w - 1) - crop_x1;
                    
                    // Bilinear interpolation
                    float v00 = jpeg_dec_buf[crop_y0 * src_w + flip_x0];
                    float v01 = jpeg_dec_buf[crop_y0 * src_w + flip_x1];
                    float v10 = jpeg_dec_buf[crop_y1 * src_w + flip_x0];
                    float v11 = jpeg_dec_buf[crop_y1 * src_w + flip_x1];
                    
                    float val = (1-wx)*(1-wy)*v00 + wx*(1-wy)*v01 + 
                                (1-wx)*wy*v10 + wx*wy*v11;
                    
                    // Normalize to [0,1] and replicate to 3 channels
                    val = val / 255.0f;
                    int idx = (dst_y * INPUT_SZ + dst_x) * 3;
                    input_buf[idx + 0] = val;
                    input_buf[idx + 1] = val;
                    input_buf[idx + 2] = val;
                }
            }

            UINT32 t2 = SysTick1->CNT;
            inference_run(input_buf, output);
            UINT32 t3 = SysTick1->CNT;
            UINT32 infer_time = (t3 >= t2) ? (t3 - t2) : (0xFFFFFFFF - t2 + t3);

            int best_idx = 0;
            for (int i = 1; i < 6; i++) {
                if (output[i] > output[best_idx]) best_idx = i;
            }

            send_str("CLASS:");
            send_str(class_names[best_idx]);
            send_str("\r\n");
            send_str("SCORES:");
            for (int i = 0; i < 6; i++) {
                send_str(" ");
                send_str(class_names[i]);
                send_byte('=');
                send_score(output[i]);
            }
            send_str("\r\n");
            send_str("Infer time:");
            send_u32(infer_time);
            send_str(" ticks\r\n");

            send_str("JPEG_START\r\n");
            send_bytes(jpeg_buf, cur_jpeg_size);
            send_str("\r\nJPEG_END\r\n");
        } else {
            send_str("DECODE_FAIL:");
            send_i32(ret);
            send_str("\r\n");
        }

        send_str("FRAME_END\r\n");

        frame_num++;
        dvp_restart();
    }
}
