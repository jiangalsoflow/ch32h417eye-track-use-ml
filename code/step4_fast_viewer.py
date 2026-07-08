import sys
import os
import numpy as np
import cv2
import serial
import time
import threading
import argparse
import datetime
import json
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

COLLECT_DIR = r'E:\dvp-uart\Match\collected_data\raw'
COORDS_FILE = r'E:\dvp-uart\Match\code\step4_fast_coords.json'
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')
SAVE_SEQ = [0]

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
CROP_SZ = 40

if os.path.exists(COORDS_FILE):
    with open(COORDS_FILE) as f:
        c = json.load(f)
    CROP_CX = c.get('cx', 170)
    CROP_CY = c.get('cy', 110)
else:
    CROP_CX = 170
    CROP_CY = 110


def parse_frame(frame_data):
    result = {}
    lines = frame_data.split(b'\r\n')
    for line in lines:
        s = line.decode('ascii', errors='ignore')
        if s.startswith('FRAME_NUM:'):
            result['frame_num'] = int(s.split(':')[1])
        elif s.startswith('JPEG_SIZE:'):
            result['jpeg_size'] = int(s.split(':')[1])
        elif s.startswith('DECODE_OK:'):
            dims = s.split(':')[1]
            w, h = dims.split('x')
            result['width'] = int(w)
            result['height'] = int(h)
        elif s.startswith('DECODE_FAIL:'):
            result['decode_fail'] = int(s.split(':')[1])
        elif s.startswith('CROP:'):
            parts = s.split(':')[1].split(',')
            result['crop_cx'] = int(parts[0])
            result['crop_cy'] = int(parts[1])
        elif s.startswith('CLASS:'):
            result['class'] = s.split(':')[1].strip()
        elif s.startswith('Infer time:'):
            result['infer_time'] = int(s.split(':')[1].split()[0])
        elif s.startswith('PREPROC_CKSUM:'):
            result['mcu_cksum'] = int(s.split(':')[1])

    scores = {}
    for line in lines:
        s = line.decode('ascii', errors='ignore')
        if s.startswith('SCORES:'):
            parts = s[7:].strip().split()
            for p in parts:
                if '=' in p:
                    name, val = p.split('=')
                    scores[name] = float(val)
    if scores:
        result['scores'] = scores

    jpeg_start = frame_data.find(b'JPEG_START\r\n')
    if jpeg_start != -1:
        jpeg_start += len(b'JPEG_START\r\n')
        jpeg_end = frame_data.find(b'\r\nJPEG_END', jpeg_start)
        if jpeg_end != -1:
            result['jpeg_data'] = frame_data[jpeg_start:jpeg_end]

    return result


def pc_preprocess_infer(jpeg_data, cx, cy, model):
    arr = np.frombuffer(jpeg_data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None, None
    h, w = img.shape
    half = CROP_SZ // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)
    crop = img[y1:y2, x1:x2]
    if crop.shape[0] < CROP_SZ or crop.shape[1] < CROP_SZ:
        crop = cv2.resize(crop, (CROP_SZ, CROP_SZ))
    crop = cv2.flip(crop, 1)
    eye_32 = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_NEAREST)
    eye_rgb = np.stack([eye_32] * 3, axis=-1).astype(np.float32) / 255.0
    inp = np.expand_dims(eye_rgb, 0)
    out = model.predict(inp, verbose=0)[0]
    best_idx = int(np.argmax(out))
    return out, best_idx, eye_32


