import sys
import os
import numpy as np
import cv2
import serial
import time
import threading
import argparse

# ============================================================================
# Configuration (Static Global Variables)
# ============================================================================
UART_RETURN_FILE = r'E:\dvp-uart\Match\code\uart_return.txt'
SERIAL_PORT = 'COM6'
SERIAL_BAUDRATE = 115200
MODE_CONTROL_FLAG = 1  # 0: file mode, 1: serial mode
# ============================================================================

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

def parse_frames(data):
    frames = []
    pos = 0
    while True:
        start = data.find(b'FRAME_START\r\n', pos)
        if start == -1:
            break
        end = data.find(b'FRAME_END\r\n', start)
        if end == -1:
            break
        frame_data = data[start:end + len(b'FRAME_END\r\n')]
        frames.append(frame_data)
        pos = end + len(b'FRAME_END\r\n')
    return frames

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

def decode_jpeg(jpeg_data):
    if jpeg_data is None:
        return None
    arr = np.frombuffer(jpeg_data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

class RealtimeViewer:
    def __init__(self, port=None, baudrate=115200, file_path=None):
        self.port = port
        self.baudrate = baudrate
        self.file_path = file_path
        self.running = True
        self.current_img = None
        self.current_class = ''
        self.current_scores = {}
        self.frame_num = 0
        self.decode_time = 0
        self.infer_time = 0
        self.jpeg_size = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.frame_count = 0

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

    def file_thread(self):
        with open(self.file_path, 'rb') as f:
            data = f.read()
        frames = parse_frames(data)
        print(f"[File] Found {len(frames)} frames in {self.file_path}")
        for frame_data in frames:
            if not self.running:
                break
            self.process_frame(frame_data)
            time.sleep(0.03)

    def process_frame(self, frame_data):
        result = parse_frame(frame_data)
        self.frame_num = result.get('frame_num', self.frame_num)
        self.jpeg_size = result.get('jpeg_size', 0)
        self.decode_time = result.get('decode_time', 0)
        self.infer_time = result.get('infer_time', 0)
        self.current_class = result.get('class', '?')
        self.current_scores = result.get('scores', {})

        if 'jpeg_data' in result:
            img = decode_jpeg(result['jpeg_data'])
            if img is not None:
                self.current_img = img

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now
        self.frame_count += 1

        scores_str = ', '.join(f'{k}={v:.4f}' for k, v in self.current_scores.items())
        print(f"[Frame {self.frame_num}] Class={self.current_class} "
              f"JPEG={self.jpeg_size}B "
              f"Decode={self.decode_time}t Infer={self.infer_time}t "
              f"FPS={self.fps:.1f} "
              f"Scores=[{scores_str}]")

    def display_loop(self):
        cv2.namedWindow('Step3 Viewer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Step3 Viewer', 640, 480)
        while self.running:
            img = self.current_img
            if img is not None:
                display = img.copy()
                h, w = display.shape[:2]

                overlay = display.copy()
                cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)

                text = f"Frame#{self.frame_num} | {self.current_class} | FPS:{self.fps:.1f}"
                cv2.putText(display, text, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                y_offset = 60
                for cls in CLASSES:
                    score = self.current_scores.get(cls, 0)
                    bar_w = int(score * (w - 120))
                    color = (0, 255, 0) if cls == self.current_class else (200, 200, 200)
                    cv2.rectangle(display, (100, y_offset), (100 + bar_w, y_offset + 18), color, -1)
                    cv2.putText(display, f"{cls:8s}", (5, y_offset + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
                    cv2.putText(display, f"{score:.4f}", (105 + bar_w, y_offset + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    y_offset += 22

                cv2.imshow('Step3 Viewer', display)
            key = cv2.waitKey(30) & 0xFF
            if key == 27 or key == ord('q'):
                self.running = False
                break

    def run(self):
        if self.port:
            t = threading.Thread(target=self.serial_thread, daemon=True)
        else:
            t = threading.Thread(target=self.file_thread, daemon=True)
        t.start()
        self.display_loop()
        self.running = False
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='Step3 UART Viewer')
    parser.add_argument('--port', type=str, help='Serial port (e.g. COM3)')
    parser.add_argument('--baud', type=int, help='Baud rate')
    parser.add_argument('--file', type=str, help='Read from file instead of serial')
    parser.add_argument('--mode', type=int, choices=[0, 1], help='0: file mode, 1: serial mode')
    args = parser.parse_args()

    # Use command line args if provided, otherwise use global config
    port = args.port if args.port else SERIAL_PORT
    baud = args.baud if args.baud else SERIAL_BAUDRATE
    file_path = args.file if args.file else UART_RETURN_FILE
    mode = args.mode if args.mode is not None else MODE_CONTROL_FLAG

    if mode == 1:
        # Serial mode
        viewer = RealtimeViewer(port=port, baudrate=baud)
    else:
        # File mode
        viewer = RealtimeViewer(file_path=file_path)
    
    viewer.run()

if __name__ == '__main__':
    main()
