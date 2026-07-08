#include "debug.h"
#include "eye_tracking_inference.h"

int main(void)
{
    SystemAndCoreClockUpdate();
    Delay_Init();
    USART_Printf_Init(115200);
    printf("V5F SystemCoreClk:%d\r\n", SystemCoreClock);
    Delay_Ms(500);

#if (Run_Core == Run_Core_V3FandV5F)
    HSEM_FastTake(HSEM_ID0);
    HSEM_ReleaseOneSem(HSEM_ID0, 0);
    printf("V5F: starting TFLM inference...\r\n");
    EyeTrackingInference();

#elif (Run_Core == Run_Core_V5F)
    EyeTrackingInference();
#endif

    while(1) {
        Delay_Ms(5000);
    }
}
