#include "debug.h"

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

    printf("V3F: Wake up V5F\r\n");
    NVIC_WakeUp_V5F(Core_V5F_StartAddr);
    PWR_EnterSTOPMode(PWR_Regulator_ON, PWR_STOPEntry_WFE);
    printf("V3F: Woke up\r\n");
    
    while(1) {
        Delay_Ms(1000);
    }
}
