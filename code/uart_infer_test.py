"""
PC-side script to parse UART output from MCU and compare inference results.
"""
import os; os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
import cv2
import tensorflow as tf
import re

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')
UART_FILE = os.path.join(os.path.dirname(__file__), 'uart_return.txt')

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

def find_section(data, start_marker, end_marker):
    start_idx = data.find(start_marker)
    if start_idx == -1:
        return None
    start_idx += len(start_marker)
    end_idx = data.find(end_marker, start_idx)
    if end_idx == -1:
        return None
    return data[start_idx:end_idx]

def parse_uart_output(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    result = {}
    
    # Parse status lines
    for line in data.split(b'\r\n'):
        line_str = line.decode('ascii', errors='ignore')
        if line_str.startswith('V5F SystemCoreClk:'):
            result['clock'] = int(line_str.split(':')[1])
        elif line_str.startswith('JPEG data size:'):
            result['jpeg_size'] = int(line_str.split(':')[1].split()[0])
        elif line_str.startswith('Decode time:'):
            result['decode_time'] = int(line_str.split(':')[1].split()[0])
        elif line_str.startswith('Decode OK:'):
            dims = line_str.split(':')[1]
            w, h = dims.split('x')
            result['width'] = int(w)
            result['height'] = int(h)
        elif line_str.startswith('Class:'):
            result['mcu_class'] = line_str.split(':')[1].strip()
        elif line_str.startswith('Infer time:'):
            result['infer_time'] = int(line_str.split(':')[1].split()[0])
    
    # Parse scores
    scores_match = re.search(b'Scores:([^\r\n]+)', data)
    if scores_match:
        scores_str = scores_match.group(1).decode('ascii')
        result['mcu_scores'] = {}
        for part in scores_str.strip().split():
            if '=' in part:
                name, val = part.split('=')
                result['mcu_scores'][name] = float(val)
    
    # Parse preprocessed values
    preproc_match = re.search(b'Preprocessed \(first 32\):([^\r\n]+)', data)
    if preproc_match:
        preproc_str = preproc_match.group(1).decode('ascii')
        result['mcu_preprocessed'] = [float(x) for x in preproc_str.strip().split()]
    
    # Extract JPEG
    jpeg_data = find_section(data, b'JPEG_START\r\n', b'\r\nJPEG_END')
    if jpeg_data:
        result['jpeg_data'] = jpeg_data
    
    # Extract pixels
    pixel_data = find_section(data, b'PIXEL_START\r\n', b'\r\nPIXEL_END')
    if pixel_data:
        result['pixel_data'] = pixel_data
    
    return result

def pc_inference(jpeg_data):
    model = tf.keras.models.load_model(MODEL_PATH)
    
    # Decode JPEG
    img_array = np.frombuffer(jpeg_data, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
    
    if img is None:
        return None, None
    
    # Resize to 32x32 using exact MCU nearest neighbor logic
    src_h, src_w = img.shape
    img_resized = np.zeros((32, 32), dtype=np.uint8)
    for y in range(32):
        for x in range(32):
            src_x = x * src_w // 32
            src_y = y * src_h // 32
            if src_x >= src_w: src_x = src_w - 1
            if src_y >= src_h: src_y = src_h - 1
            img_resized[y, x] = img[src_y, src_x]
    
    # Normalize to [0,1]
    img_normalized = img_resized.astype(np.float32) / 255.0
    
    # Replicate to 3 channels
    img_rgb = np.stack([img_normalized] * 3, axis=-1)
    
    # Run inference
    input_batch = np.expand_dims(img_rgb, 0)
    output = model.predict(input_batch, verbose=0)[0]
    
    best_idx = np.argmax(output)
    best_class = CLASSES[best_idx]
    
    scores = {CLASSES[i]: float(output[i]) for i in range(6)}
    
    # Get first 32 preprocessed values
    preprocessed = img_rgb.flatten()[:32].tolist()
    
    return best_class, scores, preprocessed, img_resized

def main():
    print("=" * 60)
    print("UART Inference Test")
    print("=" * 60)
    
    if not os.path.exists(UART_FILE):
        print(f"Error: {UART_FILE} not found")
        print("Please capture UART output to uart_return.txt first")
        return
    
    # Parse UART output
    print("\n[1] Parsing UART output...")
    result = parse_uart_output(UART_FILE)
    
    if 'jpeg_data' not in result:
        print("Error: No JPEG data found in UART output")
        return
    
    print(f"  JPEG size: {len(result['jpeg_data'])} bytes")
    print(f"  Image dimensions: {result.get('width', '?')}x{result.get('height', '?')}")
    print(f"  MCU class: {result.get('mcu_class', '?')}")
    print(f"  MCU infer time: {result.get('infer_time', '?')} ticks")
    
    if 'mcu_scores' in result:
        print(f"  MCU scores:")
        for cls in CLASSES:
            score = result['mcu_scores'].get(cls, 0)
            print(f"    {cls}: {score:.4f}")
    
    # PC inference
    print("\n[2] Running PC inference...")
    pc_class, pc_scores, pc_preprocessed, pc_img = pc_inference(result['jpeg_data'])
    
    if pc_class is None:
        print("Error: Failed to decode JPEG on PC")
        return
    
    print(f"  PC class: {pc_class}")
    print(f"  PC scores:")
    for cls in CLASSES:
        score = pc_scores.get(cls, 0)
        print(f"    {cls}: {score:.4f}")
    
    # Compare results
    print("\n[3] Comparison:")
    mcu_class = result.get('mcu_class', '')
    class_match = mcu_class == pc_class
    print(f"  Class match: {class_match} (MCU: {mcu_class}, PC: {pc_class})")
    
    if 'mcu_scores' in result:
        max_score_diff = 0
        for cls in CLASSES:
            mcu_score = result['mcu_scores'].get(cls, 0)
            pc_score = pc_scores.get(cls, 0)
            diff = abs(mcu_score - pc_score)
            max_score_diff = max(max_score_diff, diff)
        print(f"  Max score difference: {max_score_diff:.6f}")
    
    # Compare preprocessed values
    if 'mcu_preprocessed' in result and pc_preprocessed is not None:
        mcu_prep = np.array(result['mcu_preprocessed'])
        pc_prep = np.array(pc_preprocessed)
        prep_diff = np.abs(mcu_prep - pc_prep)
        print(f"  Preprocessed diff: mean={prep_diff.mean():.6f}, max={prep_diff.max():.6f}")
        print(f"  First 10 MCU values: {mcu_prep[:10]}")
        print(f"  First 10 PC values:  {pc_prep[:10]}")
    
    # Save PC reference image
    if pc_img is not None:
        cv2.imwrite(os.path.join(os.path.dirname(__file__), 'pc_reference.png'), pc_img)
        print(f"  Saved PC reference image: pc_reference.png")
    
    print("\n" + "=" * 60)
    if class_match:
        print("Result: PASS - MCU and PC inference match")
    else:
        print("Result: FAIL - MCU and PC inference differ")
    print("=" * 60)

if __name__ == '__main__':
    main()
