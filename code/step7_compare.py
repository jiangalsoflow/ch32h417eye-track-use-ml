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
    jpeg_end = frame_data.find(b'\r\nJPEG_END', jpeg_start) if jpeg_start != -1 else -1
    if jpeg_start != -1 and jpeg_end != -1:
        result['jpeg_data'] = frame_data[jpeg_start + len(b'JPEG_START\r\n'):jpeg_end]

    return result


def pc_preprocess(jpeg_data, cx, cy, crop_sz=40):
    arr = np.frombuffer(jpeg_data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None, None, 0
    h, w = img.shape
    half = crop_sz // 2
    x1 = max(0, cx - half)
    y1 = max(0, cy - half)
    x2 = min(w, cx + half)
    y2 = min(h, cy + half)
    crop = img[y1:y2, x1:x2]
    if crop.shape[0] < crop_sz or crop.shape[1] < crop_sz:
        crop = cv2.resize(crop, (crop_sz, crop_sz))
    crop = cv2.flip(crop, 1)
    result = cv2.resize(crop, (32, 32), interpolation=cv2.INTER_NEAREST)
    cksum = int(result.astype(np.uint32).sum())
    return result, crop, cksum


class CompareViewer:
    def __init__(self, port='COM6', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.running = True
        self.current_jpeg_img = None
        self.current_pc_preproc = None
        self.current_pc_crop = None
        self.current_class = ''
        self.current_scores = {}
        self.frame_num = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.crop_cx = 0
        self.crop_cy = 0
        self.mcu_cksum = 0
        self.pc_cksum = 0

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
                        if len(buf) > 300000:
                            buf = buf[-5000:]
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
        if 'crop_cx' in result:
            self.crop_cx = result['crop_cx']
            self.crop_cy = result['crop_cy']
        if 'mcu_cksum' in result:
            self.mcu_cksum = result['mcu_cksum']

        if 'jpeg_data' in result and self.crop_cx > 0:
            arr = np.frombuffer(result['jpeg_data'], dtype=np.uint8)
            img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img_bgr is not None:
                self.current_jpeg_img = img_bgr
            pc_out, pc_crop, self.pc_cksum = pc_preprocess(
                result['jpeg_data'], self.crop_cx, self.crop_cy)
            self.current_pc_preproc = pc_out
            self.current_pc_crop = pc_crop

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

        match_status = "MATCH" if (self.mcu_cksum > 0 and self.mcu_cksum == self.pc_cksum) else "MISMATCH"
        print(f"[Frame {self.frame_num}] Class={self.current_class} "
              f"MCU_ck={self.mcu_cksum} PC_ck={self.pc_cksum} {match_status} FPS={self.fps:.1f}")

    def display_loop(self):
        cv2.namedWindow('Step7 Compare', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Step7 Compare', 960, 520)
        while self.running:
            canvas = np.zeros((520, 960, 3), dtype=np.uint8)

            # RAW JPEG with crop box (upper-left, 320x240)
            if self.current_jpeg_img is not None and self.crop_cx > 0:
                disp = self.current_jpeg_img.copy()
                h, w = disp.shape[:2]
                half = 20
                x1 = max(0, self.crop_cx - half)
                y1 = max(0, self.crop_cy - half)
                x2 = min(w, self.crop_cx + half)
                y2 = min(h, self.crop_cy + half)
                cv2.rectangle(disp, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cv2.line(disp, (self.crop_cx - 5, self.crop_cy),
                         (self.crop_cx + 5, self.crop_cy), (0, 0, 255), 1)
                cv2.line(disp, (self.crop_cx, self.crop_cy - 5),
                         (self.crop_cx, self.crop_cy + 5), (0, 0, 255), 1)
                disp_s = cv2.resize(disp, (320, 240))
                canvas[10:250, 10:330] = disp_s
            cv2.putText(canvas, "RAW 320x240 + crop box", (10, 270),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # PC 40x40 crop before resize (upper-center)
            if self.current_pc_crop is not None:
                crop_disp = cv2.cvtColor(self.current_pc_crop, cv2.COLOR_GRAY2BGR)
                crop_disp = cv2.resize(crop_disp, (200, 200), interpolation=cv2.INTER_NEAREST)
                canvas[10:210, 350:550] = crop_disp
                cv2.rectangle(canvas, (350, 10), (550, 210), (255, 128, 0), 2)
            cv2.putText(canvas, "PC crop 40x40 (flipped)", (350, 230),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # PC preproc 32x32 (upper-right)
            if self.current_pc_preproc is not None:
                pc_disp = cv2.resize(self.current_pc_preproc, (256, 256), interpolation=cv2.INTER_NEAREST)
                pc_bgr = cv2.cvtColor(pc_disp, cv2.COLOR_GRAY2BGR)
                canvas[10:266, 570:826] = pc_bgr
                cv2.rectangle(canvas, (570, 10), (826, 266), (0, 255, 0), 2)
            cv2.putText(canvas, "PC NN input 32x32", (570, 280),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

            # Info
            match_color = (0, 255, 0) if (self.mcu_cksum > 0 and self.mcu_cksum == self.pc_cksum) else (0, 0, 255)
            match_text = "MATCH" if (self.mcu_cksum > 0 and self.mcu_cksum == self.pc_cksum) else "MISMATCH"
            cv2.putText(canvas, f"#{self.frame_num} Class={self.current_class} MCU_ck={self.mcu_cksum} PC_ck={self.pc_cksum} {match_text}",
                        (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.55, match_color, 2)

            # Scores
            y_off = 325
            for cls in CLASSES:
                score = self.current_scores.get(cls, 0)
                bar_w = int(score * 180)
                cv2.rectangle(canvas, (120, y_off), (120 + bar_w, y_off + 16), (0, 200, 0), -1)
                cv2.putText(canvas, f"{cls:8s}", (10, y_off + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1)
                cv2.putText(canvas, f"{score:.4f}", (125 + bar_w, y_off + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (220, 220, 220), 1)
                y_off += 20

            cv2.putText(canvas, "Q: quit", (10, 500), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (180, 180, 180), 1)

            cv2.imshow('Step7 Compare', canvas)
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
    parser = argparse.ArgumentParser(description='Step7 Compare')
    parser.add_argument('--port', type=str, default='COM6', help='Serial port')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()
    viewer = CompareViewer(port=args.port, baudrate=args.baud)
    viewer.run()


if __name__ == '__main__':
    main()
