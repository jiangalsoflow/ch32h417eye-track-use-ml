"""
Huffman decoder reproduction script for debugging MCU JPEG decoder.

This script reproduces the exact Huffman table building and decoding logic
from jpeg_dec.c to find the bug causing wrong DC categories.
"""

import numpy as np
import cv2
import struct

# Load the test JPEG
with open(r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg', 'rb') as f:
    jpeg_data = f.read()

print(f"JPEG size: {len(jpeg_data)} bytes")

# MCU diagnostic output (indices 0-15, but we use 1-16)
mcu_dc_bits = [0, 0, 1, 5, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0]  # 17 elements, index 0 unused
mcu_ac_bits = [0, 0, 2, 1, 3, 3, 2, 4, 3, 5, 5, 4, 4, 0, 0, 1, 125]  # 17 elements, index 0 unused

print("\n=== MCU Diagnostic ===")
print(f"DC bits: {mcu_dc_bits}")
print(f"AC bits: {mcu_ac_bits}")
print(f"DC entries: {sum(mcu_dc_bits)}")
print(f"AC entries: {sum(mcu_ac_bits)}")

# Reproduce huff_build() from jpeg_dec.c
class HuffTable:
    def __init__(self):
        self.bits = [0] * 17  # bits[0] unused, bits[1..16]
        self.huffval = [0] * 256
        self.maxcode = [0] * 17  # maxcode[0] unused
        self.valptr = [0] * 17   # valptr[0] unused
        self.ready = False

def huff_build_c(bits, huffval):
    """Exact reproduction of huff_build() from jpeg_dec.c"""
    ht = HuffTable()
    ht.bits = bits[:]
    ht.huffval = huffval[:]
    
    k = 0
    code = 0
    for i in range(1, 17):
        ht.valptr[i] = k
        ht.maxcode[i] = 0xFFFF  # -1 as UINT16
        if ht.bits[i] > 0:
            ht.maxcode[i] = code + ht.bits[i] - 1
            code += ht.bits[i]
            k += ht.bits[i]
        code <<= 1
    
    ht.ready = True
    return ht

# Standard JPEG DC luminance huffval (from JPEG spec)
dc_huffval = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]

# Standard JPEG AC luminance huffval (from JPEG spec)
ac_huffval = [
    0x01, 0x02, 0x03, 0x00, 0x04, 0x11, 0x05, 0x12,
    0x21, 0x31, 0x41, 0x06, 0x13, 0x51, 0x61, 0x07,
    0x22, 0x71, 0x14, 0x32, 0x81, 0x91, 0xa1, 0x08,
    0x23, 0x42, 0xb1, 0xc1, 0x15, 0x52, 0xd1, 0xf0,
    0x24, 0x33, 0x62, 0x72, 0x82, 0x09, 0x0a, 0x16,
    0x17, 0x18, 0x19, 0x1a, 0x25, 0x26, 0x27, 0x28,
    0x29, 0x2a, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
    0x3a, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49,
    0x4a, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59,
    0x5a, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,
    0x6a, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79,
    0x7a, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89,
    0x8a, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98,
    0x99, 0x9a, 0xa2, 0xa3, 0xa4, 0xa5, 0xa6, 0xa7,
    0xa8, 0xa9, 0xaa, 0xb2, 0xb3, 0xb4, 0xb5, 0xb6,
    0xb7, 0xb8, 0xb9, 0xba, 0xc2, 0xc3, 0xc4, 0xc5,
    0xc6, 0xc7, 0xc8, 0xc9, 0xca, 0xd2, 0xd3, 0xd4,
    0xd5, 0xd6, 0xd7, 0xd8, 0xd9, 0xda, 0xe1, 0xe2,
    0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8, 0xe9, 0xea,
    0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7, 0xf8,
    0xf9, 0xfa
]

print("\n=== Building Huffman Tables (C algorithm) ===")
dc_tab = huff_build_c(mcu_dc_bits, dc_huffval)
ac_tab = huff_build_c(mcu_ac_bits, ac_huffval)

print("\nDC Table:")
print(f"  valptr: {dc_tab.valptr[1:17]}")
print(f"  maxcode: {[hex(x) for x in dc_tab.maxcode[1:17]]}")
print(f"  maxcode (decimal): {dc_tab.maxcode[1:17]}")

print("\nAC Table:")
print(f"  valptr: {ac_tab.valptr[1:17]}")
print(f"  maxcode: {[hex(x) for x in ac_tab.maxcode[1:17]]}")

# Reproduce huff_decode() from jpeg_dec.c
class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.bit_buf = 0
        self.bit_cnt = 0
        self.total_bits_read = 0
    
    def read_bit(self):
        if self.bit_cnt == 0:
            if self.pos >= len(self.data):
                return -1
            self.bit_buf = self.data[self.pos]
            self.pos += 1
            # Handle byte stuffing
            if self.bit_buf == 0xFF and self.pos < len(self.data) and self.data[self.pos] == 0x00:
                self.pos += 1
            self.bit_cnt = 8
        self.bit_cnt -= 1
        self.total_bits_read += 1
        return (self.bit_buf >> self.bit_cnt) & 1
    
    def read_bits(self, n):
        val = 0
        for _ in range(n):
            b = self.read_bit()
            if b < 0:
                return -1
            val = (val << 1) | b
        return val

