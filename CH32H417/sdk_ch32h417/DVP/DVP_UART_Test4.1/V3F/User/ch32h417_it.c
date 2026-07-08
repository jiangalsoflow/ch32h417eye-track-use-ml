/********************************** (C) COPYRIGHT *******************************
* File Name          : ch32h417_it.c
* Author             : WCH
* Version            : V1.0.0
* Date               : 2025/03/01
* Description        : Main Interrupt Service Routines.
*********************************************************************************
* Copyright (c) 2025 Nanjing Qinheng Microelectronics Co., Ltd.
* Attention: This software (modified or not) and binary are used for 
* microcontroller manufactured by Nanjing Qinheng Microelectronics.
*******************************************************************************/
#include "ch32h417_it.h"

void NMI_Handler(void) __attribute__((interrupt("WCH-Interrupt-fast")));
void HardFault_Handler(void) __attribute__((interrupt("WCH-Interrupt-fast")));

/*********************************************************************
 * @fn      NMI_Handler
 *
 * @brief   This function handles NMI exception.
 *
 * @return  none
 */
void NMI_Handler(void)
{
  while (1)
  {
  }
}

/*********************************************************************
 * @fn      HardFault_Handler
 *
 * @brief   This function handles Hard Fault exception.
 *
 * @return  none
 */
static void dbg_putc(char c) {
  while (USART_GetFlagStatus(USART1, USART_FLAG_TC) == RESET);
  USART_SendData(USART1, c);
}
static void dbg_puts(const char *s) { while (*s) dbg_putc(*s++); }
static void dbg_hex(unsigned long v) {
  int i; dbg_puts("0x");
  for(i=28;i>=0;i-=4){ unsigned long n=(v>>i)&0xF; dbg_putc(n<10?'0'+n:'A'+n-10); }
}

void HardFault_Handler(void)
{
  unsigned long mcause, mepc, mtval;
  asm volatile("csrr %0, mcause" : "=r"(mcause));
  asm volatile("csrr %0, mepc"   : "=r"(mepc));
  asm volatile("csrr %0, mtval"  : "=r"(mtval));

  dbg_puts("\r\nV3F FAULT mcause="); dbg_hex(mcause);
  dbg_puts(" mepc="); dbg_hex(mepc);
  dbg_puts(" mtval="); dbg_hex(mtval);
  dbg_puts("\r\n");

  Delay_Ms(10);
  NVIC_SystemReset();
  while (1) {}
}


