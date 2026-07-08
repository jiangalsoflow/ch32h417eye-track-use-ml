#include "debug.h"

int main(void)
{
    SystemInit();
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(921600);
    Delay_Ms(500);
    printf("V3F: SystemClk=%d CoreClk=%d\r\n", SystemClock, SystemCoreClock);

    RCC_HB1PeriphClockCmd(RCC_HB1Periph_PWR, ENABLE);
    PWR_VIO18ModeCfg(PWR_VIO18CFGMODE_SW);
    PWR_VIO18LevelCfg(PWR_VIO18Level_MODE3);

    printf("V3F: waking V5F...\r\n");
    NVIC_WakeUp_V5F(Core_V5F_StartAddr);
    HSEM_ITConfig(HSEM_ID0, ENABLE);
    NVIC->SCTLR |= 1<<4;
    PWR_EnterSTOPMode(PWR_Regulator_ON, PWR_STOPEntry_WFE);
    HSEM_ClearFlag(HSEM_ID0);
    printf("V3F: V5F running\r\n");

    while(1) {
        Delay_Ms(5000);
    }
}
