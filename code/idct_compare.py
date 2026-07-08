"""
Compare MCU integer IDCT vs standard float IDCT.
"""
import numpy as np
import cv2

# MCU's cosine table
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
    """Exact replica of MCU's idct()"""
    temp = [0] * 64
    for i in range(8):
        for j in range(8):
            s = 0
            for k in range(8):
                c = coeffs[i * 8 + k]
                if k == 0:
                    c = (c * 11585) >> 14
                s += COS_TABLE[j][k] * c
            temp[i * 8 + j] = s >> 14
    
    out = [0] * 64
    for j in range(8):
        for i in range(8):
            s = 0
            for k in range(8):
                c = temp[k * 8 + j]
                if k == 0:
                    c = (c * 11585) >> 14
                s += COS_TABLE[i][k] * c
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[i * 8 + j] = val
    return out

def idct_float_standard(coeffs):
    """
    Standard JPEG float IDCT.
    f(x,y) = (1/4) * sum_u sum_v C(u)*C(v)*F(u,v)*cos((2x+1)*u*pi/16)*cos((2y+1)*v*pi/16)
    where C(0) = 1/sqrt(2), C(u>0) = 1
    """
    block = np.array(coeffs, dtype=np.float64).reshape(8, 8)
    out = np.zeros((8, 8), dtype=np.float64)
    
    for x in range(8):
        for y in range(8):
            s = 0.0
            for u in range(8):
                for v in range(8):
                    cu = 1.0 / np.sqrt(2) if u == 0 else 1.0
                    cv = 1.0 / np.sqrt(2) if v == 0 else 1.0
                    cos_u = np.cos((2*x + 1) * u * np.pi / 16)
                    cos_v = np.cos((2*y + 1) * v * np.pi / 16)
                    s += cu * cv * block[u, v] * cos_u * cos_v
            out[x, y] = s / 4.0 + 128.0
    
    out = np.clip(out, 0, 255).astype(np.uint8)
    return out.flatten().tolist()

# Test with first block: DC = -341, all AC = 0
test_coeffs = [-341] + [0] * 63

print("=== Test Block: DC=-341, AC=0 ===")
print(f"Input coeffs[0:8]: {test_coeffs[:8]}")

mcu_out = idct_mcu(test_coeffs)
print(f"MCU IDCT output[0:8]: {mcu_out[:8]}")
print(f"MCU IDCT mean: {np.mean(mcu_out):.1f}")

float_out = idct_float_standard(test_coeffs)
print(f"Float IDCT output[0:8]: {float_out[:8]}")
print(f"Float IDCT mean: {np.mean(float_out):.1f}")

# What should a pure DC block produce?
# DC = -341, after IDCT should be DC/8 + 128 = -42.625 + 128 = 85.375
expected_val = -341 / 8 + 128
print(f"Expected (DC/8 + 128): {expected_val:.1f}")

# Test with a simple case: DC=0, all AC=0
print("\n=== Test Block: DC=0, AC=0 ===")
test_coeffs2 = [0] * 64
mcu_out2 = idct_mcu(test_coeffs2)
float_out2 = idct_float_standard(test_coeffs2)
print(f"MCU output[0:8]: {mcu_out2[:8]}")
print(f"Float output[0:8]: {float_out2[:8]}")
print(f"Expected: all 128")

# Test with DC=64 (should produce all 136 = 64/8 + 128)
print("\n=== Test Block: DC=64, AC=0 ===")
test_coeffs3 = [64] + [0] * 63
mcu_out3 = idct_mcu(test_coeffs3)
float_out3 = idct_float_standard(test_coeffs3)
print(f"MCU output[0:8]: {mcu_out3[:8]}")
print(f"Float output[0:8]: {float_out3[:8]}")
print(f"Expected: all 136 (64/8 + 128)")

# Compare with OpenCV's first block
ref = cv2.imread(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', cv2.IMREAD_GRAYSCALE)
print(f"\n=== OpenCV Reference First Block ===")
print(f"First 8x8 block:\n{ref[0:8, 0:8]}")
print(f"Mean: {ref[0:8, 0:8].mean():.1f}")

# The issue: MCU's IDCT doesn't match float IDCT
# Let's check if the cosine table is correct
print("\n=== Cosine Table Verification ===")
# Standard DCT-II cosine: cos((2*i+1)*j*pi/16)
for i in range(2):
    for j in range(4):
        expected = int(16384 * np.cos((2*i + 1) * j * np.pi / 16))
        actual = COS_TABLE[i][j]
        match = "OK" if abs(expected - actual) < 2 else "MISMATCH"
        print(f"COS[{i}][{j}]: expected={expected}, actual={actual} {match}")
