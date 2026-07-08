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

void Hardware(void);
void dvp_restart(void);

#ifdef __cplusplus
}
#endif

#endif
