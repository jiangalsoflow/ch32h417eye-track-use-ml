#include "jpeg_dec.h"
#include <string.h>

#define MAX_WIDTH  800
#define MAX_HEIGHT 600

#define JPEG_DEC_BUF_ADDR  0x20180000

UINT8 *jpeg_dec_buf = (UINT8 *)JPEG_DEC_BUF_ADDR;
int jpeg_dec_width = 0;
int jpeg_dec_height = 0;
int jpeg_dec_num_components = 0;
int jpeg_dec_comp_h[3] = {0};
int jpeg_dec_comp_v[3] = {0};
int jpeg_dec_H_max = 1;
int jpeg_dec_V_max = 1;
UINT8 jpeg_dec_huff_dc_bits[2][17];
UINT8 jpeg_dec_huff_ac_bits[2][17];
int jpeg_dec_raw_dc[8];
int jpeg_dec_debug_cat[8];
int jpeg_dec_debug_val[8];
UINT8 jpeg_dec_bitstream[4];
int jpeg_dec_block_bits[8];
int jpeg_dec_dc_bits_arr[8];
int jpeg_dec_ac_bits_arr[8];
static int debug_idx = 0;

UINT8 quant_table[2][64];

/* Huffman table: max 162 entries (sum of bits[1..16] <= 256, but typically ~162) */
typedef struct {
    UINT8 bits[17];
    UINT8 huffval[256];
    UINT16 maxcode[17];
    int valptr[17];
    int ready;
} HuffTable;

static HuffTable dc_tab[2];
static HuffTable ac_tab[2];

static int comp_qt[3], comp_dc[3], comp_ac[3];

static const UINT8 zigzag[64] = {
    0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63
};

static const int cos_table[8][8] = {
    {  16384,  16069,  15137,  13623,  11585,   9102,   6270,   3196},
    {  16384,  13623,   6270,  -3196, -11585, -16069, -15137,  -9102},
    {  16384,   9102,  -6270, -16069, -11585,   3196,  15137,  13623},
    {  16384,   3196, -15137,  -9102,  11585,  13623,  -6270, -16069},
    {  16384,  -3196, -15137,   9102,  11585, -13623,  -6270,  16069},
    {  16384,  -9102,  -6270,  16069, -11585,  -3196,  15137, -13623},
    {  16384, -13623,   6270,   3196, -11585,  16069, -15137,   9102},
    {  16384, -16069,  15137, -13623,  11585,  -9102,   6270,  -3196}
};

static UINT32 bit_buf = 0;
static int bit_cnt = 0;
static const UINT8 *data_ptr;
static const UINT8 *data_end;
static int entropy_bit_count = 0;

static int read_bit(void) {
    if (bit_cnt == 0) {
        if (data_ptr >= data_end) return -1;
        bit_buf = *data_ptr++;
        if (bit_buf == 0xFF && data_ptr < data_end && *data_ptr == 0x00) {
            data_ptr++;
        }
        bit_cnt = 8;
    }
    bit_cnt--;
    int b = (bit_buf >> bit_cnt) & 1;
    if (entropy_bit_count < 32) {
        jpeg_dec_bitstream[entropy_bit_count >> 3] |= (b << (7 - (entropy_bit_count & 7)));
    }
    entropy_bit_count++;
    return b;
}

static int read_bits(int n) {
    int val = 0;
    for (int i = 0; i < n; i++) {
        int b = read_bit();
        if (b < 0) return -1;
        val = (val << 1) | b;
    }
    return val;
}

static void huff_build(HuffTable *ht) {
    int k = 0;
    UINT16 code = 0;
    for (int i = 1; i <= 16; i++) {
        ht->valptr[i] = k;
        ht->maxcode[i] = -1;
        if (ht->bits[i] > 0) {
            ht->maxcode[i] = code + ht->bits[i] - 1;
            code += ht->bits[i];
            k += ht->bits[i];
        }
        code <<= 1;
    }
    ht->ready = 1;
}

static int huff_decode(HuffTable *ht) {
    int code = 0;
    for (int i = 1; i <= 16; i++) {
        int b = read_bit();
        if (b < 0) return -1;
        code = (code << 1) | b;
        if (ht->bits[i] > 0) {
            int mincode = ht->maxcode[i] - ht->bits[i] + 1;
            if (code >= mincode && code <= ht->maxcode[i]) {
                int idx = ht->valptr[i] + (code - mincode);
                return ht->huffval[idx];
            }
        }
    }
    /* Debug: return sentinel value showing no match */
    return -999;
}

