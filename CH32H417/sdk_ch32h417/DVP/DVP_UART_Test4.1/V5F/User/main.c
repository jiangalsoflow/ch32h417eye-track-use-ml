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

static void send_hex(UINT32 v) {
    const char hex[] = "0123456789ABCDEF";
    send_str("0x");
    for (int i = 28; i >= 0; i -= 4) {
        send_byte(hex[(v >> i) & 0xF]);
    }
}

// 测试单个内存区域
// 返回 0 表示成功，非 0 表示失败
static int test_memory_region(UINT32 addr, UINT32 size, const char *name) {
    volatile UINT8 *ptr = (volatile UINT8 *)addr;
    UINT8 patterns[] = {0x00, 0xFF, 0x55, 0xAA};
    int num_patterns = sizeof(patterns) / sizeof(patterns[0]);
    
    send_str("\r\n[TEST] ");
    send_str(name);
    send_str(" @ ");
    send_hex(addr);
    send_str(" size=");
    send_u32(size);
    send_str(" bytes\r\n");
    
    // 测试每个数据模式
    for (int p = 0; p < num_patterns; p++) {
        UINT8 pattern = patterns[p];
        
        // 写入
        for (UINT32 i = 0; i < size; i++) {
            ptr[i] = pattern;
        }
        
        // 读取验证
        int errors = 0;
        UINT32 first_error = 0;
        for (UINT32 i = 0; i < size; i++) {
            if (ptr[i] != pattern) {
                if (errors == 0) {
                    first_error = i;
                }
                errors++;
            }
        }
        
        if (errors > 0) {
            send_str("  FAIL pattern=0x");
            send_hex(pattern);
            send_str(" errors=");
            send_u32(errors);
            send_str(" first@offset=");
            send_u32(first_error);
            send_str("\r\n");
            return -1;
        } else {
            send_str("  OK pattern=0x");
            send_hex(pattern);
            send_str("\r\n");
        }
    }
    
    return 0;
}

// 测试边界地址
static void test_boundary(UINT32 addr, const char *name) {
    volatile UINT8 *ptr = (volatile UINT8 *)addr;
    UINT8 test_val = 0xA5;
    
    send_str("\r\n[BOUNDARY] ");
    send_str(name);
    send_str(" @ ");
    send_hex(addr);
    
    // 尝试写入
    *ptr = test_val;
    UINT8 read_val = *ptr;
    
    if (read_val == test_val) {
        send_str(" OK\r\n");
    } else {
        send_str(" FAIL (wrote 0x");
        send_hex(test_val);
        send_str(" read 0x");
        send_hex(read_val);
        send_str(")\r\n");
    }
}

int main(void) {
    // GPIO 初始化（LED 闪烁）
    RCC_HB2PeriphClockCmd(RCC_HB2Periph_GPIOB, ENABLE);
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_4;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_High;
    GPIO_Init(GPIOB, &GPIO_InitStructure);
    
    // 系统初始化
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);
    
    // LED 闪烁 3 次
    for (int i = 0; i < 6; i++) {
        GPIO_WriteBit(GPIOB, GPIO_Pin_4, (i % 2 == 0) ? Bit_SET : Bit_RESET);
        Delay_Ms(200);
    }
    
    send_str("\r\n========================================\r\n");
    send_str("Test4.1: Memory Address Validation\r\n");
    send_str("========================================\r\n");
    send_str("V5F SystemCoreClk:");
    send_u32(SystemCoreClock);
    send_str("\r\n\r\n");
    
    int total_tests = 0;
    int passed_tests = 0;
    
    // 测试 1: input_buf @ 0x20100000 (12KB)
    total_tests++;
    send_str("\r\n[1/5] Testing input_buf...\r\n");
    if (test_memory_region(0x20100000, 12288, "input_buf") == 0) {
        passed_tests++;
        send_str("  RESULT: PASS\r\n");
    } else {
        send_str("  RESULT: FAIL\r\n");
    }
    
    // 测试 2: conv_buf @ 0x20103000 (32KB)
    total_tests++;
    send_str("\r\n[2/5] Testing conv_buf...\r\n");
    if (test_memory_region(0x20103000, 32768, "conv_buf") == 0) {
        passed_tests++;
        send_str("  RESULT: PASS\r\n");
    } else {
        send_str("  RESULT: FAIL\r\n");
    }
    
    // 测试 3: pool_buf @ 0x2010B000 (2KB)
    total_tests++;
    send_str("\r\n[3/5] Testing pool_buf...\r\n");
    if (test_memory_region(0x2010B000, 2048, "pool_buf") == 0) {
        passed_tests++;
        send_str("  RESULT: PASS\r\n");
    } else {
        send_str("  RESULT: FAIL\r\n");
    }
    
    // 测试 4: DVP DMA buffer @ 0x20140000 (~30KB)
    total_tests++;
    send_str("\r\n[4/5] Testing DVP_DMA_buffer...\r\n");
    if (test_memory_region(0x20140000, 30720, "DVP_DMA_buffer") == 0) {
        passed_tests++;
        send_str("  RESULT: PASS\r\n");
    } else {
        send_str("  RESULT: FAIL\r\n");
    }
    
    // 测试 5: jpeg_dec_buf @ 0x20180000 (480KB)
    // 分块测试，避免一次测试太大
    total_tests++;
    send_str("\r\n[5/5] Testing jpeg_dec_buf (480KB, testing in blocks)...\r\n");
    
    UINT32 jpeg_addr = 0x20180000;
    UINT32 jpeg_size = 480 * 1024;  // 480KB
    UINT32 block_size = 64 * 1024;  // 64KB per block
    int jpeg_pass = 1;
    
    for (UINT32 offset = 0; offset < jpeg_size; offset += block_size) {
        UINT32 current_addr = jpeg_addr + offset;
        UINT32 current_size = (offset + block_size > jpeg_size) ? (jpeg_size - offset) : block_size;
        
        send_str("  Block ");
        send_u32(offset / 1024);
        send_str("KB-");
        send_u32((offset + current_size) / 1024);
        send_str("KB: ");
        
        if (test_memory_region(current_addr, current_size, "") == 0) {
            send_str("    OK\r\n");
        } else {
            send_str("    FAIL\r\n");
            jpeg_pass = 0;
            break;
        }
    }
    
    if (jpeg_pass) {
        passed_tests++;
        send_str("  RESULT: PASS\r\n");
    } else {
        send_str("  RESULT: FAIL\r\n");
    }
    
    // 测试边界地址
    send_str("\r\n========================================\r\n");
    send_str("Boundary Tests:\r\n");
    send_str("========================================\r\n");
    
    test_boundary(0x2017FFFF, "Shared_SRAM_end");
    test_boundary(0x20180000, "jpeg_dec_buf_start");
    test_boundary(0x201F4000, "jpeg_dec_buf_end");
    test_boundary(0x201FFFFF, "Shared_SRAM_last_byte");
    
    // 总结
    send_str("\r\n========================================\r\n");
    send_str("Summary:\r\n");
    send_str("========================================\r\n");
    send_str("Total tests: ");
    send_u32(total_tests);
    send_str("\r\n");
    send_str("Passed: ");
    send_u32(passed_tests);
    send_str("\r\n");
    send_str("Failed: ");
    send_u32(total_tests - passed_tests);
    send_str("\r\n");
    
    if (passed_tests == total_tests) {
        send_str("\r\n*** ALL TESTS PASSED ***\r\n");
    } else {
        send_str("\r\n*** SOME TESTS FAILED ***\r\n");
    }
    
    send_str("\r\nTest completed.\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
