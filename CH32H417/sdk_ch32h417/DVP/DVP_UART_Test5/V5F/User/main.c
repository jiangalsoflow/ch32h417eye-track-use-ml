#include "debug.h"

#define SHARED_MEM_ADDR  0x20140000
#define PATTERN_SIZE     1024

static void send_byte(UINT8 b) {
    while(USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
    USART_SendData(USART1, b);
}

static void send_str(const char *s) {
    while (*s) {
        send_byte(*s++);
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
    SystemAndCoreClockUpdate();
    Delay_Init();
    
    send_str("\r\n========================================\r\n");
    send_str("Test5: V5F Shared Memory Read Verify\r\n");
    send_str("========================================\r\n");
    send_str("V5F SystemCoreClk:");
    send_hex(SystemCoreClock);
    send_str("\r\n\r\n");
    
    send_str("V5F: Reading shared memory at 0x");
    send_hex(SHARED_MEM_ADDR);
    send_str("...\r\n");
    
    UINT8 *shared_mem = (UINT8 *)SHARED_MEM_ADDR;
    
    send_str("V5F: First 16 bytes: ");
    for (int i = 0; i < 16; i++) {
        UINT8 val = shared_mem[i];
        const char hex[] = "0123456789ABCDEF";
        send_byte(hex[(val >> 4) & 0xF]);
        send_byte(hex[val & 0xF]);
        send_byte(' ');
    }
    send_str("\r\n");
    
    send_str("V5F: Verifying pattern...\r\n");
    
    int errors = 0;
    int first_error_pos = -1;
    UINT8 first_error_expected = 0;
    UINT8 first_error_actual = 0;
    
    for (int i = 0; i < PATTERN_SIZE; i++) {
        UINT8 expected = (UINT8)(i & 0xFF);
        UINT8 actual = shared_mem[i];
        if (actual != expected) {
            if (errors == 0) {
                first_error_pos = i;
                first_error_expected = expected;
                first_error_actual = actual;
            }
            errors++;
        }
    }
    
    if (errors == 0) {
        send_str("*** ALL TESTS PASSED ***\r\n");
        send_str("V5F: All 1024 bytes match expected pattern.\r\n");
    } else {
        send_str("*** TEST FAILED ***\r\n");
        send_str("V5F: Errors found: ");
        send_hex(errors);
        send_str("\r\n");
        send_str("V5F: First error at position ");
        send_hex(first_error_pos);
        send_str(", expected ");
        send_hex(first_error_expected);
        send_str(", got ");
        send_hex(first_error_actual);
        send_str("\r\n");
    }
    
    send_str("\r\nTest completed.\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