static int decode_dc(int comp) {
    int cat = huff_decode(&dc_tab[comp]);
    
    if (cat <= 0) {
        if (debug_idx < 8) {
            jpeg_dec_debug_cat[debug_idx] = 0;
            jpeg_dec_debug_val[debug_idx] = 0;
            debug_idx++;
        }
        return 0;
    }
    
    if (debug_idx < 8) {
        jpeg_dec_debug_cat[debug_idx] = cat;
    }
    
    int val = read_bits(cat);
    if (debug_idx < 8) {
        jpeg_dec_debug_val[debug_idx] = val;
    }
    debug_idx++;
    
    if (val < (1 << (cat - 1))) {
        val -= (1 << cat) - 1;
    }
    return val;
}

static void decode_ac(int comp, int *coeffs) {
    int k = 1;
    while (k < 64) {
        int rs = huff_decode(&ac_tab[comp]);
        if (rs < 0) break;
        if (rs == 0) break;
        int run = rs >> 4;
        int len = rs & 0xF;
        k += run;
        if (k >= 64) break;
        if (len == 0) {
            if (run == 0xF) {
                continue;
            }
            break;
        }
        int val = read_bits(len);
        if (val < (1 << (len - 1))) {
            val -= (1 << len) - 1;
        }
        coeffs[zigzag[k]] = val;
        k++;
    }
}

static void idct(int *coeffs, UINT8 *out, int stride) {
    int temp[64];
    // Row transform with C(k) normalization
    for (int i = 0; i < 8; i++) {
        for (int j = 0; j < 8; j++) {
            int sum = 0;
            for (int k = 0; k < 8; k++) {
                int c = coeffs[i * 8 + k];
                if (k == 0) c = (c * 11585) >> 14;
                sum += cos_table[j][k] * c;
            }
            temp[i * 8 + j] = sum >> 14;
        }
    }
    // Column transform with C(k) normalization and /4 scaling
    for (int j = 0; j < 8; j++) {
        for (int i = 0; i < 8; i++) {
            int sum = 0;
            for (int k = 0; k < 8; k++) {
                int c = temp[k * 8 + j];
                if (k == 0) c = (c * 11585) >> 14;
                sum += cos_table[i][k] * c;
            }
            int val = (sum >> 16) + 128;  // >> 16 gives /4 scaling
            if (val < 0) val = 0;
            if (val > 255) val = 255;
            out[i * stride + j] = val;
        }
    }
}

int jpeg_dec_init(void) {
    memset(dc_tab, 0, sizeof(dc_tab));
    memset(ac_tab, 0, sizeof(ac_tab));
    return 0;
}

