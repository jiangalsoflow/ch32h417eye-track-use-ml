"""
Verify the IDCT fix with correct table indexing.
"""
import numpy as np
import cv2

# MCU's cosine table (transposed version)
COS_TABLE_MCU = [
    [ 16384,  16069,  15137,  13623,  11585,   9102,   6270,   3197],
    [ 16069,  13623,   6270,  -3197, -11585, -15137, -16069, -13623],
    [ 15137,   6270,  -9102, -16069, -13623,   3197,  16069,  11585],
    [ 13623,  -3197, -16069, -11585,   6270,  16069,   9102, -15137],
    [ 11585, -11585, -13623,   6270,  16069,   3197, -15137,  -9102],
    [  9102, -15137,   3197,  16069,  -6270, -13623,  11585,   6270],
    [  6270, -16069,  16069,  -9102, -15137,  11585,   3197, -13623],
    [  3197, -13623,  11585, -15137,  -9102,   6270,  16069, -16069]
]

# Correct cosine table
COS_TABLE_CORRECT = []
for i in range(8):
    row = []
    for j in range(8):
        val = int(16384 * np.cos((2*i + 1) * j * np.pi / 16))
        row.append(val)
    COS_TABLE_CORRECT.append(row)

def idct_with_table(coeffs, cos_table):
    """IDCT with specified cosine table"""
    temp = [0] * 64
    # Row transform
    for i in range(8):
        for j in range(8):
            s = 0
            for k in range(8):
                c = coeffs[i * 8 + k]
                if k == 0:
                    c = (c * 11585) >> 14
                s += cos_table[j][k] * c
            temp[i * 8 + j] = s >> 14
    
    # Column transform
    out = [0] * 64
    for j in range(8):
        for i in range(8):
            s = 0
            for k in range(8):
                c = temp[k * 8 + j]
                if k == 0:
                    c = (c * 11585) >> 14
                s += cos_table[i][k] * c
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[i * 8 + j] = val
    return out

def idct_with_transposed(coeffs, cos_table):
    """IDCT with transposed indexing"""
    temp = [0] * 64
    # Row transform
    for i in range(8):
        for j in range(8):
            s = 0
            for k in range(8):
                c = coeffs[i * 8 + k]
                if k == 0:
                    c = (c * 11585) >> 14
                s += cos_table[k][j] * c
            temp[i * 8 + j] = s >> 14
    
    # Column transform
    out = [0] * 64
    for j in range(8):
        for i in range(8):
            s = 0
            for k in range(8):
                c = temp[k * 8 + j]
                if k == 0:
                    c = (c * 11585) >> 14
                s += cos_table[k][i] * c
            val = (s >> 14) + 128
            if val < 0: val = 0
            if val > 255: val = 255
            out[i * 8 + j] = val
    return out

# Test with DC=-341
test_coeffs = [-341] + [0] * 63

print("=== Test: DC=-341, AC=0 ===")
print(f"Expected: all 85 (DC/8 + 128 = -341/8 + 128 = 85.375)")

out1 = idct_with_table(test_coeffs, COS_TABLE_MCU)
print(f"MCU table, normal indexing: {[out1[i*8] for i in range(8)]}")

out2 = idct_with_transposed(test_coeffs, COS_TABLE_MCU)
print(f"MCU table, transposed indexing: {[out2[i*8] for i in range(8)]}")

out3 = idct_with_table(test_coeffs, COS_TABLE_CORRECT)
print(f"Correct table, normal indexing: {[out3[i*8] for i in range(8)]}")

out4 = idct_with_transposed(test_coeffs, COS_TABLE_CORRECT)
print(f"Correct table, transposed indexing: {[out4[i*8] for i in range(8)]}")

# Check if MCU table = transpose of correct table
print("\n=== Is MCU table the transpose of correct table? ===")
is_transpose = True
for i in range(8):
    for j in range(8):
        if COS_TABLE_MCU[i][j] != COS_TABLE_CORRECT[j][i]:
            is_transpose = False
            print(f"  Mismatch at [{i}][{j}]: MCU={COS_TABLE_MCU[i][j]}, correct[{j}][{i}]={COS_TABLE_CORRECT[j][i]}")
            break
    if not is_transpose:
        break

if is_transpose:
    print("  Yes! MCU table is the transpose of correct table.")
    print("  So using transposed indexing with MCU table should work.")
else:
    print("  No, MCU table is not simply the transpose.")
    print("\n  Let's check if MCU table = correct table (not transposed):")
    is_same = True
    for i in range(8):
        for j in range(8):
            if COS_TABLE_MCU[i][j] != COS_TABLE_CORRECT[i][j]:
                is_same = False
                break
        if not is_same:
            break
    if is_same:
        print("  Yes! MCU table equals correct table.")
    else:
        print("  No, they're different.")
