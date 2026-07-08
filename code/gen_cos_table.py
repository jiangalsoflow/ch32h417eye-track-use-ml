"""
Generate correct cosine table for MCU IDCT.
"""
import numpy as np

# Standard JPEG IDCT cosine table: cos((2*i+1)*j*pi/16)
# Scaled by 16384 (2^14) for fixed-point arithmetic
print("Correct cosine table for JPEG IDCT:")
print("cos_table[8][8] = {")
for i in range(8):
    row = []
    for j in range(8):
        val = int(16384 * np.cos((2*i + 1) * j * np.pi / 16))
        row.append(val)
    row_str = ", ".join(f"{v:6d}" for v in row)
    print(f"    {{ {row_str} }},")
print("};")

# Current MCU table
print("\nCurrent MCU table:")
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
for i in range(8):
    row_str = ", ".join(f"{v:6d}" for v in COS_TABLE_MCU[i])
    print(f"    {{ {row_str} }},")

# Compare
print("\nDifferences (correct - MCU):")
correct_table = []
for i in range(8):
    row = []
    for j in range(8):
        val = int(16384 * np.cos((2*i + 1) * j * np.pi / 16))
        row.append(val)
    correct_table.append(row)

for i in range(8):
    diffs = [correct_table[i][j] - COS_TABLE_MCU[i][j] for j in range(8)]
    print(f"Row {i}: {diffs}")

# Check if MCU table is transposed
print("\nIs MCU table transposed?")
is_transposed = True
for i in range(8):
    for j in range(8):
        if COS_TABLE_MCU[i][j] != correct_table[j][i]:
            is_transposed = False
            break
    if not is_transposed:
        break

if is_transposed:
    print("  Yes! MCU table is the transpose of the correct table.")
else:
    print("  No, MCU table is not simply transposed.")
    print("\nFirst few mismatches:")
    count = 0
    for i in range(8):
        for j in range(8):
            if COS_TABLE_MCU[i][j] != correct_table[i][j]:
                print(f"  [{i}][{j}]: MCU={COS_TABLE_MCU[i][j]}, correct={correct_table[i][j]}, diff={COS_TABLE_MCU[i][j] - correct_table[i][j]}")
                count += 1
                if count >= 10:
                    break
        if count >= 10:
            break
