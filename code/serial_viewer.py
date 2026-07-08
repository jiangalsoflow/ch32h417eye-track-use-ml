"""
串口实时图像查看器 + 裁剪框校准
↑↓←→ 移动裁剪框 | +/- 调大小 | 空格 截图 | 回车 保存坐标 | g 灰度 | q 退出
右上角显示裁剪区域放大图
"""
import os
os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'   # suppress OpenCV JPEG decode warnings
os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'

import serial, cv2, numpy as np, time, struct, json
from collections import deque

# ======== 默认配置（首次运行，后续自动读取 crop_coords.json）========
SERIAL_PORT = "COM6"
BAUDRATE    = 115200
CROP_SIZE   = 64
CX, CY      = 320, 240
MOVE_STEP   = 2
# =================================================================

RGB565_MAGIC = 0xAA55AA55
MAGIC_BYTES  = struct.pack('>I', RGB565_MAGIC)
COORDS_FILE  = os.path.join(os.path.dirname(__file__), 'crop_coords.json')

def load_coords():
    """从 JSON 加载上次保存的坐标，crop_size 以代码配置为准"""
    if os.path.exists(COORDS_FILE):
        try:
            with open(COORDS_FILE, 'r') as f:
                d = json.load(f)
            cx = d.get('cx', CX)
            cy = d.get('cy', CY)
            print(f"加载已保存坐标: cx={cx}, cy={cy} (size={CROP_SIZE} 以代码配置为准)")
            return cx, cy, CROP_SIZE
        except: pass
    return CX, CY, CROP_SIZE

