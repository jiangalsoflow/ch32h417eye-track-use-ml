#include "debug.h"
#include "hardware.h"
#include "jpeg_dec.h"
#include "inference.h"

#define JPEG_BUF_ADDR   0x20160000
#define INPUT_BUF_ADDR  0x20120000
#define CROP_CX         170
#define CROP_CY         110
#define CROP_SZ         40
#define CROP_SCALE_Q8   ((CROP_SZ * 256) / 32)
#define CROP_HALF_Q8    ((CROP_SCALE_Q8 - 256) / 2)
#define CROP_MAX_MIR_Q8 ((CROP_SZ - 1) * 256)

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

    send_str("FW: STEP4_FAST v1\r\n");
    send_str("Waiting for frames...\r\n");

    UINT8 *jpeg_buf = (UINT8 *)JPEG_BUF_ADDR;
    static const char *class_names[] = {"blind", "center", "down", "left", "right", "up"};
    static float output[6];
    UINT32 frame_num = 0;

    int crop_x1 = CROP_CX - CROP_SZ / 2;
    int crop_y1 = CROP_CY - CROP_SZ / 2;

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

            #define CROP_SCALE_Q8    ((CROP_SZ * 256) / 32)
            #define CROP_HALF_Q8     ((CROP_SCALE_Q8 - 256) / 2)
            #define CROP_MAX_MIR_Q8  ((CROP_SZ - 1) * 256)

            for (int y = 0; y < 32; y++) {
                int cy_q8 = CROP_HALF_Q8 + y * CROP_SCALE_Q8;
                int oy_q8 = crop_y1 * 256 + cy_q8;
                int y0 = oy_q8 >> 8;
                int wy = oy_q8 & 0xFF;
                int y1 = y0 + 1;
                if (y1 >= src_h) y1 = src_h - 1;

                for (int x = 0; x < 32; x++) {
                    int cx_q8 = CROP_HALF_Q8 + x * CROP_SCALE_Q8;
                    int mx_q8 = CROP_MAX_MIR_Q8 - cx_q8;
                    int ox_q8 = crop_x1 * 256 + mx_q8;
                    int x0 = ox_q8 >> 8;
                    int wx = ox_q8 & 0xFF;
                    int x1 = x0 + 1;
                    if (x1 >= src_w) x1 = src_w - 1;

                    int tl = jpeg_dec_buf[y0 * src_w + x0];
                    int tr = jpeg_dec_buf[y0 * src_w + x1];
                    int bl = jpeg_dec_buf[y1 * src_w + x0];
                    int br = jpeg_dec_buf[y1 * src_w + x1];

                    int top = tl * (256 - wx) + tr * wx;
                    int bot = bl * (256 - wx) + br * wx;
                    int pixel = (top * (256 - wy) + bot * wy) >> 16;

                    float val = (float)pixel / 255.0f;
                    int idx = (y * 32 + x) * 3;
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