int jpeg_dec_decode(const UINT8 *jpeg_data, UINT32 jpeg_size) {
    data_ptr = jpeg_data;
    data_end = jpeg_data + jpeg_size;

    if (read_bits(16) != 0xFFD8) return JPEG_DEC_ERR_FORMAT;

    while (data_ptr < data_end) {
        int marker = read_bits(16);
        if (marker == 0xFFD9) break;

        int len = read_bits(16);
        if (len < 2) return JPEG_DEC_ERR_FORMAT;
        len -= 2;

        if (marker == 0xFFC0) {
            read_bits(8);
            jpeg_dec_height = read_bits(16);
            jpeg_dec_width = read_bits(16);
            jpeg_dec_num_components = read_bits(8);
            if (jpeg_dec_num_components != 1 && jpeg_dec_num_components != 3) {
                return JPEG_DEC_ERR_UNSUPPORTED;
            }
            jpeg_dec_H_max = 1; jpeg_dec_V_max = 1;
            for (int i = 0; i < jpeg_dec_num_components; i++) {
                read_bits(8);
                int sampling = read_bits(8);
                jpeg_dec_comp_h[i] = sampling >> 4;
                jpeg_dec_comp_v[i] = sampling & 0xF;
                if (jpeg_dec_comp_h[i] > jpeg_dec_H_max) jpeg_dec_H_max = jpeg_dec_comp_h[i];
                if (jpeg_dec_comp_v[i] > jpeg_dec_V_max) jpeg_dec_V_max = jpeg_dec_comp_v[i];
                comp_qt[i] = read_bits(8);
            }
        } else if (marker == 0xFFDB) {
            while (len > 0) {
                int info = read_bits(8);
                int id = info & 0xF;
                for (int i = 0; i < 64; i++) {
                    quant_table[id][i] = read_bits(8);
                }
                len -= 65;
            }
        } else if (marker == 0xFFC4) {
            while (len > 0) {
                int info = read_bits(8);
                int cls = (info >> 4) & 0xF;
                int id = info & 0xF;
                HuffTable *ht = (cls == 0) ? &dc_tab[id] : &ac_tab[id];
                int total = 0;
                for (int i = 1; i <= 16; i++) {
                    ht->bits[i] = read_bits(8);
                    if (cls == 0) jpeg_dec_huff_dc_bits[id][i] = ht->bits[i];
                    else jpeg_dec_huff_ac_bits[id][i] = ht->bits[i];
                    total += ht->bits[i];
                }
                for (int i = 0; i < total; i++) {
                    ht->huffval[i] = read_bits(8);
                }
                huff_build(ht);
                len -= 17 + total;
            }
        } else if (marker == 0xFFDA) {
            int n = read_bits(8);
            for (int i = 0; i < n; i++) {
                read_bits(8);
                int tab = read_bits(8);
                comp_dc[i] = tab >> 4;
                comp_ac[i] = tab & 0xF;
            }
            read_bits(8);
            read_bits(8);
            read_bits(8);
            len -= 6 + 2 * n;

            memset(jpeg_dec_bitstream, 0, 4);
            entropy_bit_count = 0;
            debug_idx = 0;
            memset(jpeg_dec_debug_cat, 0, sizeof(jpeg_dec_debug_cat));
            memset(jpeg_dec_debug_val, 0, sizeof(jpeg_dec_debug_val));
            int prev_dc[3] = {0};
            int mcu_row = 0;
            int mcu_col = 0;
            int mcu_cols = (jpeg_dec_width + jpeg_dec_H_max * 8 - 1) / (jpeg_dec_H_max * 8);
            int mcu_rows = (jpeg_dec_height + jpeg_dec_V_max * 8 - 1) / (jpeg_dec_V_max * 8);
            int raw_dc_idx = 0;
            int block_idx = 0;

            while (data_ptr < data_end) {
                for (int c = 0; c < jpeg_dec_num_components; c++) {
                    for (int by = 0; by < jpeg_dec_comp_v[c]; by++) {
                        for (int bx = 0; bx < jpeg_dec_comp_h[c]; bx++) {
                            int bits_before = entropy_bit_count;
                            int dc = decode_dc(comp_dc[c]);
                            int bits_after_dc = entropy_bit_count;
                            prev_dc[c] += dc;
                            int coeffs[64];
                            memset(coeffs, 0, sizeof(coeffs));
                            coeffs[0] = prev_dc[c];
                            decode_ac(comp_ac[c], coeffs);
                            if (block_idx < 8) {
                                jpeg_dec_dc_bits_arr[block_idx] = bits_after_dc - bits_before;
                                jpeg_dec_ac_bits_arr[block_idx] = entropy_bit_count - bits_after_dc;
                                jpeg_dec_block_bits[block_idx] = entropy_bit_count - bits_before;
                            }
                            block_idx++;

                            if (raw_dc_idx < 8) {
                                jpeg_dec_raw_dc[raw_dc_idx++] = coeffs[0] * quant_table[comp_qt[c]][0];
                            }

                            for (int i = 0; i < 64; i++) {
                                coeffs[i] *= quant_table[comp_qt[c]][i];
                            }

                            UINT8 block[64];
                            idct(coeffs, block, 8);

                            int px0 = mcu_col * jpeg_dec_H_max * 8 + bx * 8;
                            int py0 = mcu_row * jpeg_dec_V_max * 8 + by * 8;

                            for (int y = 0; y < 8; y++) {
                                for (int x = 0; x < 8; x++) {
                                    int px = px0 + x;
                                    int py = py0 + y;
                                    if (px < jpeg_dec_width && py < jpeg_dec_height) {
                                        jpeg_dec_buf[py * jpeg_dec_width + px] = block[y * 8 + x];
                                    }
                                }
                            }
                        }
                    }
                }

                mcu_col++;
                if (mcu_col >= mcu_cols) {
                    mcu_col = 0;
                    mcu_row++;
                    if (mcu_row >= mcu_rows) {
                        return JPEG_DEC_OK;
                    }
                }
            }
        } else {
            for (int i = 0; i < len; i++) {
                read_bits(8);
            }
        }
    }

    return JPEG_DEC_OK;
}
