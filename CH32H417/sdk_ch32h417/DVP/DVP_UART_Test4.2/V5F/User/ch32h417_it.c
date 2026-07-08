#include "ch32h417_it.h"
#include "hardware.h"

void NMI_Handler(void) __attribute__((interrupt("WCH-Interrupt-fast")));
void HardFault_Handler(void) __attribute__((interrupt("WCH-Interrupt-fast")));
void DVP_IRQHandler(void) __attribute__((interrupt("WCH-Interrupt-fast")));

void NMI_Handler(void) { while (1) {} }

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
  dbg_puts("\r\nV5F FAULT mcause="); dbg_hex(mcause);
  dbg_puts(" mepc="); dbg_hex(mepc);
  dbg_puts(" mtval="); dbg_hex(mtval);
  dbg_puts("\r\n");
  Delay_Ms(10);
  NVIC_SystemReset();
  while(1){}
}

void DVP_IRQHandler(void)
{
    if (DVP_GetITStatus(DVP_IT_ROW_DONE) != RESET) {
        DVP_ClearITPendingBit(DVP_IT_ROW_DONE);
        href_cnt++;
        if (addr_cnt%2) { addr_cnt++; DVP->DMA_BUF1 += 800 * 2; }
        else            { addr_cnt++; DVP->DMA_BUF0 += 800 * 2; }
    }
    if (DVP_GetITStatus(DVP_IT_FRM_DONE) != RESET) {
        DVP_ClearITPendingBit(DVP_IT_FRM_DONE);
        DVP_Cmd(DISABLE);
        jpeg_size = href_cnt * 800;
        // 立即重置 DMA 地址，和 Step1 一样
        DVP->DMA_BUF0 = JPEG_DVPDMAaddr0;
        DVP->DMA_BUF1 = JPEG_DVPDMAaddr1;
        href_cnt = 0;
        addr_cnt = 0;
        frame_ready = 1;
        DVP_Cmd(ENABLE);
    }
    if (DVP_GetITStatus(DVP_IT_STR_FRM) != RESET) { DVP_ClearITPendingBit(DVP_IT_STR_FRM); frame_cnt++; }
    if (DVP_GetITStatus(DVP_IT_STP_FRM) != RESET) DVP_ClearITPendingBit(DVP_IT_STP_FRM);
    if (DVP_GetITStatus(DVP_IT_FIFO_OV) != RESET) DVP_ClearITPendingBit(DVP_IT_FIFO_OV);
}