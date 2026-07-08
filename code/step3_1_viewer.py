import sys
import os
import numpy as np
import cv2
import serial
import time
import threading
import argparse
import datetime

COLLECT_DIR = r'E:\dvp-uart\Match\collected_data\raw'
SAVE_SEQ = [0]

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

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
        elif s.startswith('Decode time:'):
            result['decode_time'] = int(s.split(':')[1].split()[0])
        elif s.startswith('CLASS:'):
            result['class'] = s.split(':')[1].strip()
        elif s.startswith('Infer time:'):
            result['infer_time'] = int(s.split(':')[1].split()[0])

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

class RealtimeCollector:
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

        self.box_cx = 120
        self.box_cy = 100
        self.box_size = 40

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
                        if len(buf) > 100000:
                            buf = buf[-1000:]
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
        self.current_class = result.get('class', '?')
        self.current_scores = result.get('scores', {})

        if 'jpeg_data' in result:
            arr = np.frombuffer(result['jpeg_data'], dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None:
                self.current_img = img

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

    def save_eye_region(self):
        if self.current_img is None:
            return

        img = self.current_img
        h, w = img.shape[:2]

        display_cx = self.box_cx
        display_cy = self.box_cy

        orig_center_y = 239 - display_cx
        orig_center_x = display_cy

        half = self.box_size // 2
        x1 = max(0, orig_center_x - half)
        y1 = max(0, orig_center_y - half)
        x2 = min(w, orig_center_x + half)
        y2 = min(h, orig_center_y + half)

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
        print(f"[SAVE] {fpath}  pos=(cx={self.box_cx}, cy={self.box_cy})  orig_center=({orig_center_x}, {orig_center_y})")

    def display_loop(self):
        cv2.namedWindow('Step3.1 Collector', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Step3.1 Collector', 480, 640)
        while self.running:
            img = self.current_img
            if img is not None:
                display = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                dh, dw = display.shape[:2]

                half = self.box_size // 2
                x1 = self.box_cx - half
                y1 = self.box_cy - half
                x2 = self.box_cx + half
                y2 = self.box_cy + half

                cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.line(display, (self.box_cx - 5, self.box_cy), (self.box_cx + 5, self.box_cy), (0, 0, 255), 1)
                cv2.line(display, (self.box_cx, self.box_cy - 5), (self.box_cx, self.box_cy + 5), (0, 0, 255), 1)

                overlay = display.copy()
                cv2.rectangle(overlay, (0, 0), (dw, 24), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)

                text = f"Frame#{self.frame_num} | {self.current_class} | FPS:{self.fps:.1f} | Box:({self.box_cx},{self.box_cy})"
                cv2.putText(display, text, (5, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

                y_offset = dh - 80
                cv2.putText(display, "ARROWS/WASD: move box  SPACE: save  q: quit", (5, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                cv2.putText(display, f"Saved: {SAVE_SEQ[0]}", (5, y_offset + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

                cv2.imshow('Step3.1 Collector', display)
            else:
                blank = np.zeros((320, 240, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for frames...", (30, 160),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                cv2.imshow('Step3.1 Collector', blank)

            key = cv2.waitKey(30) & 0xFF
            if key == 27 or key == ord('q'):
                self.running = False
            elif key == ord(' '):
                self.save_eye_region()
            elif key == 224 or key == 0:
                key2 = cv2.waitKey(10) & 0xFF
                if key2 == 72: self.box_cy = max(20, self.box_cy - 2)
                elif key2 == 80: self.box_cy = min(299, self.box_cy + 2)
                elif key2 == 75: self.box_cx = max(20, self.box_cx - 2)
                elif key2 == 77: self.box_cx = min(219, self.box_cx + 2)
            elif key == ord('w'): self.box_cy = max(20, self.box_cy - 2)
            elif key == ord('s'): self.box_cy = min(299, self.box_cy + 2)
            elif key == ord('a'): self.box_cx = max(20, self.box_cx - 2)
            elif key == ord('d'): self.box_cx = min(219, self.box_cx + 2)

    def run(self):
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()
        self.running = False
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='Step3.1 Data Collector')
    parser.add_argument('--port', type=str, default='COM6', help='Serial port')
    parser.add_argument('--baud', type=int, default=460800, help='Baud rate')
    args = parser.parse_args()

    viewer = RealtimeCollector(port=args.port, baudrate=args.baud)
    viewer.run()

if __name__ == '__main__':
    main()
