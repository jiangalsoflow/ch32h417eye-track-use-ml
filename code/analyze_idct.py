"""
Analyze the correct IDCT scaling.
"""
import numpy as np

# Standard JPEG IDCT formula:
# f(x,y) = (1/4) * sum_u sum_v C(u)*C(v)*F(u,v)*cos((2x+1)*u*pi/16)*cos((2y+1)*v*pi/16)
# where C(0) = 1/sqrt(2), C(u>0) = 1

# For a pure DC block (only F(0,0) != 0):
# f(x,y) = (1/4) * C(0)*C(0)*F(0,0)*cos(0)*cos(0)
#        = (1/4) * (1/sqrt(2))^2 * F(0,0) * 1 * 1
#        = (1/4) * (1/2) * F(0,0)
#        = F(0,0) / 8

# Test with F(0,0) = -341
# Expected: -341 / 8 + 128 = -42.625 + 128 = 85.375

# Separable implementation:
# Row pass: g(x,v) = (1/2) * sum_u C(u)*F(u,v)*cos((2x+1)*u*pi/16)
# Col pass: f(x,y) = (1/2) * sum_v C(v)*g(x,v)*cos((2y+1)*v*pi/16)

# For pure DC:
# Row pass: g(x,0) = (1/2) * C(0)*F(0,0)*cos(0) = (1/2) * (1/sqrt(2)) * F(0,0) * 1 = F(0,0) / (2*sqrt(2))
# Col pass: f(x,y) = (1/2) * C(0)*g(x,0)*cos(0) = (1/2) * (1/sqrt(2)) * F(0,0)/(2*sqrt(2)) * 1
#                   = F(0,0) / (4*2) = F(0,0) / 8 ✓

print("=== Standard JPEG IDCT Analysis ===")
print("For pure DC block F(0,0) = -341:")
print("Expected output: -341 / 8 + 128 = 85.375")

# Now let's implement it correctly with fixed-point
SCALE = 16384  # 2^14
C0 = int(SCALE / np.sqrt(2))  # C(0) = 1/sqrt(2) scaled by 2^14

print(f"\nFixed-point constants:")
print(f"  SCALE = {SCALE}")
print(f"  C(0) = {C0} (should be ~11585)")

# Correct implementation
def idct_correct(coeffs):
    """Correct JPEG IDCT with proper scaling"""
    # Cosine table: cos((2*i+1)*j*pi/16) scaled by 2^14
    cos_table = np.zeros((8, 8))
    for i in range(8):
        for j in range(8):
            cos_table[i, j] = int(round(SCALE * np.cos((2*i + 1) * j * np.pi / 16)))
    
    # Row transform
    temp = [[0]*8 for _ in range(8)]
    for x in range(8):
        for v in range(8):
            s = 0
            for u in range(8):
                c = coeffs[u * 8 + v]
                if u == 0:
                    c = (c * C0) >> 14  # Apply C(0)
                s += c * int(cos_table[x, u])
            temp[x][v] = s >> 14  # Scale down by 2^14
    
    # Column transform
    out = [0] * 64
    for y in range(8):
        for x in range(8):
            s = 0
            for v in range(8):
                c = temp[x][v]
                if v == 0:
                    c = (c * C0) >> 14  # Apply C(0)
                s += c * int(cos_table[y, v])
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[x * 8 + y] = val
    
    return out

# Test
test_coeffs = [-341] + [0] * 63
out = idct_correct(test_coeffs)
print(f"\nCorrect IDCT output[0:8]: {out[:8]}")
print(f"Mean: {np.mean(out):.1f}")

# The issue: we're applying C(0) twice, which gives F(0,0) * (1/sqrt(2))^2 = F(0,0) / 2
# But we need F(0,0) / 8, so we need an additional factor of 1/4

# Let me check the actual formula more carefully...
print("\n=== Checking the formula ===")
print("Standard 2D IDCT:")
print("  f(x,y) = (1/4) * sum_u sum_v C(u)*C(v)*F(u,v)*cos(...)*cos(...)")
print("\nSeparable implementation:")
print("  Row: g(x,v) = sum_u C(u)*F(u,v)*cos((2x+1)*u*pi/16)")
print("  Col: f(x,y) = sum_v C(v)*g(x,v)*cos((2y+1)*v*pi/16)")
print("  Final: f(x,y) = f(x,y) / 4 + 128")
print("\nFor pure DC:")
print("  Row: g(x,0) = C(0)*F(0,0)*cos(0) = F(0,0)/sqrt(2)")
print("  Col: f(x,y) = C(0)*g(x,0)*cos(0) = F(0,0)/sqrt(2)/sqrt(2) = F(0,0)/2")
print("  Final: F(0,0)/2 / 4 + 128 = F(0,0)/8 + 128")

# So the fix is to divide by 4 at the end!
def idct_with_div4(coeffs):
    """IDCT with /4 at the end"""
    cos_table = np.zeros((8, 8))
    for i in range(8):
        for j in range(8):
            cos_table[i, j] = int(round(SCALE * np.cos((2*i + 1) * j * np.pi / 16)))
    
    # Row transform
    temp = [[0]*8 for _ in range(8)]
    for x in range(8):
        for v in range(8):
            s = 0
            for u in range(8):
                c = coeffs[u * 8 + v]
                if u == 0:
                    c = (c * C0) >> 14
                s += c * int(cos_table[x, u])
            temp[x][v] = s >> 14
    
    # Column transform
    out = [0] * 64
    for y in range(8):
        for x in range(8):
            s = 0
            for v in range(8):
                c = temp[x][v]
                if v == 0:
                    c = (c * C0) >> 14
                s += c * int(cos_table[y, v])
            val = (s >> 16) + 128  # >> 16 instead of >> 14 gives /4
            if val < 0: val = 0
            if val > 255: val = 255
            out[x * 8 + y] = val
    
    return out

test_coeffs = [-341] + [0] * 63
out2 = idct_with_div4(test_coeffs)
print(f"\nIDCT with /4 output[0:8]: {out2[:8]}")
print(f"Mean: {np.mean(out2):.1f}")
