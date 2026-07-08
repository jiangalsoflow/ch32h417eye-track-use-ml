/********************************** (C) COPYRIGHT  *******************************
* File Name          : hardware.h
* Author             : WCH
* Version            : V1.0.0
* Date               : 2025/03/01
* Description        : This file contains all the functions prototypes for the 
*                      hardware.
*********************************************************************************
* Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
* Attention: This software (modified or not) and binary are used for 
* microcontroller manufactured by Nanjing Qinheng Microelectronics.
*******************************************************************************/
#ifndef __HARDWARE_H
#define __HARDWARE_H

#ifdef __cplusplus
 extern "C" {
#endif

#include "ch32h417.h"
#include "debug.h"

extern volatile UINT32 frame_ready;
extern volatile UINT32 jpeg_size;
extern volatile UINT32 frame_cnt;
extern volatile UINT32 href_cnt;
extern volatile UINT32 addr_cnt;
extern UINT32 JPEG_DVPDMAaddr0;
extern UINT32 JPEG_DVPDMAaddr1;

void Hardware(void);
void dvp_restart(void);

#ifdef __cplusplus
}
#endif

#endif 





