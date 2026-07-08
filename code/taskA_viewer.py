import sys
import os
import numpy as np
import cv2
import serial
import time
import threading
import argparse
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
CROP_SZ = 40
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')


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
        return None, None, None, None
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
    return out, best_idx, eye_32, crop


class TaskAViewer:
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
        self.crop_cx = 170
        self.crop_cy = 110
        self.pc_scores = {}
        self.pc_class = '?'
        self.pc_best_idx = -1
        self.pc_eye_32 = None
        self.pc_crop_40 = None
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
            out, best_idx, eye_32, crop_40 = pc_preprocess_infer(
                result['jpeg_data'], self.crop_cx, self.crop_cy, self.model)
            if out is not None:
                self.pc_scores = {CLASSES[i]: float(out[i]) for i in range(6)}
                self.pc_class = CLASSES[best_idx]
                self.pc_best_idx = best_idx
                self.pc_eye_32 = eye_32
                self.pc_crop_40 = crop_40

        self.agree = (self.current_class == self.pc_class)

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

        agree_str = "OK" if self.agree else "DIFF"
        print(f"[Frame {self.frame_num}] MCU={self.current_class} PC={self.pc_class} {agree_str} FPS={self.fps:.1f}")

    def display_loop(self):
            cv2.namedWindow('TaskA Viewer', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('TaskA Viewer', 1050, 600)
        while self.running:
            canvas = np.zeros((600, 1000, 3), dtype=np.uint8)

            # ============ TOP-LEFT: RAW + mirrored JPEG with crop box ============
            if self.current_img is not None:
                img_raw = self.current_img.copy()
                h, w = img_raw.shape[:2]
                half = 20
                cx, cy = self.crop_cx, self.crop_cy
                x1 = max(0, cx - half)
                y1 = max(0, cy - half)
                x2 = min(w, cx + half)
                y2 = min(h, cy + half)
                cv2.rectangle(img_raw, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.line(img_raw, (cx - 5, cy), (cx + 5, cy), (0, 0, 255), 1)
                cv2.line(img_raw, (cx, cy - 5), (cx, cy + 5), (0, 0, 255), 1)
                raw_disp = cv2.resize(img_raw, (280, 210))
                canvas[10:220, 10:290] = raw_disp

                img_mirror = cv2.flip(img_raw, 1)
                cv2.rectangle(img_mirror, (w - 1 - x2, y1), (w - 1 - x1, y2), (0, 0, 255), 2)
                mir_disp = cv2.resize(img_mirror, (280, 210))
                canvas[10:220, 305:585] = mir_disp

            cv2.putText(canvas, "RAW", (10, 238), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            cv2.putText(canvas, "MIRRORED", (305, 238), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # ============ TOP-RIGHT: PC crop 40x40 (flipped) ============
            if self.pc_crop_40 is not None:
                crop_bgr = cv2.cvtColor(self.pc_crop_40, cv2.COLOR_GRAY2BGR)
                crop_bgr = cv2.resize(crop_bgr, (200, 200), interpolation=cv2.INTER_NEAREST)
                canvas[10:210, 610:810] = crop_bgr
                cv2.rectangle(canvas, (610, 10), (810, 210), (255, 128, 0), 2)
            cv2.putText(canvas, "PC crop 40x40 (flipped)", (610, 228),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # ============ BOTTOM-LEFT: PC NN input 32x32 + inference ============
            if self.pc_eye_32 is not None:
                nn_bgr = cv2.cvtColor(self.pc_eye_32, cv2.COLOR_GRAY2BGR)
                nn_disp = cv2.resize(nn_bgr, (180, 180), interpolation=cv2.INTER_NEAREST)
                canvas[280:460, 10:190] = nn_disp
                cv2.rectangle(canvas, (10, 280), (190, 460), (0, 255, 0), 2)
            cv2.putText(canvas, "PC NN input 32x32", (10, 478),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # MCU vs PC score bars (right of NN input)
            cv2.putText(canvas, "MCU (green) vs PC (blue)", (200, 290),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
            y_off = 310
            for cls in CLASSES:
                mcu_s = self.current_scores.get(cls, 0)
                pc_s = self.pc_scores.get(cls, 0)
                mcu_w = int(mcu_s * 140)
                pc_w = int(pc_s * 140)
                cv2.rectangle(canvas, (255, y_off), (255 + mcu_w, y_off + 11), (0, 150, 0), -1)
                cv2.rectangle(canvas, (255, y_off + 11), (255 + pc_w, y_off + 22), (150, 50, 0), -1)
                cv2.putText(canvas, f"{cls:8s} M:{mcu_s:.4f}", (200, y_off + 9),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (180, 180, 180), 1)
                cv2.putText(canvas, f"{'':8s} P:{pc_s:.4f}", (200, y_off + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.3, (180, 180, 180), 1)
                y_off += 28

            # ============ BOTTOM-RIGHT: red box image vs NN input ============
            if self.current_img is not None and self.pc_eye_32 is not None:
                # Extract red box region from JPEG as raw crop
                img_gray = cv2.cvtColor(self.current_img, cv2.COLOR_BGR2GRAY)
                cx, cy = self.crop_cx, self.crop_cy
                half = 20
                bx1 = max(0, cx - half)
                by1 = max(0, cy - half)
                bx2 = min(img_gray.shape[1], cx + half)
                by2 = min(img_gray.shape[0], cy + half)
                box_crop = img_gray[by1:by2, bx1:bx2]
                if box_crop.size > 0:
                    box_bgr = cv2.cvtColor(box_crop, cv2.COLOR_GRAY2BGR)
                    box_disp = cv2.resize(box_bgr, (180, 180), interpolation=cv2.INTER_NEAREST)
                    canvas[280:460, 500:680] = box_disp
                    cv2.putText(canvas, "Red box 40x40 (raw)", (500, 478),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.rectangle(canvas, (500, 280), (680, 460), (0, 0, 255), 2)

                # NN input beside red box
                nn2_bgr = cv2.cvtColor(self.pc_eye_32, cv2.COLOR_GRAY2BGR)
                nn2_disp = cv2.resize(nn2_bgr, (180, 180), interpolation=cv2.INTER_NEAREST)
                canvas[280:460, 700:880] = nn2_disp
                cv2.rectangle(canvas, (700, 280), (880, 460), (0, 255, 0), 2)
                cv2.putText(canvas, "NN input 32x32", (700, 478),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # ============ Info bar ============
            agree_color = (0, 255, 0) if self.agree else (0, 0, 255)
            agree_text = "MCU==PC" if self.agree else "MCU!=PC"
            cv2.putText(canvas, f"#{self.frame_num} MCU={self.current_class} PC={self.pc_class} {agree_text} FPS:{self.fps:.1f}",
                        (10, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.45, agree_color, 1)

            cv2.putText(canvas, "Q: quit", (960, 590), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

            cv2.imshow('TaskA Viewer', canvas)
            key = cv2.waitKey(30) & 0xFF
            if key == 27 or key == ord('q'):
                self.running = False

    def run(self):
        self.load_model()
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()
        self.running = False
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='TaskA Viewer')
    parser.add_argument('--port', type=str, default='COM6', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    viewer = TaskAViewer(port=args.port, baudrate=args.baud)
    viewer.run()


if __name__ == '__main__':
    main()