def huff_decode_c(reader, ht, debug=False):
    """Exact reproduction of huff_decode() from jpeg_dec.c"""
    code = 0
    for i in range(1, 17):
        b = reader.read_bit()
        if b < 0:
            return -1
        code = (code << 1) | b
        if debug:
            print(f"    i={i}, bit={b}, code={code} (0b{code:b}), maxcode[{i}]={ht.maxcode[i]}, bits[{i}]={ht.bits[i]}")
        if ht.bits[i] > 0 and code <= ht.maxcode[i]:
            # Calculate index
            mincode = ht.maxcode[i] - ht.bits[i] + 1
            idx = ht.valptr[i] + (code - mincode)
            if debug:
                print(f"    MATCH! mincode={mincode}, idx={idx}, huffval={ht.huffval[idx]}")
            return ht.huffval[idx]
    if debug:
        print(f"    NO MATCH after 16 bits!")
    return -999

# Parse JPEG to find SOS marker and extract compressed data
def parse_jpeg_markers(data):
    pos = 0
    markers = []
    
    # Skip SOI
    if data[0:2] != b'\xFF\xD8':
        print("Not a JPEG file!")
        return None
    pos = 2
    
    while pos < len(data) - 1:
        if data[pos] != 0xFF:
            pos += 1
            continue
        
        marker = (data[pos] << 8) | data[pos + 1]
        pos += 2
        
        if marker == 0xFFD9:  # EOI
            markers.append(('EOI', pos, None))
            break
        
        if marker == 0xFF00 or (marker >= 0xFFD0 and marker <= 0xFFD7):
            continue  # Stuffed byte or RST marker
        
        # Read length
        if pos + 2 > len(data):
            break
        length = (data[pos] << 8) | data[pos + 1]
        
        marker_name = {
            0xFFC0: 'SOF0',
            0xFFC4: 'DHT',
            0xFFDA: 'SOS',
            0xFFDB: 'DQT',
            0xFFDD: 'DRI',
            0xFFE0: 'APP0',
        }.get(marker, f'0x{marker:04X}')
        
        marker_data = data[pos + 2:pos + length]
        markers.append((marker_name, pos, marker_data))
        
        if marker == 0xFFDA:  # SOS - compressed data follows
            # Compressed data starts right after the SOS header
            sos_end = pos + length
            # Find EOI
            eoi_pos = data.find(b'\xFF\xD9', sos_end)
            if eoi_pos == -1:
                eoi_pos = len(data)
            markers.append(('COMPRESSED_DATA', sos_end, data[sos_end:eoi_pos]))
            markers.append(('EOI', eoi_pos, None))
            break
        
        pos += length
    
    return markers

print("\n=== Parsing JPEG Markers ===")
markers = parse_jpeg_markers(jpeg_data)
for name, pos, data in markers:
    if name == 'COMPRESSED_DATA':
        print(f"{name}: pos={pos}, size={len(data)} bytes")
    elif data:
        print(f"{name}: pos={pos}, size={len(data)} bytes")
    else:
        print(f"{name}: pos={pos}")

# Find SOS marker and extract compressed data
sos_data = None
for name, pos, mdata in markers:
    if name == 'SOS':
        # Parse SOS header
        n_comp = mdata[0]
        print(f"\nSOS: {n_comp} components")
        for i in range(n_comp):
            comp_id = mdata[1 + i * 2]
            tab = mdata[2 + i * 2]
            dc_tab_id = tab >> 4
            ac_tab_id = tab & 0xF
            print(f"  Component {comp_id}: DC table {dc_tab_id}, AC table {ac_tab_id}")
        break

# Find compressed data
for name, pos, mdata in markers:
    if name == 'COMPRESSED_DATA':
        sos_data = mdata
        break

if sos_data is None:
    print("ERROR: Could not find compressed data!")
    exit(1)

print(f"\nCompressed data size: {len(sos_data)} bytes")

# Parse DHT markers to get actual Huffman tables from the JPEG file
print("\n=== Parsing DHT Markers ===")
for name, pos, mdata in markers:
    if name == 'DHT':
        info = mdata[0]
        cls = (info >> 4) & 0xF
        tab_id = info & 0xF
        bits = [0] + list(mdata[1:17])  # bits[1..16]
        total = sum(bits)
        huffval = list(mdata[17:17+total])
        print(f"DHT at pos {pos}: class={cls} id={tab_id}")
        print(f"  bits[1..16]: {bits[1:]}")
        print(f"  total entries: {total}")
        print(f"  huffval (first 16): {[hex(v) for v in huffval[:16]]}")
        
        # Build table and show maxcode/valptr
        ht = huff_build_c(bits, huffval)
        print(f"  valptr: {ht.valptr[1:17]}")
        print(f"  maxcode: {[hex(x) for x in ht.maxcode[1:17]]}")