class CompareViewer:
    def __init__(self, port='COM6', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.current_img = None
        self.current_class = ''
        self.current_scores = {}
        self.frame_num = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.crop_cx = CROP_CX
        self.crop_cy = CROP_CY
        self.pc_scores = {}
        self.pc_class = '?'
        self.pc_best_idx = -1
        self.mcu_cksum = 0
        self.agree = True
        self.model = None

    def load_model(self):
        print("Loading model...")
        self.model = tf.keras.models.load_model(MODEL_PATH)
        self.model.predict(np.zeros((1, 32, 32, 3), dtype=np.float32), verbose=0)
        print("Model loaded.")

    def serial_thread(self):
        ser = serial.Serial(self.port, self.baudrate, timeout=1)
        buf = bytearray()
        print(f"[Serial] Connected to {self.port} @ {self.baudrate}")
        while self.running:
            if ser.in_waiting > 0:
                buf.extend(ser.read(ser.in_waiting))
                while True:
                    start = buf.find(b'FRAME_START\r\n')
                    if start == -1:
                        if len(buf) > 200000:
                            buf = buf[-2000:]
                        break
                    end = buf.find(b'FRAME_END\r\n', start)
                    if end == -1:
                        break
                    frame_data = bytes(buf[start:end + len(b'FRAME_END\r\n')])
                    buf = buf[end + len(b'FRAME_END\r\n'):]
                    self.process_frame(frame_data)

    def process_frame(self, frame_data):
        result = parse_frame(frame_data)
        self.frame_num = result.get('frame_num', self.frame_num)
        self.mcu_cksum = result.get('mcu_cksum', 0)

        if 'class' in result:
            self.current_class = result['class']
        if 'scores' in result:
            self.current_scores = result['scores']
        if 'jpeg_data' in result:
            arr = np.frombuffer(result['jpeg_data'], dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                self.current_img = img
        if 'crop_cx' in result:
            self.crop_cx = result['crop_cx']
            self.crop_cy = result['crop_cy']

        if 'jpeg_data' in result and self.crop_cx > 0 and self.model is not None:
            out, best_idx, _ = pc_preprocess_infer(
                result['jpeg_data'], self.crop_cx, self.crop_cy, self.model)
            if out is not None:
                self.pc_scores = {CLASSES[i]: float(out[i]) for i in range(6)}
                self.pc_class = CLASSES[best_idx]
                self.pc_best_idx = best_idx

        self.agree = (self.current_class == self.pc_class)

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

        agree_str = "OK" if self.agree else "DIFF"
        print(f"[Frame {self.frame_num}] MCU={self.current_class} PC={self.pc_class} {agree_str} FPS={self.fps:.1f}")

    def orig_to_display(self, ox, oy):
        return oy, ox

    def save_eye_region(self):
        if self.current_img is None:
            return
        img = self.current_img
        cx, cy = self.crop_cx, self.crop_cy
        half = CROP_SZ // 2
        x1 = max(0, cx - half)
        y1 = max(0, cy - half)
        x2 = min(img.shape[1], cx + half)
        y2 = min(img.shape[0], cy + half)
        eye_region = img[y1:y2, x1:x2]
        if eye_region.size == 0:
            return
        eye_region = cv2.flip(eye_region, 1)
        eye_gray = cv2.cvtColor(eye_region, cv2.COLOR_BGR2GRAY)
        os.makedirs(COLLECT_DIR, exist_ok=True)
        SAVE_SEQ[0] += 1
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        fname = f"eye_{ts}_{SAVE_SEQ[0]:04d}.jpg"
        fpath = os.path.join(COLLECT_DIR, fname)
        cv2.imwrite(fpath, eye_gray, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"[SAVE] {fpath}  crop=({cx},{cy})")

    def save_crop_coords(self):
        with open(COORDS_FILE, 'w') as f:
            json.dump({'cx': self.crop_cx, 'cy': self.crop_cy}, f)
        print(f"[COORDS] Saved cx={self.crop_cx} cy={self.crop_cy}")

    def display_loop(self):
        cv2.namedWindow('Step4 + PC Compare', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Step4 + PC Compare', 600, 750)
        while self.running:
            canvas = np.zeros((750, 600, 3), dtype=np.uint8)

            img = self.current_img
            if img is not None:
                display = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                display = cv2.flip(display, 1)

                dcx, dcy = self.orig_to_display(self.crop_cx, self.crop_cy)
                half = CROP_SZ // 2
                x1 = dcx - half
                y1 = dcy - half
                x2 = dcx + half
                y2 = dcy + half

                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.line(display, (dcx - 5, dcy), (dcx + 5, dcy), (0, 0, 255), 1)
                cv2.line(display, (dcx, dcy - 5), (dcx, dcy + 5), (0, 0, 255), 1)

                dh, dw = display.shape[:2]
                display = cv2.resize(display, (240, 320))
                canvas[5:325, 10:250] = display

                overlay = np.zeros((22, 240, 3), dtype=np.uint8)
                cv2.putText(overlay, f"#{self.frame_num} {self.current_class} | PC:{self.pc_class} | FPS:{self.fps:.1f}",
                            (3, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
                canvas[5:27, 10:250] = overlay

            # MCU scores (left side)
            cv2.putText(canvas, "MCU scores:", (270, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            y_off = 40
            for cls in CLASSES:
                score = self.current_scores.get(cls, 0)
                bar_w = int(score * 120)
                cv2.rectangle(canvas, (355, y_off), (355 + bar_w, y_off + 14), (0, 150, 0), -1)
                cv2.putText(canvas, f"{cls:8s}", (270, y_off + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                cv2.putText(canvas, f"{score:.4f}", (360 + bar_w, y_off + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (180, 180, 180), 1)
                y_off += 16

            # PC scores (right side)
            y_off = 40
            for cls in CLASSES:
                score = self.pc_scores.get(cls, 0)
                bar_w = int(score * 120)
                cv2.rectangle(canvas, (520, y_off), (520 + bar_w, y_off + 14), (150, 0, 0), -1)
                cv2.putText(canvas, f"{cls:8s}", (440, y_off + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)
                cv2.putText(canvas, f"{score:.4f}", (525 + bar_w, y_off + 11), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (180, 180, 180), 1)
                y_off += 16

            # Compare result
            agree_color = (0, 255, 0) if self.agree else (0, 0, 255)
            agree_text = "MCU == PC" if self.agree else "MCU != PC"
            cv2.putText(canvas, f"{agree_text}  crop:({self.crop_cx},{self.crop_cy})",
                        (270, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.5, agree_color, 2)

            # Controls
            cv2.putText(canvas, "ARROWS/WASD: move | SPACE: save | S: save coords | Q: quit",
                        (270, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
            cv2.putText(canvas, "Green = MCU, Blue = PC inference", (270, 210),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

            cv2.imshow('Step4 + PC Compare', canvas)
            key = cv2.waitKey(30) & 0xFF
            if key == 27 or key == ord('q'):
                self.running = False
            elif key == ord(' '):
                self.save_eye_region()
            elif key == ord('s'):
                self.save_crop_coords()
            elif key == 224 or key == 0:
                key2 = cv2.waitKey(10) & 0xFF
                if key2 == 72: self.crop_cy = max(20, self.crop_cy - 2)
                elif key2 == 80: self.crop_cy = min(219, self.crop_cy + 2)
                elif key2 == 75: self.crop_cx = max(20, self.crop_cx - 2)
                elif key2 == 77: self.crop_cx = min(299, self.crop_cx + 2)
            elif key == ord('w'): self.crop_cy = max(20, self.crop_cy - 2)
            elif key == ord('s'): self.crop_cy = min(219, self.crop_cy + 2)
            elif key == ord('a'): self.crop_cx = max(20, self.crop_cx - 2)
            elif key == ord('d'): self.crop_cx = min(299, self.crop_cx + 2)

    def run(self):
        self.load_model()
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()
        self.running = False
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Step4 + PC Inference Compare')
    parser.add_argument('--port', type=str, default='COM6', help='Serial port')
    parser.add_argument('--baud', type=int, default=460800, help='Baud rate')
    args = parser.parse_args()
    viewer = CompareViewer(port=args.port, baudrate=args.baud)
    viewer.run()


if __name__ == '__main__':
    main()
