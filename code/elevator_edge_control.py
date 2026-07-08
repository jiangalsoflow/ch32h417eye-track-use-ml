"""Edge Elevator Control — elevator demo driven by MCU's eye tracking CNN.

Receives MCU serial protocol output (CLASS: / SCORES: / PREPROC data)
and drives an elevator panel. Blink = blind→non-blind transition.
"""
import sys, os, numpy as np, cv2, serial, time, threading, argparse
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from edge_inference_viewer import parse_frame, CLASSES, NN_SZ


def floor_num(row, col):
    return row * 2 + 1 if col == 0 else row * 2 + 2


BTN_W, BTN_H = 110, 62
LEFT_X, RIGHT_X = 30, 165
BTN_BASE_Y = 440
BTN_GAP = 10


def btn_rect(row, col):
    x = LEFT_X if col == 0 else RIGHT_X
    y = BTN_BASE_Y - row * (BTN_H + BTN_GAP)
    return x, y, x + BTN_W, y + BTN_H


class EdgeElevatorControl:
    def __init__(self, port='COM6', baudrate=460800):
        self.port = port
        self.baudrate = baudrate
        self.running = True

        self.frame_num = 0
        self.fps = 0.0
        self.last_frame_time = time.time()
        self.infer_time = 0

        self.nn_input = None
        self.class_name = 'center'
        self.class_idx = 1
        self.scores = {c: 0.0 for c in CLASSES}
        self.scores['center'] = 1.0
        self.decode_ok = False

        self.mode = 'idle'
        self.cursor_row = 0
        self.cursor_col = 0
        self.selected_floor = -1
        self.blink_pending = False
        self.flash_timer = 0.0

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

        if self.decode_ok and self.class_name:
            direction = self.class_name
            prev_floor = floor_num(self.cursor_row, self.cursor_col)

            if self.mode == 'idle':
                if direction == 'blind':
                    self.blink_pending = True
                elif self.blink_pending:
                    self.mode = 'selecting'
                    self.blink_pending = False

            elif self.mode == 'selecting':
                if direction == 'blind':
                    self.blink_pending = True
                elif self.blink_pending:
                    cur_floor = floor_num(self.cursor_row, self.cursor_col)
                    if cur_floor == prev_floor:
                        self.selected_floor = cur_floor
                        self.mode = 'selected'
                    self.blink_pending = False
                else:
                    if direction == 'up':
                        self.cursor_row = min(4, self.cursor_row + 1)
                    elif direction == 'down':
                        self.cursor_row = max(0, self.cursor_row - 1)
                    elif direction == 'left':
                        self.cursor_col = 0
                    elif direction == 'right':
                        self.cursor_col = 1

        now = time.time()
        dt = now - self.last_frame_time
        if dt > 0:
            self.fps = 1.0 / dt
        self.last_frame_time = now

    def draw(self, canvas):
        H, W = canvas.shape[:2]
        cv2.rectangle(canvas, (0, 0), (W, H), (18, 18, 18), -1)

        panel_x, panel_y, panel_w, panel_h = 10, 10, 300, 530
        cv2.rectangle(canvas, (panel_x, panel_y),
                      (panel_x + panel_w, panel_y + panel_h), (30, 30, 35), -1)
        cv2.rectangle(canvas, (panel_x, panel_y),
                      (panel_x + panel_w, panel_y + panel_h), (80, 80, 85), 2)
        cv2.putText(canvas, 'ELEVATOR', (panel_x + 80, panel_y + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        self.flash_timer += 0.033
        flash_on = int(self.flash_timer * 3) % 2 == 0
        cur_floor = floor_num(self.cursor_row, self.cursor_col)

        for row in range(5):
            for col in range(2):
                fn = floor_num(row, col)
                x1, y1, x2, y2 = btn_rect(row, col)

                if fn == self.selected_floor:
                    color = (0, 180, 80)
                    border = (0, 255, 100)
                    thickness = 2
                elif fn == cur_floor and self.mode == 'selecting' and flash_on:
                    color = (50, 140, 200)
                    border = (80, 200, 255)
                    thickness = 2
                else:
                    color = (60, 60, 65)
                    border = (100, 100, 105)
                    thickness = 1

                cv2.rectangle(canvas, (x1, y1), (x2, y2), color, -1)
                cv2.rectangle(canvas, (x1, y1), (x2, y2), border, thickness)

                txt = str(fn)
                (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)
                cv2.putText(canvas, txt,
                            (x1 + (BTN_W - tw) // 2, y1 + (BTN_H + th) // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

        rx, ry = 330, 10
        cv2.putText(canvas, 'Eye ROI (32x32)', (rx, ry - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)
        cam_w, cam_h = 320, 240
        if self.nn_input is not None:
            disp = cv2.resize(self.nn_input, (cam_w, cam_h),
                              interpolation=cv2.INTER_NEAREST)
            disp_bgr = cv2.cvtColor(disp, cv2.COLOR_GRAY2BGR)
            canvas[ry:ry + cam_h, rx:rx + cam_w] = disp_bgr

        nn_x, nn_y = rx + cam_w + 15, ry
        nn_sz = 180
        cv2.putText(canvas, 'NN Input (32x32)', (nn_x, nn_y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (140, 140, 140), 1)
        if self.nn_input is not None:
            nn_bgr = cv2.cvtColor(self.nn_input, cv2.COLOR_GRAY2BGR)
            nn_disp = cv2.resize(nn_bgr, (nn_sz, nn_sz), interpolation=cv2.INTER_NEAREST)
            canvas[nn_y:nn_y + nn_sz, nn_x:nn_x + nn_sz] = nn_disp
            cv2.rectangle(canvas, (nn_x, nn_y), (nn_x + nn_sz, nn_y + nn_sz), (0, 180, 0), 2)

        rec_x, rec_y = rx, ry + cam_h + 10
        cv2.putText(canvas, 'MCU Edge CNN Inference', (rec_x, rec_y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (100, 180, 255), 1)
        cv2.line(canvas, (rec_x, rec_y + 20), (rec_x + 300, rec_y + 20), (60, 60, 60), 1)

        cls_color = (0, 255, 200) if self.class_idx != 0 else (255, 165, 0)
        cv2.putText(canvas, self.class_name.upper(), (rec_x, rec_y + 52),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, cls_color, 2)

        if self.mode == 'selected':
            prompt = f'Floor {self.selected_floor} Selected'
            pcolor = (0, 255, 120)
        elif self.mode == 'selecting':
            prompt = f'Blink to confirm Floor {cur_floor}'
            pcolor = (200, 200, 50)
        else:
            prompt = 'Blink to activate elevator'
            pcolor = (140, 140, 200)
        cv2.putText(canvas, prompt, (rec_x, rec_y + 76),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, pcolor, 1)

        bar_x, bar_y = 10, BTN_BASE_Y + BTN_H + 20
        bar_w = W - 20
        bar_h = 14
        bar_gap = 3
        bar_label_w = 80

        for ci, cls in enumerate(CLASSES):
            by = bar_y + ci * (bar_h + bar_gap)
            prob = self.scores.get(cls, 0.0)
            cv2.putText(canvas, cls, (bar_x, by + bar_h - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1)
            bbx = bar_x + bar_label_w + 5
            bbw = bar_w - bar_label_w - 110
            cv2.rectangle(canvas, (bbx, by), (bbx + bbw, by + bar_h), (35, 35, 35), -1)
            fill_w = max(1, int(prob * bbw))
            if ci == self.class_idx and prob > 0.5:
                bc = (0, 200, 100)
            elif ci == self.class_idx:
                bc = (0, 140, 70)
            else:
                bc = (55, 65, 85)
            cv2.rectangle(canvas, (bbx, by), (bbx + fill_w, by + bar_h), bc, -1)
            cv2.putText(canvas, f'{prob:.4f}', (bbx + bbw + 6, by + bar_h - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3,
                        (0, 255, 150) if ci == self.class_idx else (130, 130, 130), 1)

        status_y = H - 18
        cv2.rectangle(canvas, (0, status_y - 2), (W, H), (12, 12, 12), -1)
        cv2.putText(canvas, f'Frame:#{self.frame_num}  FPS:{self.fps:.1f}  '
                    f'Infer:{self.infer_time}ticks',
                    (10, status_y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 160, 160), 1)
        cv2.putText(canvas, 'MCU Edge CNN v3.2 | FW: STEP7_PREPROC v1',
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
        cv2.namedWindow('Edge Elevator Control', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Edge Elevator Control', 1020, 600)

        while self.running:
            canvas = np.zeros((600, 1020, 3), dtype=np.uint8)
            self.draw(canvas)
            cv2.imshow('Edge Elevator Control', canvas)

            key = cv2.waitKeyEx(30)
            if key == 27 or key == ord('q'):
                self.running = False
            elif key == ord(' '):
                if self.nn_input is not None:
                    ts = time.strftime('%Y%m%d_%H%M%S')
                    fname = f'elev_edge_{ts}_{self.frame_num:04d}.jpg'
                    cv2.imwrite(os.path.join(self.save_dir, fname), self.nn_input)
            elif key == ord('t'):
                self.mode = 'idle'
                self.selected_floor = -1
                self.cursor_row = 0
                self.cursor_col = 0
                self.blink_pending = False

        cv2.destroyAllWindows()

    def run(self):
        t = threading.Thread(target=self.serial_thread, daemon=True)
        t.start()
        self.display_loop()


def main():
    parser = argparse.ArgumentParser(description='Edge Elevator Control — MCU CNN driven')
    parser.add_argument('--port', type=str, default='COM6')
    parser.add_argument('--baud', type=int, default=460800)
    args = parser.parse_args()
    ctrl = EdgeElevatorControl(port=args.port, baudrate=args.baud)
    ctrl.run()


if __name__ == '__main__':
    main()
