#include "debug.h"
#include "hardware.h"
#include "jpeg_dec.h"
#include "inference.h"

#define JPEG_BUF_ADDR   0x20160000
#define INPUT_BUF_ADDR  0x20120000

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

    send_str("FW: STEP3 v1\r\n");
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

            for (int y = 0; y < 32; y++) {
                for (int x = 0; x < 32; x++) {
                    int src_x = x * src_w / 32;
                    int src_y = y * src_h / 32;
                    if (src_x >= src_w) src_x = src_w - 1;
                    if (src_y >= src_h) src_y = src_h - 1;
                    float val = jpeg_dec_buf[src_y * src_w + src_x] / 255.0f;
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
