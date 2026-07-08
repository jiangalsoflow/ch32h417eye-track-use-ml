/*
 * Test4.2: DVP 接收验证 (多帧诊断版)
 * 
 * 目标：验证 DVP 是否能正常接收 800x600 JPEG 数据
 * 
 * 测试流程：
 * 1. 初始化系统
 * 2. 初始化 OV2640 摄像头
 * 3. 初始化 DVP
 * 4. 接收多帧，跳过前 5 帧（OV2640 稳定）
 * 5. 验证第 6 帧的 JPEG 数据
 */

#include "debug.h"
#include "hardware.h"
#include "ov2640.h"

static void send_byte(UINT8 b) {
    while(USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
    USART_SendData(USART1, b);
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

static void send_hex(UINT32 v) {
    const char hex[] = "0123456789ABCDEF";
    send_str("0x");
    for (int i = 28; i >= 0; i -= 4) {
        send_byte(hex[(v >> i) & 0xF]);
    }
}

int main(void) {
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
    
    send_str("\r\n========================================\r\n");
    send_str("Test4.2: DVP Receive Validation (Multi-frame) v10\r\n");
    send_str("========================================\r\n");
    send_str("V5F SystemCoreClk:");
    send_u32(SystemCoreClock);
    send_str("\r\n\r\n");
    
    send_str("[DIAG] Step 1: Initializing OV2640 camera...\r\n");
    Hardware();
    send_str("[DIAG] Step 2: Camera initialized\r\n");
    
    // 读取 OV2640 寄存器验证配置
    send_str("[DIAG] Reading OV2640 registers...\r\n");
    // 读取 PID/MID
    UINT8 mid_h = SCCB_RD_Reg(0x1C);
    UINT8 mid_l = SCCB_RD_Reg(0x1D);
    UINT8 pid_h = SCCB_RD_Reg(0x0A);
    UINT8 pid_l = SCCB_RD_Reg(0x0B);
    send_str("[DIAG] MID: ");
    send_hex((mid_h << 8) | mid_l);
    send_str(", PID: ");
    send_hex((pid_h << 8) | pid_l);
    send_str("\r\n");
    
    // 读取输出尺寸寄存器 (bank 00)
    SCCB_WR_Reg(0xFF, 0x00);  // 切换到 DSP bank
    UINT8 zmow = SCCB_RD_Reg(0x5A);  // OUTW[7:0] = width/4
    UINT8 zmoh = SCCB_RD_Reg(0x5B);  // OUTH[7:0] = height/4
    UINT8 zmhh = SCCB_RD_Reg(0x5C);  // OUTH[8], OUTW[9:8]
    UINT16 out_w = ((zmhh & 0x03) << 8) | zmow;
    UINT16 out_h = ((zmhh >> 2) & 0x01) << 8 | zmoh;
    out_w *= 4;
    out_h *= 4;
    send_str("[DIAG] ZMOW=");
    send_hex(zmow);
    send_str(", ZMOH=");
    send_hex(zmoh);
    send_str(", ZMHH=");
    send_hex(zmhh);
    send_str("\r\n");
    send_str("[DIAG] Output size: ");
    send_u32(out_w);
    send_str("x");
    send_u32(out_h);
    send_str("\r\n");
    
    // 读取 IMAGE_MODE (bank 00, 0xDA)
    UINT8 image_mode = SCCB_RD_Reg(0xDA);
    send_str("[DIAG] IMAGE_MODE=");
    send_hex(image_mode);
    if (image_mode & 0x10) {
        send_str(" (JPEG enabled)\r\n");
    } else {
        send_str(" (JPEG DISABLED!)\r\n");
    }
    
    // 读取 COM7 (bank 01, 0x12) - 分辨率模式
    SCCB_WR_Reg(0xFF, 0x01);  // 切换到 sensor bank
    UINT8 com7 = SCCB_RD_Reg(0x12);
    send_str("[DIAG] COM7=");
    send_hex(com7);
    UINT8 res_mode = (com7 >> 4) & 0x07;
    send_str(" (resolution: ");
    if (res_mode == 0) send_str("UXGA");
    else if (res_mode == 2) send_str("CIF");
    else if (res_mode == 4) send_str("SVGA");
    else send_str("unknown");
    send_str(")\r\n");
    
    send_str("[DIAG] Step 3: DVP initialized\r\n");
    
    #define SKIP_FRAMES 10
    #define TOTAL_FRAMES 15
    
    send_str("[DIAG] Step 4: Capturing ");
    send_u32(TOTAL_FRAMES);
    send_str(" frames (skip first ");
    send_u32(SKIP_FRAMES);
    send_str(" for stabilization)...\r\n\r\n");
    
    UINT32 timeout = 0;
    UINT32 max_timeout = 30000;
    
    for (int frame_idx = 0; frame_idx < TOTAL_FRAMES; frame_idx++) {
        timeout = 0;
        while (!frame_ready && timeout < max_timeout) {
            Delay_Ms(1);
            timeout++;
        }
        
        if (timeout >= max_timeout) {
            send_str("[DIAG] TIMEOUT at frame ");
            send_u32(frame_idx);
            send_str("\r\n");
            send_str("*** TEST FAILED: TIMEOUT ***\r\n");
            while(1) { Delay_Ms(1000); }
        }
        
        send_str("[FRAME ");
        send_u32(frame_idx);
        send_str("] jpeg_size=");
        send_u32(jpeg_size);
        send_str(" bytes, href_cnt=");
        send_u32(jpeg_size / 800);  // 从 jpeg_size 反推行数
        send_str(", frame_cnt=");
        send_u32(frame_cnt);
        
        if (frame_idx < SKIP_FRAMES) {
            send_str(" (skip)\r\n");
        } else {
            send_str("\r\n");
        }
        
        if (frame_idx < TOTAL_FRAMES - 1) {
            dvp_restart();
        }
    }
    
    send_str("\r\n[DIAG] Step 5: Validating last frame...\r\n");
    
    UINT8 *jpeg_buf = (UINT8 *)0x20140000;
    
    UINT8 soi_0 = jpeg_buf[0];
    UINT8 soi_1 = jpeg_buf[1];
    send_str("[DIAG] SOI marker: ");
    send_hex(soi_0);
    send_str(" ");
    send_hex(soi_1);
    if (soi_0 == 0xFF && soi_1 == 0xD8) {
        send_str(" (VALID)\r\n");
    } else {
        send_str(" (INVALID)\r\n");
    }
    
    UINT8 eoi_0 = jpeg_buf[jpeg_size - 2];
    UINT8 eoi_1 = jpeg_buf[jpeg_size - 1];
    send_str("[DIAG] EOI marker: ");
    send_hex(eoi_0);
    send_str(" ");
    send_hex(eoi_1);
    if (eoi_0 == 0xFF && eoi_1 == 0xD9) {
        send_str(" (VALID)\r\n");
    } else {
        send_str(" (INVALID)\r\n");
    }
    
    send_str("\r\n[DIAG] First 32 bytes:\r\n");
    for (int i = 0; i < 32; i++) {
        send_hex(jpeg_buf[i]);
        send_str(" ");
        if ((i + 1) % 16 == 0) send_str("\r\n");
    }
    
    send_str("\r\n[DIAG] Last 32 bytes:\r\n");
    for (int i = jpeg_size - 32; i < jpeg_size; i++) {
        send_hex(jpeg_buf[i]);
        send_str(" ");
        if ((i + 1) % 16 == 0) send_str("\r\n");
    }
    
    send_str("\r\n========================================\r\n");
    send_str("Summary:\r\n");
    send_str("========================================\r\n");
    
    int soi_valid = (soi_0 == 0xFF && soi_1 == 0xD8);
    int eoi_valid = (eoi_0 == 0xFF && eoi_1 == 0xD9);
    
    if (soi_valid && eoi_valid) {
        send_str("*** ALL TESTS PASSED ***\r\n");
        send_str("DVP receive is working correctly!\r\n");
    } else {
        send_str("*** TEST FAILED ***\r\n");
        if (!soi_valid) send_str("- SOI marker invalid\r\n");
        if (!eoi_valid) send_str("- EOI marker invalid\r\n");
    }
    
    send_str("\r\nTest completed.\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
