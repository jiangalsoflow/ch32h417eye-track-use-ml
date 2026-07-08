/*
 * Test4.3: DVP 接收验证 (V3F 处理 DVP)
 * 
 * 目标：验证 DVP 是否能正常接收 800x600 JPEG 数据
 * 
 * 修复：让 V3F 处理 DVP（像 Step1 一样），V5F 只等待
 */

#include "debug.h"

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

int main(void) {
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);
    
    send_str("\r\n========================================\r\n");
    send_str("Test4.3: V5F waiting (V3F handles DVP)\r\n");
    send_str("========================================\r\n");
    send_str("V5F SystemCoreClk:");
    send_u32(SystemCoreClock);
    send_str("\r\n\r\n");
    
    send_str("V5F: Waiting for V3F to handle DVP...\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
