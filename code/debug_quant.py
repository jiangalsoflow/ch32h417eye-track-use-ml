"""
Debug quantization and inverse quantization.
"""
import numpy as np
import cv2

# Read UART output to get MCU's quant table
with open(r'E:\dvp-uart\Match\code\uart_return.txt', 'r') as f:
    uart_data = f.read()

# Extract quant table from diagnostic
import re
qt_match = re.search(r'Quant table\[0\]: min=(\d+), max=(\d+), mean=([\d.]+)', uart_data)
if qt_match:
    print(f"MCU Quant table: min={qt_match.group(1)}, max={qt_match.group(2)}, mean={qt_match.group(3)}")

# Extract DC coefficients
dc_match = re.search(r'Raw DC coeffs \(dequantized, first 8 blocks\): \[([^\]]+)\]', uart_data)
if dc_match:
    dc_vals = [int(x.strip()) for x in dc_match.group(1).split(',')]
    print(f"MCU DC coeffs (first 8): {dc_vals}")

# Extract Huffman categories
cat_match = re.search(r'Huffman categories \(first 8 DCs\): \[([^\]]+)\]', uart_data)
if cat_match:
    cat_vals = [int(x.strip()) for x in cat_match.group(1).split(',')]
    print(f"MCU Huffman categories (first 8): {cat_vals}")

# Extract raw bit values
raw_match = re.search(r'Raw bit values \(first 8 DCs\): \[([^\]]+)\]', uart_data)
if raw_match:
    raw_vals = [int(x.strip()) for x in raw_match.group(1).split(',')]
    print(f"MCU raw bit values (first 8): {raw_vals}")

# Now decode the JPEG with Python to compare
with open(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', 'rb') as f:
    jpeg_data = f.read()

# Parse JPEG markers
pos = 2
markers = {}
while pos < len(jpeg_data) - 1:
    if jpeg_data[pos] != 0xFF:
        pos += 1
        continue
    
    marker = (jpeg_data[pos] << 8) | jpeg_data[pos + 1]
    pos += 2
    
    if marker == 0xFFD9:
        break
    if marker == 0xFF00 or (0xFFD0 <= marker <= 0xFFD7):
        continue
    
    length = (jpeg_data[pos] << 8) | jpeg_data[pos + 1]
    
    if marker == 0xFFDB:  # DQT
        info = jpeg_data[pos + 2]
        qid = info & 0xF
        qt = list(jpeg_data[pos + 3:pos + 67])
        markers[f'DQT_{qid}'] = qt
        print(f"\nPython Quant table {qid}: min={min(qt)}, max={max(qt)}, mean={np.mean(qt):.1f}")
        print(f"  First 16 values: {qt[:16]}")
    
    if marker == 0xFFDA:  # SOS
        # Compressed data starts after SOS header
        sos_end = pos + length
        markers['compressed_start'] = sos_end
        break
    
    pos += length

# Decode with Python
print("\n=== Python Full Decode ===")
from full_decode import full_decode
py_result = full_decode(jpeg_data)

print(f"Python DC coeffs (first 8): {py_result['dc_coeffs'][:8]}")
print(f"Python output: min={py_result['output'].min()}, max={py_result['output'].max()}, mean={py_result['output'].mean():.1f}")

# Compare with OpenCV
ref = cv2.imread(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', cv2.IMREAD_GRAYSCALE)
diff = np.abs(py_result['output'].astype(int) - ref.astype(int))
print(f"\nPython vs OpenCV: mean={diff.mean():.2f}, max={diff.max()}")

# Check first block details
print(f"\n=== First Block Analysis ===")
print(f"Python first block DC coeff: {py_result['dc_coeffs'][0]}")
print(f"Python first block output mean: {py_result['output'][0:8, 0:8].mean():.1f}")
print(f"OpenCV first block mean: {ref[0:8, 0:8].mean():.1f}")

# The issue might be in how DC coefficients are accumulated
print(f"\n=== DC Accumulation Check ===")
print(f"First 8 DC diffs (should be small): {[py_result['dc_coeffs'][i] - py_result['dc_coeffs'][i-1] for i in range(1, 8)]}")
