"""
Verify the fixed IDCT with C(0) normalization only in row transform.
"""
import numpy as np
import cv2

# Corrected cosine table
COS_TABLE = [
    [  16384,  16069,  15137,  13623,  11585,   9102,   6270,   3196],
    [  16384,  13623,   6270,  -3196, -11585, -16069, -15137,  -9102],
    [  16384,   9102,  -6270, -16069, -11585,   3196,  15137,  13623],
    [  16384,   3196, -15137,  -9102,  11585,  13623,  -6270, -16069],
    [  16384,  -3196, -15137,   9102,  11585, -13623,  -6270,  16069],
    [  16384,  -9102,  -6270,  16069, -11585,  -3196,  15137, -13623],
    [  16384, -13623,   6270,   3196, -11585,  16069, -15137,   9102],
    [  16384, -16069,  15137, -13623,  11585,  -9102,   6270,  -3196]
]

def idct_fixed(coeffs):
    """Fixed IDCT: C(0) normalization only in row transform"""
    temp = [0] * 64
    # Row transform with C(k) normalization
    for i in range(8):
        for j in range(8):
            s = 0
            for k in range(8):
                c = coeffs[i * 8 + k]
                if k == 0:
                    c = (c * 11585) >> 14
                s += COS_TABLE[j][k] * c
            temp[i * 8 + j] = s >> 14
    
    # Column transform (no C(k) normalization)
    out = [0] * 64
    for j in range(8):
        for i in range(8):
            s = 0
            for k in range(8):
                s += COS_TABLE[i][k] * temp[k * 8 + j]
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[i * 8 + j] = val
    return out

# Test with DC=-341
test_coeffs = [-341] + [0] * 63
out = idct_fixed(test_coeffs)
print(f"DC=-341: output[0:8] = {out[:8]}")
print(f"  Expected: all 85 (DC/8 + 128 = 85.375)")
print(f"  Mean: {np.mean(out):.1f}")

# Test with DC=64
test_coeffs2 = [64] + [0] * 63
out2 = idct_fixed(test_coeffs2)
print(f"\nDC=64: output[0:8] = {out2[:8]}")
print(f"  Expected: all 136 (DC/8 + 128 = 136)")
print(f"  Mean: {np.mean(out2):.1f}")

# Test with DC=0
test_coeffs3 = [0] * 64
out3 = idct_fixed(test_coeffs3)
print(f"\nDC=0: output[0:8] = {out3[:8]}")
print(f"  Expected: all 128")

# Full decode test
print("\n=== Full Decode Test ===")
from full_decode import parse_jpeg, huff_build, BitReader, huff_decode, ZIGZAG

with open(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', 'rb') as f:
    jpeg_data = f.read()

parsed = parse_jpeg(jpeg_data)
W, H, NC, sof_comps = parsed['sof']
quant_table = parsed['dqt'][0]
dc_bits, dc_huffval = parsed['dht'][(0, 0)]
ac_bits, ac_huffval = parsed['dht'][(1, 0)]

dc_maxcode, dc_valptr, dc_hv = huff_build(dc_bits, dc_huffval)
ac_maxcode, ac_valptr, ac_hv = huff_build(ac_bits, ac_huffval)

reader = BitReader(parsed['compressed'])
prev_dc = 0
mcu_cols = (W + 7) // 8
mcu_rows = (H + 7) // 8
output = np.zeros((H, W), dtype=np.uint8)

block_idx = 0
for mcu_row in range(mcu_rows):
    for mcu_col in range(mcu_cols):
        cat = huff_decode(reader, dc_maxcode, dc_valptr, dc_bits, dc_hv)
        if cat > 0:
            val = reader.read_bits(cat)
            if val < (1 << (cat - 1)):
                val -= (1 << cat) - 1
        else:
            val = 0
        prev_dc += val
        
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
        
        for i in range(64):
            coeffs[i] *= quant_table[i]
        
        block = idct_fixed(coeffs)
        
        px0 = mcu_col * 8
        py0 = mcu_row * 8
        for y in range(8):
            for x in range(8):
                px = px0 + x
                py = py0 + y
                if px < W and py < H:
                    output[py, px] = block[y * 8 + x]
        
        block_idx += 1

ref = cv2.imread(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', cv2.IMREAD_GRAYSCALE)
diff = np.abs(output.astype(int) - ref.astype(int))
print(f"Output: min={output.min()}, max={output.max()}, mean={output.mean():.1f}")
print(f"Diff vs OpenCV: mean={diff.mean():.2f}, max={diff.max()}")
for t in [5, 10, 20, 50]:
    pct = np.sum(diff < t) * 100 / (W * H)
    print(f"  Pixels with diff < {t}: {pct:.1f}%")

from PIL import Image
Image.fromarray(output).save(r'E:\dvp-uart\Match\code\fixed_decode.png')
print(f"\nSaved fixed_decode.png")
