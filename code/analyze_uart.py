import numpy as np
from PIL import Image
import sys

def main():
    try:
        data = open(r'E:\dvp-uart\Match\code\uart_return.txt', 'rb').read()
    except FileNotFoundError:
        print("ERROR: uart_return.txt not found!")
        sys.exit(1)

    print(f"File size: {len(data)} bytes")
    print("=" * 60)

    # --- Find text lines ---
    def find_text(marker):
        idx = data.find(marker)
        if idx < 0:
            return None
        end = data.find(b'\r\n', idx)
        if end < 0:
            end = idx + 100
        return data[idx:end].decode('utf-8', errors='replace').strip()

    # --- Find binary section ---
    def find_section(start_marker, end_marker):
        s = data.find(start_marker)
        if s < 0:
            return None
        s += len(start_marker)
        e = data.find(end_marker, s)
        if e < 0:
            return None
        return data[s:e]

    # --- Parse text status ---
    print("\n[Status Lines]")
    for marker in [b'V5F SystemCoreClk:', b'JPEG data size:', b'Decode time:',
                   b'DTCM .bss used:', b'jpeg_dec_buf @',
                   b'Decode OK:', b'Decode failed:', b'Done']:
        val = find_text(marker)
        if val:
            print(f"  {val}")

    # --- Check firmware version ---
    has_diag = find_text(b'Decode time:') is not None
    if not has_diag:
        print("\n[WARNING] Old firmware detected (no diagnostic output)")
        print("Please recompile and flash the new firmware.")

    # --- Diagnostic section ---
    diag = find_section(b'DIAG_START\r\n', b'\r\nDIAG_END')
    W, H = 0, 0
    if diag:
        print("\n[Diagnostic]")
        for line in diag.split(b'\r\n'):
            if not line:
                continue
            try:
                if line.startswith(b'W:'):
                    parts = line.decode().split()
                    W = int(parts[0].split(':')[1])
                    H = int(parts[1].split(':')[1])
                    nc = int(parts[2].split(':')[1]) if len(parts) > 2 else 0
                    hmax = int(parts[3].split(':')[1]) if len(parts) > 3 else 1
                    vmax = int(parts[4].split(':')[1]) if len(parts) > 4 else 1
                    print(f"  Image: {W}x{H}, Components: {nc}, Hmax: {hmax}, Vmax: {vmax}")
                elif line.startswith(b'COMP'):
                    print(f"  {line.decode()}")
                elif line.startswith(b'QT0:'):
                    vals = [int(x) for x in line[4:].split(b',') if x]
                    print(f"  Quant table[0]: min={min(vals)}, max={max(vals)}, mean={np.mean(vals):.1f}")
                elif line.startswith(b'DCBITS0:'):
                    vals = [int(x) for x in line[8:].split(b',') if x]
                    total = sum(vals)
                    print(f"  DC Huffman bits[0]: {vals} (total entries: {total})")
                elif line.startswith(b'ACBITS0:'):
                    vals = [int(x) for x in line[8:].split(b',') if x]
                    total = sum(vals)
                    print(f"  AC Huffman bits[0]: {vals} (total entries: {total})")
                elif line.startswith(b'RAW_DC:'):
                    vals = [int(x) for x in line[7:].split(b',') if x]
                    print(f"  Raw DC coeffs (dequantized, first 8 blocks): {vals}")
                elif line.startswith(b'DC_CAT:'):
                    vals = [int(x) for x in line[7:].split(b',') if x]
                    print(f"  Huffman categories (first 8 DCs): {vals}")
                elif line.startswith(b'DC_VAL:'):
                    vals = [int(x) for x in line[7:].split(b',') if x]
                    print(f"  Raw bit values (first 8 DCs): {vals}")
                elif line.startswith(b'DC_SAMPLE:'):
                    vals = [int(x) for x in line[10:].split(b',') if x]
                    print(f"  DC samples (first 8 block DCs): {vals}")
                elif line.startswith(b'COMP_DATA_328:'):
                    vals = line[13:].split()
                    hex_vals = [v.decode() for v in vals[:16]]
                    print(f"  Compressed data @328: {' '.join(hex_vals)}")
                elif line.startswith(b'BITSTREAM:'):
                    vals = line[10:].split()
                    hex_vals = [v.decode() for v in vals]
                    print(f"  Bitstream (first 32 bits): {' '.join(hex_vals)}")
                elif line.startswith(b'BLOCK_BITS:'):
                    vals = [int(x) for x in line[11:].split(b',') if x]
                    print(f"  Bits per block (first 8): {vals}")
                elif line.startswith(b'DC_BITS:'):
                    vals = [int(x) for x in line[8:].split(b',') if x]
                    print(f"  DC bits per block (first 8): {vals}")
                elif line.startswith(b'AC_BITS:'):
                    vals = [int(x) for x in line[8:].split(b',') if x]
                    print(f"  AC bits per block (first 8): {vals}")
                elif line.startswith(b'PIXEL_CHECK:'):
                    vals = [int(x) for x in line[12:].split(b',') if x]
                    print(f"  MCU first pixels (3 rows x 10 cols):")
                    for r in range(3):
                        row_vals = vals[r*10:(r+1)*10]
                        print(f"    Row {r}: {row_vals}")
            except Exception as e:
                print(f"  [parse error: {e}]")
    else:
        print("\n[Diagnostic] Not found")

    # --- Extract JPEG ---
    jpeg_data = find_section(b'JPEG_START\r\n', b'\r\nJPEG_END')
    ref = None
    if jpeg_data:
        print(f"\n[JPEG] Received {len(jpeg_data)} bytes")
        try:
            # Decode JPEG using PIL to get reference
            from PIL import Image
            import io
            ref_img = Image.open(io.BytesIO(jpeg_data)).convert('L')
            ref = np.array(ref_img)
            print(f"  Reference (PIL decode): {ref.shape}, min={ref.min()}, max={ref.max()}, mean={ref.mean():.1f}")
            ref_img.save(r'E:\dvp-uart\Match\code\reference.png')
        except Exception as e:
            print(f"  [Error loading reference: {e}]")
    else:
        print("\n[JPEG] Marker not found, scanning for SOI...")
        # Scan for JPEG SOI marker (0xFF 0xD8)
        soi_idx = data.find(b'\xff\xd8')
        if soi_idx >= 0:
            # Find EOI marker (0xFF 0xD9)
            eoi_idx = data.find(b'\xff\xd9', soi_idx)
            if eoi_idx >= 0:
                jpeg_data = data[soi_idx:eoi_idx+2]
                print(f"  Found JPEG at offset {soi_idx}, length {len(jpeg_data)} bytes")
                try:
                    from PIL import Image
                    import io
                    ref_img = Image.open(io.BytesIO(jpeg_data)).convert('L')
                    ref = np.array(ref_img)
                    print(f"  Reference (PIL decode): {ref.shape}, min={ref.min()}, max={ref.max()}, mean={ref.mean():.1f}")
                    ref_img.save(r'E:\dvp-uart\Match\code\reference.png')
                except Exception as e:
                    print(f"  [Error loading reference: {e}]")

    # --- Analyze pixel data ---
    if jpeg_data:
        # Properly extract pixel data using find_section
        pixel_data = find_section(b'PIXEL_START\r\n', b'\r\nPIXEL_END')
        if pixel_data is None:
            print("\n[Pixel] PIXEL_START marker not found, trying fallback...")
            # Fallback: scan for pixel data after JPEG_END
            jpeg_end_idx = data.find(b'\r\nJPEG_END\r\n')
            if jpeg_end_idx >= 0:
                pixel_start_idx = data.find(b'PIXEL_START\r\n', jpeg_end_idx)
                if pixel_start_idx >= 0:
                    pixel_data_start = pixel_start_idx + len(b'PIXEL_START\r\n')
                    pixel_end_idx = data.find(b'\r\nPIXEL_END', pixel_data_start)
                    if pixel_end_idx >= 0:
                        pixel_data = data[pixel_data_start:pixel_end_idx]
        
        if pixel_data:
            print(f"\n[Pixel] Extracted {len(pixel_data)} bytes")
            print(f"  First 32 bytes: {pixel_data[:32].hex()}")
            
            # Try to interpret as pixels
            if len(pixel_data) >= 480000:
                pixel_bytes = pixel_data[:480000]
                img = np.frombuffer(pixel_bytes, dtype=np.uint8).reshape((600, 800))
                print(f"\n  As 800x600 image:")
                print(f"    Min: {img.min()}, Max: {img.max()}, Mean: {img.mean():.1f}")
                unique_vals = len(np.unique(img))
                print(f"    Unique values: {unique_vals}")
                
                # Check if it's a gradient
                first_row = img[0, :]
                is_gradient = np.all(np.diff(first_row[:100]) > 0) or np.all(np.diff(first_row[:100]) < 0)
                print(f"    First row looks like gradient: {is_gradient}")
                print(f"    First row samples: {first_row[::100]}")
                
                Image.fromarray(img).save(r'E:\dvp-uart\Match\code\remaining_as_image.png')
                print(f"  Saved as remaining_as_image.png")
                
                if ref is not None and ref.shape == img.shape:
                    diff = np.abs(img.astype(int) - ref.astype(int))
                    print(f"\n  Diff vs reference: mean={diff.mean():.2f}, max={diff.max()}")
                    for threshold in [5, 10, 20, 50]:
                        pct = np.sum(diff < threshold) * 100 / 480000
                        print(f"    Pixels with diff < {threshold}: {pct:.1f}%")
                    
                    # Check for horizontal shift by comparing first few rows
                    print(f"\n  Horizontal alignment check:")
                    # Compare first pixels
                    print(f"  MCU first pixels (3 rows x 10 cols):")
                    for r in range(3):
                        mcu_row_pixels = img[r, :10].tolist()
                        print(f"    Row {r}: {mcu_row_pixels}")
                    print(f"  Reference first pixels (3 rows x 10 cols):")
                    for r in range(3):
                        ref_row = ref[r, :10].tolist()
                        print(f"    Row {r}: {ref_row}")
                    
                    for y in [0, 100, 300, 500]:
                        mcu_row = img[y, :]
                        ref_row = ref[y, :]
                        # Find best match by cross-correlation
                        best_shift = 0
                        best_corr = -1
                        for shift in range(-50, 51):
                            if shift >= 0:
                                corr = np.corrcoef(mcu_row[shift:], ref_row[:-shift] if shift > 0 else ref_row)[0, 1]
                            else:
                                corr = np.corrcoef(mcu_row[:shift], ref_row[-shift:])[0, 1]
                            if not np.isnan(corr) and corr > best_corr:
                                best_corr = corr
                                best_shift = shift
                        print(f"    Row {y}: best shift = {best_shift} pixels (correlation = {best_corr:.3f})")
            else:
                print(f"  [ERROR] Pixel data too short: {len(pixel_data)} bytes (expected 480000)")
        else:
            print("\n[Pixel] Could not extract pixel data")

    print("\n" + "=" * 60)
    print("Analysis complete.")

if __name__ == '__main__':
    main()
