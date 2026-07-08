import sys
import numpy as np
import cv2
import serial
import time
import threading
import argparse

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']


def parse_frame(frame_data):
    result = {}
    lines = frame_data.split(b'\r\n')

    preproc_start = frame_data.find(b'PREPROC_START\r\n')
    preproc_end = frame_data.find(b'\r\nPREPROC_END')

    if preproc_start != -1 and preproc_end != -1:
        raw = frame_data[preproc_start + len(b'PREPROC_START\r\n'):preproc_end]
        if len(raw) >= 1024:
            img = np.frombuffer(raw[:1024], dtype=np.uint8).reshape(32, 32)
            result['preproc'] = img

    for line in lines:
        s = line.decode('ascii', errors='ignore')
        if s.startswith('FRAME_NUM:'):
            result['frame_num'] = int(s.split(':')[1])
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
        elif s.startswith('Decode time:'):
            result['decode_time'] = int(s.split(':')[1].split()[0])

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

    return result


class DebugViewer:
    def __init__(self, port='COM6', baudrate=460800):
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.current_preproc = None
        self.current_class = ''
        self.current_scores = {}
        self.frame_num = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.decode_time = 0
        self.infer_time = 0
        self.crop_cx = 0
        self.crop_cy = 0

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
        self.current_class = result.get('class', '?')
        self.current_scores = result.get('scores', {})
        self.decode_time = result.get('decode_time', 0)
        self.infer_time = result.get('infer_time', 0)
        self.crop_cx = result.get('crop_cx', 0)
        self.crop_cy = result.get('crop_cy', 0)

        if 'preproc' in result:
            self.current_preproc = result['preproc']

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

        print(f"[Frame {self.frame_num}] Class={self.current_class} "
              f"Decode={self.decode_time}t Infer={self.infer_time}t FPS={self.fps:.1f}")

    def display_loop(self):
        cv2.namedWindow('Step4 Debug - NN Input (32x32)', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Step4 Debug - NN Input (32x32)', 512, 640)
        while self.running:
            canvas = np.zeros((640, 512, 3), dtype=np.uint8)

            if self.current_preproc is not None:
                zoom = cv2.resize(self.current_preproc, (320, 320), interpolation=cv2.INTER_NEAREST)
                zoom_bgr = cv2.cvtColor(zoom, cv2.COLOR_GRAY2BGR)
                canvas[10:330, 10:330] = zoom_bgr
                cv2.rectangle(canvas, (10, 10), (329, 329), (0, 255, 0), 1)

                for y in range(0, 320, 32):
                    cv2.line(canvas, (10, 10 + y), (329, 10 + y), (50, 50, 50), 1)
                for x in range(0, 320, 32):
                    cv2.line(canvas, (10 + x, 10), (10 + x, 329), (50, 50, 50), 1)

                text = f"NN Input 32x32 | Frame#{self.frame_num} | {self.current_class} | FPS:{self.fps:.1f}"
                cv2.putText(canvas, text, (10, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
                cv2.putText(canvas, f"crop:({self.crop_cx},{self.crop_cy}) dec:{self.decode_time}t inf:{self.infer_time}t",
                            (10, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)

                y_offset = 395
                for cls in CLASSES:
                    score = self.current_scores.get(cls, 0)
                    bar_w = int(score * 200)
                    cv2.rectangle(canvas, (110, y_offset), (110 + bar_w, y_offset + 16), (0, 200, 0), -1)
                    cv2.putText(canvas, f"{cls:8s}", (5, y_offset + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
                    cv2.putText(canvas, f"{score:.4f}", (115 + bar_w, y_offset + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
                    y_offset += 22

                cv2.putText(canvas, "Q: quit", (10, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)
            else:
                cv2.putText(canvas, "Waiting for frames...", (130, 300),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

            cv2.imshow('Step4 Debug - NN Input (32x32)', canvas)
            key = cv2.waitKey(30) & 0xFF
            if key == 27 or key == ord('q'):
                self.running = False

    def run(self):
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()
        self.running = False
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description='Step4 Debug - Visualize NN Input')
    parser.add_argument('--port', type=str, default='COM6', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    viewer = DebugViewer(port=args.port, baudrate=args.baud)
    viewer.run()


if __name__ == '__main__':
    main()