class DualModeViewer:
    def __init__(self, port, baudrate=921600):
        self.port = port
        self.baudrate = baudrate
        self.buffer = bytearray()
        self.text_buf = bytearray()
        self.frame_count = 0
        self.raw_bytes_received = 0
        self.start_time = None
        self.frame_times = deque(maxlen=20)
        self.SOI = b'\xff\xd8'
        self.EOI = b'\xff\xd9'
        self.cx, self.cy, self.crop_size = load_coords()
        self.move_step = MOVE_STEP
        self.grayscale = True
        self.last_img = None
        self.mute = True       # 默认静音
        self.class_idx = 1     # 当前类别: 0=blind 1=center 2=down 3=left 4=right 5=up
        # 从已有文件恢复计数（取最大编号+1），避免覆盖
        CLASSES = ['blind','center','down','left','right','up']
        images_root = os.path.join(os.path.dirname(__file__), '..', 'images')
        self.counters = []
        import re
        for c in CLASSES:
            d = os.path.join(images_root, c)
            max_n = -1
            if os.path.isdir(d):
                for f in os.listdir(d):
                    m = re.match(rf'{c}_(\d+)\.jpg', f)
                    if m:
                        max_n = max(max_n, int(m.group(1)))
            self.counters.append(max_n + 1)
        print(f"已有: {' '.join(f'{c}:{n}' for c,n in zip(CLASSES,self.counters))}")

    def open_serial(self):
        print(f"打开串口 {self.port} @ {self.baudrate} baud ...")
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate,
                            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                            stopbits=serial.STOPBITS_ONE, timeout=0.5)
        self.ser.setDTR(False); self.ser.setRTS(False)
        time.sleep(0.1); self.ser.reset_input_buffer()
        print("串口已打开")
        return self.ser

    def get_fps(self):
        if len(self.frame_times) < 2: return 0.0
        dt = self.frame_times[-1] - self.frame_times[0]
        return (len(self.frame_times) - 1) / dt if dt > 0 else 0.0

    def try_extract_jpeg(self):
        soi_idx = self.buffer.find(self.SOI)
        if soi_idx == -1: return None, 0
        if soi_idx > 0:
            self.text_buf.extend(self.buffer[:soi_idx])
            self.buffer = self.buffer[soi_idx:]
        eoi_idx = self.buffer.find(self.EOI, 2)
        if eoi_idx == -1: return None, 0
        jpeg_data = bytes(self.buffer[:eoi_idx + 2])
        self.buffer = self.buffer[eoi_idx + 2:]
        arr = np.frombuffer(jpeg_data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img, len(jpeg_data) if img is not None else 0

    def try_extract_rgb565(self):
        magic_idx = self.buffer.find(MAGIC_BYTES)
        if magic_idx == -1: return None, 0
        if magic_idx > 0:
            self.text_buf.extend(self.buffer[:magic_idx])
            self.buffer = self.buffer[magic_idx:]
        if len(self.buffer) < 12: return None, 0
        _, w, h = struct.unpack('>III', bytes(self.buffer[:12]))
        if w == 0 or h == 0 or w > 2048 or h > 2048:
            self.buffer = self.buffer[4:]; return None, 0
        frame_size = 12 + w * h * 2
        if len(self.buffer) < frame_size: return None, 0
        pixel_data = bytes(self.buffer[12:frame_size])
        self.buffer = self.buffer[frame_size:]
        pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape(h, w, 2)
        r = (pixels[:, :, 1] & 0xF8).astype(np.uint8)
        g = ((pixels[:, :, 1] & 0x07) << 5 | (pixels[:, :, 0] & 0xE0) >> 3).astype(np.uint8)
        b = ((pixels[:, :, 0] & 0x1F) << 3).astype(np.uint8)
        return cv2.merge([b, g, r]), frame_size

    def flush_text(self):
        if self.mute: self.text_buf.clear(); return
        if len(self.text_buf) == 0: return
        text = self.text_buf.decode('ascii', errors='replace').strip()
        self.text_buf.clear()
        if text:
            for line in text.splitlines():
                line = line.strip()
                if line: print(f"  [串口] {line}")

    def get_crop_region(self, img):
        """取裁剪区域 (用于画框和放大预览)"""
        half = self.crop_size // 2
        x1 = max(0, self.cx - half)
        y1 = max(0, self.cy - half)
        x2 = min(img.shape[1], self.cx + half)
        y2 = min(img.shape[0], self.cy + half)
        return x1, y1, x2, y2

    def draw_crop_box(self, img):
        """画裁剪框 + 十字"""
        x1, y1, x2, y2 = self.get_crop_region(img)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.drawMarker(img, (self.cx, self.cy), (0, 255, 0),
                       cv2.MARKER_CROSS, 8, 1)
        return x1, y1, x2, y2

    def draw_zoom_preview(self, main_img, crop_img, x1, y1, x2, y2):
        """在右上角叠加裁剪区域的放大预览"""
        if crop_img is None or crop_img.size == 0:
            return
        # 放大到 160x160
        zoom = cv2.resize(crop_img, (160, 160), interpolation=cv2.INTER_NEAREST)
        h_main, w_main = main_img.shape[:2]
        px, py = w_main - 170, 10  # 右上角

        # 半透明背景
        roi = main_img[py:py+170, px:px+170]
        if roi.shape == (170, 170, 3):
            blended = cv2.addWeighted(roi, 0.3, np.full_like(roi, 30), 0.7, 0)
            main_img[py:py+170, px:px+170] = blended

        # 放大的裁剪区域
        main_img[py+5:py+165, px+5:px+165] = zoom
        # 边框
        cv2.rectangle(main_img, (px, py), (px+170, py+170), (0, 255, 255), 1)
        cv2.putText(main_img, "ZOOM", (px+5, py+15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    def save_coords(self):
        data = {"cx": self.cx, "cy": self.cy, "crop_size": self.crop_size}
        with open(COORDS_FILE, 'w') as f:
            json.dump(data, f)
        print(f"  坐标已保存: cx={self.cx}, cy={self.cy}, size={self.crop_size}")

    def run(self):
        self.ser = self.open_serial()
        cv2.namedWindow("DVP Camera (Real-time)", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("DVP Camera (Real-time)", 1024, 768)

        print(f"\n裁剪框: {self.crop_size}x{self.crop_size}px  位置: ({self.cx},{self.cy})")
        print("5=中 8=上 4=左 6=右 2=下 0=闭眼 | 空格=截图 | m=串口 q=退出\n")
        self.start_time = time.time()
        last_flush = time.time()
        CLASSES = ['blind','center','down','left','right','up']
        images_root = os.path.join(os.path.dirname(__file__), '..', 'images')
        for c in CLASSES:
            os.makedirs(os.path.join(images_root, c), exist_ok=True)

        try:
            while True:
                try:
                    waiting = self.ser.in_waiting
                    data = self.ser.read(waiting) if waiting > 0 else b''
                except serial.SerialException as e:
                    print(f"串口错误: {e}"); break

                if data:
                    self.raw_bytes_received += len(data)
                    self.buffer.extend(data)

                    img, size = self.try_extract_rgb565()
                    if img is None:
                        img, size = self.try_extract_jpeg()

                    if img is not None:
                        img = cv2.flip(img, 1)  # 水平镜像，匹配训练数据
                        self.frame_count += 1
                        self.frame_times.append(time.time())
                        fps = self.get_fps()
                        h, w = img.shape[:2]

                        self.last_img = img.copy()
                        self.img_w, self.img_h = w, h

                        # 提取裁剪区域（在灰度转换前）
                        x1, y1, x2, y2 = self.get_crop_region(img)
                        crop_raw = img[y1:y2, x1:x2].copy() if x2>x1 and y2>y1 else None

                        # 显示用的图像
                        if self.grayscale:
                            disp = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                            disp = cv2.cvtColor(disp, cv2.COLOR_GRAY2BGR)
                        else:
                            disp = img

                        # 画框
                        self.draw_crop_box(disp)

                        # 右上角放大预览
                        if crop_raw is not None:
                            self.draw_zoom_preview(disp, crop_raw, x1, y1, x2, y2)

                        # 信息
                        cls_name = ['blind','center','down','left','right','up'][self.class_idx]
                        cnt = self.counters[self.class_idx]
                        gs = "GRAY" if self.grayscale else "COLOR"
                        cv2.putText(disp, f"CLASS: {cls_name} ({cnt}/30) | {w}x{h} | {gs}",
                                    (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                        cv2.putText(disp, f"({self.cx},{self.cy}) {self.crop_size}px [arrows +/-]",
                                    (10, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        cv2.imshow("DVP Camera (Real-time)", disp)

                    if time.time() - last_flush > 1:
                        self.flush_text()
                        if len(self.buffer) > 100000:
                            self.buffer = self.buffer[-10000:]
                        last_flush = time.time()
                else:
                    self.flush_text()

                # ---- 按键 ----
                raw = cv2.waitKeyEx(10)
                moved = False

                if raw == ord('q') or raw == 27:
                    print("用户退出"); break

                elif raw == ord('g'):
                    self.grayscale = not self.grayscale
                    print(f"  灰度: {'开' if self.grayscale else '关'}")
                elif raw == ord('m'):
                    self.mute = not self.mute
                    print(f"  串口文本: {'静音' if self.mute else '显示'}")

                # 小键盘布局: 5=中 8=上 4=左 6=右 2=下 0=闭眼
                elif raw == ord('5'):
                    self.class_idx = 1; print(f"  >>> center ({self.counters[1]}/30) <<<")
                elif raw == ord('8'):
                    self.class_idx = 5; print(f"  >>> up ({self.counters[5]}/30) <<<")
                elif raw == ord('4'):
                    self.class_idx = 3; print(f"  >>> left ({self.counters[3]}/30) <<<")
                elif raw == ord('6'):
                    self.class_idx = 4; print(f"  >>> right ({self.counters[4]}/30) <<<")
                elif raw == ord('2'):
                    self.class_idx = 2; print(f"  >>> down ({self.counters[2]}/30) <<<")
                elif raw == ord('0'):
                    self.class_idx = 0; print(f"  >>> blind ({self.counters[0]}/30) <<<")

                elif raw == 13:   # 回车 = 保存坐标
                    self.save_coords()

                elif raw == ord('i'):   # 'i' = PC本地推理
                    if self.last_img is not None:
                        x1, y1, x2, y2 = self.get_crop_region(self.last_img)
                        eye = self.last_img[y1:y2, x1:x2]
                        eye_gray = cv2.cvtColor(eye, cv2.COLOR_BGR2GRAY)
                        eye_32 = cv2.resize(eye_gray, (32, 32))
                        eye_rgb = cv2.cvtColor(eye_32, cv2.COLOR_GRAY2RGB)
                        inp = eye_rgb.transpose(2,0,1).astype(np.float32)/255.0  # CHW
                        # Lazy-load inference on first use
                        if not hasattr(self, 'ci'):
                            print('  加载推理引擎...')
                            import sys
                            sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
                            from debug_inference import CInference, parse_c_weights
                            w = parse_c_weights(os.path.join(os.path.dirname(__file__), '..',
                                'CH32H417','sdk_ch32h417','DVP','DVP_UART','Common','weights_f32.c'))
                            self.ci = CInference(w)
                        import sys, io
                        old_stdout = sys.stdout
                        sys.stdout = io.StringIO()
                        out = self.ci.run(inp.flatten())
                        sys.stdout = old_stdout
                        cls_name = CLASSES[np.argmax(out)]
                        pcts = ' '.join(f'{n}:{out[i]*100:.0f}%' for i,n in enumerate(CLASSES))
                        print(f'  => {cls_name}  {pcts}')
                    else:
                        print("  暂无图像")

                elif raw == ord('+') or raw == ord('='):
                    self.crop_size = min(200, self.crop_size + 4)
                    print(f"  大小: {self.crop_size}px")
                elif raw == ord('-') or raw == ord('_'):
                    self.crop_size = max(12, self.crop_size - 4)
                    print(f"  大小: {self.crop_size}px")

                # 方向键（边界根据实际图像尺寸动态限制）
                elif raw == 2424832:   # 左
                    self.cx = max(self.crop_size//2, self.cx - self.move_step); moved = True
                elif raw == 2555904:   # 右
                    self.cx = min(self.img_w - self.crop_size//2, self.cx + self.move_step); moved = True
                elif raw == 2490368:   # 上
                    self.cy = max(self.crop_size//2, self.cy - self.move_step); moved = True
                elif raw == 2621440:   # 下
                    self.cy = min(self.img_h - self.crop_size//2, self.cy + self.move_step); moved = True

                # 空格 = 截图保存
                elif raw == 32:
                    if self.last_img is not None:
                        cls_name = ['blind','center','down','left','right','up'][self.class_idx]
                        cnt = self.counters[self.class_idx]
                        images_root = os.path.join(os.path.dirname(__file__), '..', 'images')
                        save_dir = os.path.join(images_root, cls_name)
                        os.makedirs(save_dir, exist_ok=True)
                        filename = f"{cls_name}_{cnt:03d}.jpg"
                        save_path = os.path.join(save_dir, filename)
                        x1, y1, x2, y2 = self.get_crop_region(self.last_img)
                        crop = self.last_img[y1:y2, x1:x2]
                        if crop.size > 0:
                            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                            cv2.imwrite(save_path, crop_gray)
                            self.counters[self.class_idx] += 1
                            print(f"  已保存: {filename}")
                        else:
                            print(f"  裁剪区域为空")

                if moved:
                    print(f"  ({self.cx}, {self.cy})")

        except KeyboardInterrupt:
            print("\n中断退出")
        finally:
            self.flush_text()
            self.ser.close()
            cv2.destroyAllWindows()
            elapsed = time.time() - self.start_time if self.start_time else 0
            avg_fps = self.frame_count / elapsed if elapsed > 0 and self.frame_count > 0 else 0
            print(f"会话结束: {elapsed:.0f}s | {self.frame_count} 帧 | "
                  f"收{self.raw_bytes_received/1024:.1f}KB | 平均 {avg_fps:.1f} FPS")


if __name__ == "__main__":
    DualModeViewer(SERIAL_PORT, BAUDRATE).run()