# Show first 32 bytes of compressed data
print(f"\n=== First 32 bytes of compressed data ===")
print(f"Hex: {sos_data[:32].hex()}")
print(f"Binary:")
for i in range(min(16, len(sos_data))):
    print(f"  byte {i}: 0x{sos_data[i]:02X} = {sos_data[i]:08b}")

# Full decode with bit position tracking
print("\n=== Full Decode with Bit Tracking ===")
reader = BitReader(sos_data)

# First, dump the first 32 bits of compressed data
print("\nFirst 32 bits of compressed data:")
bits_dump = []
for i in range(32):
    b = reader.read_bit()
    bits_dump.append(b)
print(f"  Bits: {''.join(str(b) for b in bits_dump)}")
print(f"  As bytes: {bytes([int(''.join(str(b) for b in bits_dump[i*8:(i+1)*8]), 2) for i in range(4)]).hex()}")

# Reset reader
reader = BitReader(sos_data)

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

def decode_ac_full(reader, ht, block_idx):
    """Decode AC coefficients, return (coeffs, bits_consumed)"""
    coeffs = [0] * 64
    k = 1
    ac_bits = 0
    while k < 64:
        start_bit = reader.total_bits_read
        rs = huff_decode_c(reader, ht, debug=False)
        ac_bits += reader.total_bits_read - start_bit
        if rs < 0:
            print(f"  Block {block_idx} AC: decode error at k={k}")
            break
        if rs == 0:
            # EOB
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
        val = reader.read_bits(length)
        ac_bits += length
        if val < (1 << (length - 1)):
            val -= (1 << length) - 1
        coeffs[ZIGZAG[k]] = val
        k += 1
    return coeffs, ac_bits

prev_dc = 0
for block_idx in range(10):
    bits_before = reader.total_bits_read
    byte_pos = reader.pos
    bit_in_byte = 8 - reader.bit_cnt
    
    # Decode DC with detailed bit tracing for first 3 blocks
    if block_idx < 3:
        print(f"\n--- Block {block_idx} (starting at bit {bits_before}, byte~{byte_pos}) ---")
        # Trace DC decode bit by bit
        code = 0
        dc_cat = -1
        for i in range(1, 17):
            b = reader.read_bit()
            reader.total_bits_read  # already incremented in read_bit
            code = (code << 1) | b
            if dc_tab.bits[i] > 0 and code <= dc_tab.maxcode[i]:
                mincode = dc_tab.maxcode[i] - dc_tab.bits[i] + 1
                idx = dc_tab.valptr[i] + (code - mincode)
                dc_cat = dc_tab.huffval[idx]
                print(f"  DC decode: bits read = {i}, code = {code} (0b{code:b}), cat = {dc_cat}")
                break
        cat = dc_cat
    else:
        cat = huff_decode_c(reader, dc_tab, debug=False)
    
    dc_bits_used = reader.total_bits_read - bits_before
    
    if cat > 0:
        val = reader.read_bits(cat)
        dc_bits_used += cat
        if val < (1 << (cat - 1)):
            val -= (1 << cat) - 1
    else:
        val = 0
    
    prev_dc += val
    bits_after_dc = reader.total_bits_read
    
    if block_idx < 3:
        print(f"  DC value = {val}, prev_dc = {prev_dc}")
        print(f"  After DC: bit position = {bits_after_dc}")
    
    # Decode AC
    ac_coeffs, ac_bits_used = decode_ac_full(reader, ac_tab, block_idx)
    
    total_bits = reader.total_bits_read - bits_before
    nonzero_ac = sum(1 for c in ac_coeffs if c != 0)
    
    if block_idx < 3:
        print(f"  AC: {ac_bits_used} bits, nonzero = {nonzero_ac}")
        print(f"  After AC: bit position = {reader.total_bits_read}")
    
    print(f"Block {block_idx}: byte~{byte_pos}, cat={cat}, dc={val}, prev_dc={prev_dc}, "
          f"DC_bits={dc_bits_used}, AC_bits={ac_bits_used}, total={total_bits}, "
          f"nonzero_AC={nonzero_ac}")

print(f"\nTotal bits consumed: {reader.total_bits_read} ({reader.total_bits_read // 8} bytes)")
print(f"Total compressed data: {len(sos_data)} bytes")

# Compare with OpenCV decode
print("\n=== OpenCV Reference ===")
img_cv = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
print(f"OpenCV decode: {img_cv.shape}, min={img_cv.min()}, max={img_cv.max()}, mean={img_cv.mean():.1f}")

# Show first 8x8 block from OpenCV
print(f"\nFirst 8x8 block (OpenCV):")
print(img_cv[0:8, 0:8])

# Calculate what DC value should be for first block
first_block = img_cv[0:8, 0:8].astype(np.float64)
# Simple DCT to get DC coefficient
dc_coeff = np.sum(first_block - 128) / 8
print(f"\nExpected DC coefficient (approx): {dc_coeff:.1f}")
