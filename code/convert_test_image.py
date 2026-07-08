"""
Convert a test image to C array for MCU testing.
"""
import sys

def jpg_to_c_array(jpg_path, c_path, array_name="test_jpeg_data"):
    with open(jpg_path, 'rb') as f:
        data = f.read()
    
    with open(c_path, 'w') as f:
        f.write(f'#include "{c_path.split("/")[-1].replace(".c", ".h")}"\n\n')
        f.write(f'const unsigned char {array_name}[] = {{\n')
        
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = ', '.join(f'0x{b:02X}' for b in chunk)
            f.write(f'    {hex_str},\n')
        
        f.write('};\n\n')
        f.write(f'const unsigned long {array_name.replace("data", "size")} = {len(data)};\n')
    
    print(f"Converted {jpg_path} ({len(data)} bytes) to {c_path}")
    return len(data)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        jpg_path = sys.argv[1]
    else:
        jpg_path = r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg'
    
    c_path = r'E:\dvp-uart\Match\CH32H417\sdk_ch32h417\DVP\DVP_UART_Test2.1\Common\test_image.c'
    
    size = jpg_to_c_array(jpg_path, c_path)
    print(f"\nArray size: {size} bytes")
    print(f"Update test_image.h if needed:")
    print(f'  extern const unsigned char test_jpeg_data[];')
    print(f'  extern const unsigned int test_jpeg_size;')
