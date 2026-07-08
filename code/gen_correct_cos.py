"""
Generate the correct cosine table for JPEG IDCT.
"""
import numpy as np

print("// Correct JPEG IDCT cosine table")
print("// cos_table[i][j] = round(16384 * cos((2*i+1)*j*pi/16))")
print("static const int cos_table[8][8] = {")
for i in range(8):
    row = []
    for j in range(8):
        val = int(round(16384 * np.cos((2*i + 1) * j * np.pi / 16)))
        row.append(val)
    row_str = ", ".join(f"{v:6d}" for v in row)
    print(f"    {{ {row_str} }},")
print("};")
