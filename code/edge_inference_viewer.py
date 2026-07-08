"""Edge Inference Viewer — displays MCU's real-time eye tracking CNN output.

Parses MCU serial protocol (STEP7_PREPROC v1):
  CLASS: direction    SCORES: class=prob ...
  PREPROC_START [40-line 40x40 crop] PREPROC_END
"""
import sys, os, numpy as np, cv2, serial, time, threading, argparse
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
NN_SZ = 32


def parse_frame(frame_data):
    result = {}
    lines = frame_data.split(b'\r\n')
    for line in lines:
        s = line.decode('ascii', errors='ignore').strip()
        if not s:
            continue
        if s.startswith('FRAME_NUM:'):
            result['frame_num'] = int(s.split(':')[1])
        elif s.startswith('JPEG_SIZE:'):
            result['jpeg_size'] = int(s.split(':')[1])
        elif s.startswith('DECODE_OK:'):
            result['decode_ok'] = True
        elif s.startswith('DECODE_FAIL:'):
            result['decode_ok'] = False
        elif s.startswith('CLASS:'):
            cls_name = s.split(':')[1].strip()
            if cls_name in CLASSES:
                result['class_name'] = cls_name
                result['class_idx'] = CLASSES.index(cls_name)
        elif s.startswith('SCORES:'):
            scores = {}
            parts = s[7:].strip().split()
            for p in parts:
                if '=' in p:
                    k, v = p.split('=')
                    if k in CLASSES:
                        scores[k] = float(v)
            if len(scores) == 6:
                result['scores'] = scores
        elif s.startswith('Infer time:'):
            result['infer_time'] = int(s.split(':')[1].strip().split()[0])
        elif s.startswith('Decode time:'):
            result['decode_time'] = int(s.split(':')[1].strip().split()[0])

    preproc_start = frame_data.find(b'PREPROC_START\r\n')
    preproc_end = frame_data.find(b'\r\nPREPROC_END')
    if preproc_start != -1 and preproc_end != -1:
        preproc_start += len(b'PREPROC_START\r\n')
        preproc_data = frame_data[preproc_start:preproc_end]
        if len(preproc_data) == 1024:
            result['nn_input'] = np.frombuffer(preproc_data, dtype=np.uint8).reshape(32, 32).copy()

    return result


