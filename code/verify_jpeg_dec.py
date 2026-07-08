import serial
import cv2
import numpy as np
import sys
import time



def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_jpeg_dec.py <com_port> <jpeg_file>")
        print("Example: python verify_jpeg_dec.py COM3 test.jpg")
        return
    
    port = sys.argv[1]
    jpeg_file = sys.argv[2]
    
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(1)
    
    with open(jpeg_file, 'rb') as f:
        jpeg_data = f.read()
    
    print(f"JPEG file: {jpeg_file}, size: {len(jpeg_data)} bytes")
    
    img_ref = cv2.imread(jpeg_file, cv2.IMREAD_GRAYSCALE)
    if img_ref is None:
        print("Failed to read JPEG with OpenCV")
        return
    h_ref, w_ref = img_ref.shape
    print(f"OpenCV decoded: {w_ref}x{h_ref}")
    
    print("Sending JPEG to MCU...")
    ser.write(jpeg_data)
    
    print("Waiting for MCU response...")
    response = b""
    expected_size = w_ref * h_ref
    
    start_time = time.time()
    while len(response) < expected_size:
        if time.time() - start_time > 30:
            print("Timeout waiting for pixels")
            break
        data = ser.read(expected_size - len(response))
        if data:
            response += data
    
    if len(response) == expected_size:
        print(f"Received {len(response)} pixels")
        mcu_pixels = np.frombuffer(response, dtype=np.uint8).reshape(h_ref, w_ref)
        
        diff = cv2.absdiff(img_ref, mcu_pixels)
        avg_diff = np.mean(diff)
        max_diff = np.max(diff)
        
        print(f"\nComparison results:")
        print(f"  Average difference: {avg_diff:.2f}")
        print(f"  Max difference: {max_diff}")
        print(f"  Pixels with diff < 5: {np.sum(diff < 5) / diff.size * 100:.1f}%")
        print(f"  Pixels with diff < 10: {np.sum(diff < 10) / diff.size * 100:.1f}%")
        
        cv2.imshow("OpenCV decode", img_ref)
        cv2.imshow("MCU decode", mcu_pixels)
        cv2.imshow("Difference (x10)", diff * 10)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"Expected {expected_size} pixels, got {len(response)}")
    
    ser.close()

if __name__ == "__main__":
    main()
