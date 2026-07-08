#ifndef __JPEG_DEC_H
#define __JPEG_DEC_H

#include "ch32h417.h"

#define JPEG_DEC_OK              0
#define JPEG_DEC_ERR_FORMAT      -1
#define JPEG_DEC_ERR_MEMORY      -2
#define JPEG_DEC_ERR_UNSUPPORTED -3

extern UINT8 *jpeg_dec_buf;
extern int jpeg_dec_width;
extern int jpeg_dec_height;
extern int jpeg_dec_num_components;
extern int jpeg_dec_comp_h[3];
extern int jpeg_dec_comp_v[3];
extern int jpeg_dec_H_max;
extern int jpeg_dec_V_max;
extern UINT8 jpeg_dec_huff_dc_bits[2][17];
extern UINT8 jpeg_dec_huff_ac_bits[2][17];
extern int jpeg_dec_raw_dc[8];
extern int jpeg_dec_debug_cat[8];
extern int jpeg_dec_debug_val[8];
extern UINT8 jpeg_dec_bitstream[4];
extern int jpeg_dec_block_bits[8];
extern int jpeg_dec_dc_bits_arr[8];
extern int jpeg_dec_ac_bits_arr[8];

int jpeg_dec_init(void);
int jpeg_dec_decode(const UINT8 *jpeg_data, UINT32 jpeg_size);

#endif
