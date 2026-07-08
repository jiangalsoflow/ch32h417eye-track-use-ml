#include "debug.h"

#define SHARED_MEM_ADDR  0x20140000
#define PATTERN_SIZE     1024

int main(void)
{
    SystemInit();
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);
    Delay_Ms(1000);

    RCC_HB1PeriphClockCmd(RCC_HB1Periph_PWR, ENABLE);
    PWR_VIO18ModeCfg(PWR_VIO18CFGMODE_SW);
    PWR_VIO18LevelCfg(PWR_VIO18Level_MODE3);

    printf("V3F: Test5 - Shared Memory Pattern Write\r\n");
    printf("V3F: Writing pattern to 0x%08X...\r\n", SHARED_MEM_ADDR);

    UINT8 *shared_mem = (UINT8 *)SHARED_MEM_ADDR;
    
    for (int i = 0; i < PATTERN_SIZE; i++) {
        shared_mem[i] = (UINT8)(i & 0xFF);
    }
    
    printf("V3F: Pattern written. First 16 bytes: ");
    for (int i = 0; i < 16; i++) {
        printf("%02X ", shared_mem[i]);
    }
    printf("\r\n");
    
    printf("V3F: Waking up V5F...\r\n");
    NVIC_WakeUp_V5F(Core_V5F_StartAddr);
    
    printf("V3F: Done. Waiting...\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
