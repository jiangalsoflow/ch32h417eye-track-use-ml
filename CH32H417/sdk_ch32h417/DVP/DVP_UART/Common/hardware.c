/********************************** (C) COPYRIGHT  *******************************
* File Name          : hardware.c
* Description        : 简单推流 — DVP JPEG → UART → PC
*******************************************************************************/
#include "hardware.h"
#include "ov2640.h"

#ifndef Func_Run_V3F
#define Func_Run_V3F  1
#endif
#ifndef DVP_Work_Mode
#define DVP_Work_Mode  1
#endif
#ifndef JPEG_MODE
#define JPEG_MODE  1
#endif

#define JPEG_COL_NUM   800

__attribute__ ((aligned(32))) UINT32  JPEG_DVPDMAaddr0 = 0x20140000;
__attribute__ ((aligned(32))) UINT32  JPEG_DVPDMAaddr1 = 0x20140000 + JPEG_COL_NUM;

volatile UINT32 frame_cnt = 0;
volatile UINT32 addr_cnt = 0;
volatile UINT32 href_cnt = 0;

void DVP_IRQHandler (void) __attribute__((interrupt("WCH-Interrupt-fast")));

void USART_Send_Byte(u8 t)
{
    while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
    USART_SendData(USART1, t);
}

void DVP_Function_Init(void)
{
    DVP_InitTypeDef DVP_InitStructure = {0};
    RCC_HBPeriphClockCmd(RCC_HBPeriph_DVP, ENABLE);
    DVP_DeInit();
    DVP_InitStructure.DVP_DataSize = DVP_DataSize_8b;
    DVP_InitStructure.DVP_COL_NUM = JPEG_COL_NUM;
    DVP_InitStructure.DVP_HCLK_P = DVP_Hclk_P_Rising;
    DVP_InitStructure.DVP_HSYNC_P = DVP_Hsync_P_High;
    DVP_InitStructure.DVP_VSYNC_P = DVP_Vsync_P_High;
    DVP_InitStructure.DVP_DMA_BUF0_Addr = JPEG_DVPDMAaddr0;
    DVP_InitStructure.DVP_DMA_BUF1_Addr = JPEG_DVPDMAaddr1;
    DVP_InitStructure.DVP_FrameCapRate = DVP_FrameCapRate_25P;
    DVP_InitStructure.DVP_JPEGMode = ENABLE;
    DVP_Init(&DVP_InitStructure);
    DVP_ReceiveCircuitResetCmd(DISABLE);
    DVP_FIFO_ResetCmd(DISABLE);
    NVIC_EnableIRQ(DVP_IRQn);
    NVIC_SetPriority(DVP_IRQn, 0);
    DVP_ITConfig(DVP_IT_STR_FRM|DVP_IT_ROW_DONE|DVP_IT_FRM_DONE|DVP_IT_FIFO_OV|DVP_IT_STP_FRM, ENABLE);
    DVP_DMACmd(ENABLE);
    DVP_Cmd(ENABLE);
}

#if Func_Run_V3F
void DVP_IRQHandler(void)
{
    if (DVP_GetITStatus(DVP_IT_ROW_DONE) != RESET) {
        DVP_ClearITPendingBit(DVP_IT_ROW_DONE);
        href_cnt++;
        if (addr_cnt%2) { addr_cnt++; DVP->DMA_BUF1 += JPEG_COL_NUM * 2; }
        else            { addr_cnt++; DVP->DMA_BUF0 += JPEG_COL_NUM * 2; }
    }
    if (DVP_GetITStatus(DVP_IT_FRM_DONE) != RESET) {
        DVP_ClearITPendingBit(DVP_IT_FRM_DONE);
        DVP_Cmd(DISABLE);
        href_cnt = href_cnt * JPEG_COL_NUM;
        { UINT32 i; UINT8 *p = (UINT8*)0x20140000;
          for (i = 0; i < href_cnt; i++) {
            while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
            USART_SendData(USART1, *p++); } }
        DVP->DMA_BUF0 = JPEG_DVPDMAaddr0;
        DVP->DMA_BUF1 = JPEG_DVPDMAaddr1;
        href_cnt = 0; addr_cnt = 0;
        DVP_Cmd(ENABLE);
    }
    if (DVP_GetITStatus(DVP_IT_STR_FRM) != RESET) { DVP_ClearITPendingBit(DVP_IT_STR_FRM); frame_cnt++; }
    if (DVP_GetITStatus(DVP_IT_STP_FRM) != RESET) DVP_ClearITPendingBit(DVP_IT_STP_FRM);
    if (DVP_GetITStatus(DVP_IT_FIFO_OV) != RESET) DVP_ClearITPendingBit(DVP_IT_FIFO_OV);
}
#endif

void Hardware(void)
{
    OV_PWDN_SET; OV_RESET_SET; Delay_Ms(100);
    OV_RESET_CLR; OV_PWDN_CLR; Delay_Ms(500);
    OV_PWDN_SET; Delay_Ms(100); OV_RESET_SET; Delay_Ms(100);
    while(OV2640_Init()) { Delay_Ms(1000); }
    Delay_Ms(1000); RGB565_Mode_Init(); Delay_Ms(1000);
#if (DVP_Work_Mode == JPEG_MODE)
    JPEG_Mode_Init(); Delay_Ms(1000);
#endif
    DVP_Function_Init();
    printf("FW: STREAM v1\r\n");
    while(1) { Delay_Ms(1000); }
}
