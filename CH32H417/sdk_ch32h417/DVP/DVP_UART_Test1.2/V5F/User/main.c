#include "debug.h"
#include "test_image.h"
#include "jpeg_dec.h"

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

static void send_hex(UINT32 v) {
    const char hex[] = "0123456789ABCDEF";
    send_str("0x");
    for (int i = 28; i >= 0; i -= 4) {
        send_byte(hex[(v >> i) & 0xF]);
    }
}

int main(void)
{
    /* GPIO debug: blink PB4 to confirm V5F is running */
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOB, ENABLE);
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_4;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_High;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);

    /* Blink PB4 3 times */
    for (int i = 0; i < 6; i++) {
        GPIO_WriteBit(GPIOB, GPIO_Pin_4, (i % 2 == 0) ? Bit_SET : Bit_RESET);
        Delay_Ms(200);
    }

    send_str("V5F SystemCoreClk:");
    send_u32(SystemCoreClock);
    send_str("\r\n");

    Delay_Ms(500);

    send_str("Starting JPEG decode test...\r\n");
    send_str("JPEG data size:");
    send_u32(test_jpeg_size);
    send_str(" bytes\r\n");

    /* --- Diagnostic: timing --- */
    UINT32 t0 = SysTick1->CNT;
    jpeg_dec_init();
    int ret = jpeg_dec_decode(test_jpeg_data, test_jpeg_size);
    UINT32 t1 = SysTick1->CNT;
    UINT32 elapsed = (t1 >= t0) ? (t1 - t0) : (0xFFFFFFFF - t0 + t1);
    send_str("Decode time:");
    send_u32(elapsed);
    send_str(" ticks\r\n");

    /* --- Diagnostic: memory usage --- */
    extern UINT32 _sbss, _ebss;
    UINT32 bss_used = (UINT32)&_ebss - (UINT32)&_sbss;
    send_str("DTCM .bss used:");
    send_u32(bss_used);
    send_str(" bytes\r\n");
    send_str("jpeg_dec_buf @");
    send_hex((UINT32)jpeg_dec_buf);
    send_str("\r\n");

    /* --- Diagnostic: intermediate values --- */
    send_str("DIAG_START\r\n");
    send_str("COMP_DATA_328:");
    for (int i = 328; i < 344; i++) {
        send_hex(test_jpeg_data[i]);
        send_byte(' ');
    }
    send_str("\r\n");
    extern UINT8 jpeg_dec_bitstream[4];
    extern int jpeg_dec_block_bits[8];
    extern int jpeg_dec_dc_bits_arr[8];
    extern int jpeg_dec_ac_bits_arr[8];
    send_str("BITSTREAM:");
    for (int i = 0; i < 4; i++) {
        send_hex(jpeg_dec_bitstream[i]);
        send_byte(' ');
    }
    send_str("\r\n");
    send_str("BLOCK_BITS:");
    for (int i = 0; i < 8; i++) {
        send_u32(jpeg_dec_block_bits[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("DC_BITS:");
    for (int i = 0; i < 8; i++) {
        send_u32(jpeg_dec_dc_bits_arr[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("AC_BITS:");
    for (int i = 0; i < 8; i++) {
        send_u32(jpeg_dec_ac_bits_arr[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("W:");
    send_i32(jpeg_dec_width);
    send_str(" H:");
    send_i32(jpeg_dec_height);
    send_str(" NC:");
    send_i32(jpeg_dec_num_components);
    send_str(" Hmax:");
    send_i32(jpeg_dec_H_max);
    send_str(" Vmax:");
    send_i32(jpeg_dec_V_max);
    send_str("\r\n");
    for (int c = 0; c < jpeg_dec_num_components; c++) {
        send_str("COMP");
        send_u32(c);
        send_str(":h");
        send_u32(jpeg_dec_comp_h[c]);
        send_str("v");
        send_u32(jpeg_dec_comp_v[c]);
        send_str("\r\n");
    }
    extern UINT8 quant_table[2][64];
    send_str("QT0:");
    for (int i = 0; i < 64; i++) {
        send_u32(quant_table[0][i]);
        send_byte(',');
    }
    send_str("\r\n");
    extern UINT8 jpeg_dec_huff_dc_bits[2][17];
    extern UINT8 jpeg_dec_huff_ac_bits[2][17];
    extern int jpeg_dec_raw_dc[8];
    extern int jpeg_dec_debug_cat[8];
    extern int jpeg_dec_debug_val[8];
    send_str("RAW_DC:");
    for (int i = 0; i < 8; i++) {
        send_i32(jpeg_dec_raw_dc[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("DC_CAT:");
    for (int i = 0; i < 8; i++) {
        send_u32(jpeg_dec_debug_cat[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("DC_VAL:");
    for (int i = 0; i < 8; i++) {
        send_u32(jpeg_dec_debug_val[i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("ACBITS0:");
    for (int i = 1; i <= 16; i++) {
        send_u32(jpeg_dec_huff_ac_bits[0][i]);
        send_byte(',');
    }
    send_str("\r\n");
    send_str("RAW_DC:");
    for (int i = 0; i < 8; i++) {
        send_i32(jpeg_dec_raw_dc[i]);
        send_byte(',');
    }
    send_str("\r\n");
    if (jpeg_dec_width > 0 && jpeg_dec_height > 0) {
        send_str("DC_SAMPLE:");
        int max_samples = jpeg_dec_width * jpeg_dec_height / 64;
        if (max_samples > 8) max_samples = 8;
        for (int i = 0; i < max_samples; i++) {
            send_i32(jpeg_dec_buf[i * 64]);
            send_byte(',');
        }
        send_str("\r\n");
    }
    send_str("DIAG_END\r\n");

    if (ret == JPEG_DEC_OK) {
        send_str("Decode OK:");
        send_i32(jpeg_dec_width);
        send_byte('x');
        send_i32(jpeg_dec_height);
        send_str("\r\n");

        // Output first few pixels for alignment check
        send_str("PIXEL_CHECK:");
        for (int y = 0; y < 3; y++) {
            for (int x = 0; x < 10; x++) {
                send_u32(jpeg_dec_buf[y * jpeg_dec_width + x]);
                send_byte(',');
            }
        }
        send_str("\r\n");

        /* --- Send original JPEG for PC comparison --- */
        send_str("JPEG_START\r\n");
        send_bytes(test_jpeg_data, test_jpeg_size);
        send_str("\r\nJPEG_END\r\n");

        /* --- Send decoded pixels --- */
        send_str("PIXEL_START\r\n");
        int total = jpeg_dec_width * jpeg_dec_height;
        send_bytes(jpeg_dec_buf, total);
        send_str("\r\nPIXEL_END\r\n");

        send_str("Done\r\n");
    } else {
        send_str("Decode failed:");
        send_i32(ret);
        send_str("\r\n");
    }

    while(1) {
        Delay_Ms(1000);
    }
}