class EdgeInferenceViewer:
    def __init__(self, port='COM6', baudrate=460800):
        self.port = port
        self.baudrate = baudrate
        self.running = True

        self.frame_num = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.infer_time = 0

        self.nn_input = None
        self.class_name = '?'
        self.class_idx = 1
        self.scores = {c: 0.0 for c in CLASSES}
        self.scores['center'] = 1.0
        self.decode_ok = False

        self.save_dir = os.path.join(os.path.dirname(__file__), '..', 'images_miss')
        os.makedirs(self.save_dir, exist_ok=True)

    def process_frame(self, frame_data):
        result = parse_frame(frame_data)
        self.frame_num = result.get('frame_num', self.frame_num)
        self.decode_ok = result.get('decode_ok', False)

        if 'class_idx' in result:
            self.class_idx = result['class_idx']
            self.class_name = result['class_name']
        if 'scores' in result:
            self.scores = result['scores']
        if 'infer_time' in result:
            self.infer_time = result['infer_time']
        if 'nn_input' in result:
            self.nn_input = result['nn_input']

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

    def draw(self, canvas):
        H, W = canvas.shape[:2]
        cv2.rectangle(canvas, (0, 0), (W, H), (18, 18, 18), -1)

        cam_x, cam_y, cam_w, cam_h = 10, 10, 400, 300
        cv2.putText(canvas, 'Eye ROI (32x32)', (cam_x, cam_y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)

        if self.nn_input is not None:
            disp = cv2.resize(self.nn_input, (cam_w, cam_h),
                              interpolation=cv2.INTER_NEAREST)
            disp_bgr = cv2.cvtColor(disp, cv2.COLOR_GRAY2BGR)
            canvas[cam_y:cam_y + cam_h, cam_x:cam_x + cam_w] = disp_bgr

        nn_x, nn_y, nn_sz = 440, 10, 240
        cv2.putText(canvas, 'NN Input (32x32)', (nn_x, nn_y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)
        if self.nn_input is not None:
            nn_bgr = cv2.cvtColor(self.nn_input, cv2.COLOR_GRAY2BGR)
            nn_disp = cv2.resize(nn_bgr, (nn_sz, nn_sz), interpolation=cv2.INTER_NEAREST)
            canvas[nn_y:nn_y + nn_sz, nn_x:nn_x + nn_sz] = nn_disp
            cv2.rectangle(canvas, (nn_x, nn_y), (nn_x + nn_sz, nn_y + nn_sz), (0, 180, 0), 2)

        inf_x, inf_y = nn_x, nn_y + nn_sz + 10
        cv2.putText(canvas, 'MCU Edge CNN Inference', (inf_x, inf_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 180, 255), 1)
        cv2.line(canvas, (inf_x, inf_y + 20), (inf_x + 240, inf_y + 20), (60, 60, 60), 1)

        cls_color = (0, 255, 200) if self.class_idx != 0 else (255, 165, 0)
        cv2.putText(canvas, self.class_name.upper(), (inf_x, inf_y + 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, cls_color, 2)

        bar_x, bar_y = 10, 360
        bar_w = W - 20
        bar_h = 18
        bar_gap = 5
        bar_label_w = 80

        for ci, cls in enumerate(CLASSES):
            by = bar_y + ci * (bar_h + bar_gap)
            prob = self.scores.get(cls, 0.0)
            cv2.putText(canvas, cls, (bar_x, by + bar_h - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1)
            bbx = bar_x + bar_label_w + 5
            bbw = bar_w - bar_label_w - 110
            cv2.rectangle(canvas, (bbx, by), (bbx + bbw, by + bar_h), (40, 40, 40), -1)
            fill_w = max(1, int(prob * bbw))
            if ci == self.class_idx and prob > 0.5:
                bar_color = (0, 200, 100)
            elif ci == self.class_idx:
                bar_color = (0, 140, 70)
            else:
                bar_color = (60, 70, 90)
            cv2.rectangle(canvas, (bbx, by), (bbx + fill_w, by + bar_h), bar_color, -1)
            cv2.putText(canvas, f'{prob:.4f}', (bbx + bbw + 8, by + bar_h - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35,
                        (0, 255, 150) if ci == self.class_idx else (140, 140, 140), 1)

        status_y = H - 18
        cv2.rectangle(canvas, (0, status_y - 2), (W, H), (12, 12, 12), -1)
        cv2.putText(canvas, f'Frame:#{self.frame_num}  FPS:{self.fps:.1f}  '
                    f'Infer:{self.infer_time}ticks',
                    (10, status_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1)
        status = 'OK' if self.decode_ok else 'FAIL'
        cv2.putText(canvas, f'MCU:{status} | FW: STEP7_PREPROC v1',
                    (W - 350, status_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (100, 100, 100), 1)

    def serial_thread(self):
        ser = serial.Serial(self.port, self.baudrate, timeout=1)
        buf = bytearray()
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

    def display_loop(self):
        cv2.namedWindow('Edge Inference Viewer', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Edge Inference Viewer', 1000, 500)

        while self.running:
            canvas = np.zeros((500, 1000, 3), dtype=np.uint8)
            self.draw(canvas)
            cv2.imshow('Edge Inference Viewer', canvas)

            key = cv2.waitKeyEx(30)
            if key == 27 or key == ord('q'):
                self.running = False
            elif key == ord(' '):
                if self.nn_input is not None:
                    ts = time.strftime('%Y%m%d_%H%M%S')
                    fname = f'edge_{ts}_{self.frame_num:04d}_{self.class_name}.jpg'
                    cv2.imwrite(os.path.join(self.save_dir, fname), self.nn_input)

        cv2.destroyAllWindows()

    def run(self):
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()


def main():
    parser = argparse.ArgumentParser(description='Edge Inference Viewer — MCU CNN output')
    parser.add_argument('--port', type=str, default='COM6')
    parser.add_argument('--baud', type=int, default=460800)
    args = parser.parse_args()
    viz = EdgeInferenceViewer(port=args.port, baudrate=args.baud)
    viz.run()


if __name__ == '__main__':
    main()
