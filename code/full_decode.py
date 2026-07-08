"""
Full JPEG decoder matching MCU algorithm exactly.
Compare intermediate values to find the remaining bug.
"""
import numpy as np
import cv2
import struct

with open(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', 'rb') as f:
    jpeg_data = f.read()

# ====== Parse markers ======
def parse_jpeg(data):
    pos = 2  # skip SOI
    result = {'dqt': {}, 'dht': {}, 'sof': None, 'sos': None, 'compressed': None}
    
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = (data[pos] << 8) | data[pos + 1]
        pos += 2
        
        if marker == 0xFFD9:
            break
        if marker == 0xFF00 or (0xFFD0 <= marker <= 0xFFD7):
            continue
        
        length = (data[pos] << 8) | data[pos + 1]
        mdata = data[pos + 2:pos + length]
        
        if marker == 0xFFDB:  # DQT
            info = mdata[0]
            qid = info & 0xF
            result['dqt'][qid] = list(mdata[1:65])
        elif marker == 0xFFC4:  # DHT
            info = mdata[0]
            cls = (info >> 4) & 0xF
            tid = info & 0xF
            bits = [0] + list(mdata[1:17])
            total = sum(bits)
            huffval = list(mdata[17:17+total])
            result['dht'][(cls, tid)] = (bits, huffval)
        elif marker == 0xFFC0:  # SOF0
            prec = mdata[0]
            h = (mdata[1] << 8) | mdata[2]
            w = (mdata[3] << 8) | mdata[4]
            nc = mdata[5]
            comps = []
            for i in range(nc):
                cid = mdata[6 + i*3]
                sampling = mdata[7 + i*3]
                qt = mdata[8 + i*3]
                comps.append((cid, sampling >> 4, sampling & 0xF, qt))
            result['sof'] = (w, h, nc, comps)
        elif marker == 0xFFDA:  # SOS
            ns = mdata[0]
            sos_comps = []
            for i in range(ns):
                cid = mdata[1 + i*2]
                tab = mdata[2 + i*2]
                sos_comps.append((cid, tab >> 4, tab & 0xF))
            result['sos'] = (ns, sos_comps)
            result['compressed'] = data[pos + length:]
            break
        
        pos += length
    
    return result

parsed = parse_jpeg(jpeg_data)
W, H, NC, sof_comps = parsed['sof']
print(f"Image: {W}x{H}, components: {NC}")
for cid, sh, sv, qt in sof_comps:
    print(f"  Component {cid}: h={sh}, v={sv}, qt={qt}")

quant_table = parsed['dqt'][0]
print(f"Quant table[0]: min={min(quant_table)}, max={max(quant_table)}, mean={np.mean(quant_table):.1f}")

dc_bits, dc_huffval = parsed['dht'][(0, 0)]
ac_bits, ac_huffval = parsed['dht'][(1, 0)]
print(f"DC bits: {dc_bits[1:]}, entries: {sum(dc_bits)}")
print(f"AC bits: {ac_bits[1:]}, entries: {sum(ac_bits)}")

# ====== Build Huffman tables ======
def huff_build(bits, huffval):
    k = 0
    code = 0
    maxcode = [0] * 17
    valptr = [0] * 17
    for i in range(1, 17):
        valptr[i] = k
        if bits[i] > 0:
            maxcode[i] = code + bits[i] - 1
            code += bits[i]
            k += bits[i]
        else:
            maxcode[i] = -1
        code <<= 1
    return maxcode, valptr, huffval

dc_maxcode, dc_valptr, dc_hv = huff_build(dc_bits, dc_huffval)
ac_maxcode, ac_valptr, ac_hv = huff_build(ac_bits, ac_huffval)

# ====== Bit reader ======
class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.bit_buf = 0
        self.bit_cnt = 0
    
    def read_bit(self):
        if self.bit_cnt == 0:
            if self.pos >= len(self.data):
                return -1
            self.bit_buf = self.data[self.pos]
            self.pos += 1
            if self.bit_buf == 0xFF and self.pos < len(self.data) and self.data[self.pos] == 0x00:
                self.pos += 1
            self.bit_cnt = 8
        self.bit_cnt -= 1
        return (self.bit_buf >> self.bit_cnt) & 1
    
    def read_bits(self, n):
        val = 0
        for _ in range(n):
            b = self.read_bit()
            if b < 0: return -1
            val = (val << 1) | b
        return val

def huff_decode(reader, maxcode, valptr, bits, huffval):
    code = 0
    for i in range(1, 17):
        b = reader.read_bit()
        if b < 0: return -1
        code = (code << 1) | b
        if bits[i] > 0:
            mc = maxcode[i] - bits[i] + 1
            if mc <= code <= maxcode[i]:
                idx = valptr[i] + (code - mc)
                return huffval[idx]
    return -999

ZIGZAG = [
    0,  1,  8, 16,  9,  2,  3, 10,
    17, 24, 32, 25, 18, 11,  4,  5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13,  6,  7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63
]

# ====== MCU-style integer IDCT ======
COS_TABLE = [
    [ 16384,  16069,  15137,  13623,  11585,   9102,   6270,   3197],
    [ 16069,  13623,   6270,  -3197, -11585, -15137, -16069, -13623],
    [ 15137,   6270,  -9102, -16069, -13623,   3197,  16069,  11585],
    [ 13623,  -3197, -16069, -11585,   6270,  16069,   9102, -15137],
    [ 11585, -11585, -13623,   6270,  16069,   3197, -15137,  -9102],
    [  9102, -15137,   3197,  16069,  -6270, -13623,  11585,   6270],
    [  6270, -16069,  16069,  -9102, -15137,  11585,   3197, -13623],
    [  3197, -13623,  11585, -15137,  -9102,   6270,  16069, -16069]
]

def idct_mcu(coeffs):
    """Exact replica of MCU's idct() - with transposed cos_table indexing"""
    temp = [0] * 64
    for i in range(8):
        for j in range(8):
            s = 0
            for k in range(8):
                c = coeffs[i * 8 + k]
                if k == 0:
                    c = (c * 11585) >> 14
                s += COS_TABLE[k][j] * c
            temp[i * 8 + j] = s >> 14
    
    out = [0] * 64
    for j in range(8):
        for i in range(8):
            s = 0
            for k in range(8):
                c = temp[k * 8 + j]
                if k == 0:
                    c = (c * 11585) >> 14
                s += COS_TABLE[k][i] * c
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[i * 8 + j] = val
    return out

# ====== Full decode ======
reader = BitReader(parsed['compressed'])
prev_dc = 0
mcu_cols = (W + 7) // 8
mcu_rows = (H + 7) // 8
output = np.zeros((H, W), dtype=np.uint8)

all_dc = []
first_block_coeffs = None
first_block_output = None

block_idx = 0
for mcu_row in range(mcu_rows):
    for mcu_col in range(mcu_cols):
        # Decode DC
        cat = huff_decode(reader, dc_maxcode, dc_valptr, dc_bits, dc_hv)
        if cat > 0:
            val = reader.read_bits(cat)
            if val < (1 << (cat - 1)):
                val -= (1 << cat) - 1
        else:
            val = 0
        prev_dc += val
        
        # Decode AC
        coeffs = [0] * 64
        coeffs[0] = prev_dc
        k = 1
        while k < 64:
            rs = huff_decode(reader, ac_maxcode, ac_valptr, ac_bits, ac_hv)
            if rs < 0 or rs == 0:
                break
            run = rs >> 4
            length = rs & 0xF
            k += run
            if k >= 64:
                break
            if length == 0:
                if run == 0xF:
                    continue
                break
            aval = reader.read_bits(length)
            if aval < (1 << (length - 1)):
                aval -= (1 << length) - 1
            coeffs[ZIGZAG[k]] = aval
            k += 1
        
        if block_idx == 0:
            first_block_coeffs = coeffs[:]
        
        # Dequantize
        for i in range(64):
            coeffs[i] *= quant_table[i]
        
        if block_idx < 8:
            all_dc.append(coeffs[0])
        
        # IDCT
        block = idct_mcu(coeffs)
        
        if block_idx == 0:
            first_block_output = block[:]
        
        px0 = mcu_col * 8
        py0 = mcu_row * 8
        for y in range(8):
            for x in range(8):
                px = px0 + x
                py = py0 + y
                if px < W and py < H:
                    output[py, px] = block[y * 8 + x]
        
        block_idx += 1

print(f"\n=== Python Full Decode ===")
print(f"First block coeffs[0:8]: {first_block_coeffs[:8]}")
print(f"First block output[0:8]: {first_block_output[:8]}")
print(f"First 8 DC coeffs (dequantized): {all_dc[:8]}")
print(f"Output: min={output.min()}, max={output.max()}, mean={output.mean():.1f}")
print(f"First row samples: {list(output[0, ::100])}")

# Compare with OpenCV
ref = cv2.imread(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', cv2.IMREAD_GRAYSCALE)
diff = np.abs(output.astype(int) - ref.astype(int))
print(f"\nDiff vs OpenCV: mean={diff.mean():.2f}, max={diff.max()}")
for t in [5, 10, 20, 50]:
    pct = np.sum(diff < t) * 100 / (W * H)
    print(f"  Pixels with diff < {t}: {pct:.1f}%")

# Save
from PIL import Image
Image.fromarray(output).save(r'E:\dvp-uart\Match\code\py_full_decode.png')
print(f"\nSaved py_full_decode.png")

# OpenCV reference first block
print(f"\n=== OpenCV Reference ===")
print(f"First 8x8 block:\n{ref[0:8, 0:8]}")
print(f"First row samples: {list(ref[0, ::100])}")
