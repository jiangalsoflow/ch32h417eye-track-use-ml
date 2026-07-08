"""
PC 端: 接收 MCU JPEG → 解码 → 裁剪 → 推理 → 显示结果
MCU 只发 JPEG，不需要接收任何数据
"""
import serial, cv2, numpy as np, time, os, sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

SERIAL_PORT = "COM3"
BAUDRATE = 2000000
COORDS_FILE = os.path.join(os.path.dirname(__file__), 'pc_infer_coords.json')
if os.path.exists(COORDS_FILE):
    import json as _json
    with open(COORDS_FILE) as _f:
        _c = _json.load(_f)
    EYE_CX, EYE_CY, CROP_SZ = _c.get('cx', 412), _c.get('cy', 312), _c.get('crop', 40)
    del _json, _f, _c
else:
    EYE_CX, EYE_CY, CROP_SZ = 412, 312, 40
CLASSES = ["blind", "center", "down", "left", "right", "up"]
SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_new')
CLASS_KEYS = {ord('0'): 'blind', ord('5'): 'center', ord('2'): 'down',
              ord('4'): 'left', ord('6'): 'right', ord('8'): 'up'}
current_class = 'center'
debug_idx = 0
# 初始化保存目录和计数器
for cls in CLASSES:
    os.makedirs(os.path.join(SAVE_DIR, cls), exist_ok=True)
save_counters = {}
for cls in CLASSES:
    d = os.path.join(SAVE_DIR, cls)
    existing = [f for f in os.listdir(d) if f.endswith('.jpg')]
    save_counters[cls] = len(existing)

# 加载模型
print("加载模型...")
model = tf.keras.models.load_model(os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5'))
model.predict(np.zeros((1,32,32,3), dtype=np.float32), verbose=0)
print("完成\n")

print(f"连接 {SERIAL_PORT} @ {BAUDRATE} ...")
ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.5)
ser.setDTR(False); ser.setRTS(False)
time.sleep(0.5); ser.reset_input_buffer()
print("已连接\n")

SOI, EOI = b'\xff\xd8', b'\xff\xd9'
buf = bytearray()
frame_count = 0
last_time = time.time()
count = {c: 0 for c in CLASSES}

while True:
    waiting = ser.in_waiting
    if waiting > 0:
        buf.extend(ser.read(waiting))

    soi_idx = buf.find(SOI)
    if soi_idx == -1:
        if len(buf) > 200000: buf.clear()
        time.sleep(0.005)
        continue
    if soi_idx > 0: buf = buf[soi_idx:]
    eoi_idx = buf.find(EOI, 2)
    if eoi_idx == -1:
        time.sleep(0.005)
        continue

    jpeg_data = bytes(buf[:eoi_idx + 2])
    buf = buf[eoi_idx + 2:]

    img = cv2.imdecode(np.frombuffer(jpeg_data, np.uint8), cv2.IMREAD_COLOR)
    if img is None: continue
    img = cv2.flip(img, 1)
    h, w = img.shape[:2]

    # 裁剪眼睛区域
    half = CROP_SZ // 2
    x1, y1 = max(0, EYE_CX-half), max(0, EYE_CY-half)
    x2, y2 = min(w, EYE_CX+half), min(h, EYE_CY+half)
    eye_crop = img[y1:y2, x1:x2]
    if eye_crop.shape[0] < CROP_SZ or eye_crop.shape[1] < CROP_SZ:
        eye_crop = cv2.resize(eye_crop, (CROP_SZ, CROP_SZ))

    eye_gray = cv2.cvtColor(eye_crop, cv2.COLOR_BGR2GRAY)
    eye_32 = cv2.resize(eye_gray, (32, 32))
    eye_rgb = np.stack([eye_32]*3, axis=-1).astype(np.float32)/255.0

    out = model.predict(np.expand_dims(eye_rgb, 0), verbose=0)[0]
    best = CLASSES[np.argmax(out)]
    pct = out[np.argmax(out)] * 100
    count[best] += 1
    frame_count += 1

    # FPS
    now = time.time()
    fps = frame_count / (now - last_time) if now > last_time else 0
    if frame_count > 30:
        frame_count = 0; last_time = now

    # 显示
    disp = img.copy()
    cv2.rectangle(disp, (x1,y1), (x2,y2), (0,255,0), 2)
    zoom = cv2.resize(eye_gray, (160,160), interpolation=cv2.INTER_NEAREST)
    zoom = cv2.cvtColor(zoom, cv2.COLOR_GRAY2BGR)
    disp[10:170, w-170:w-10] = zoom

    cv2.putText(disp, f"{best} {pct:.0f}%", (10,30),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2)
    cv2.putText(disp, f"({EYE_CX},{EYE_CY}) {fps:.1f}fps", (10,60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1)
    for i, c in enumerate(CLASSES):
        cv2.putText(disp, f"{c}: {count[c]}", (10, 90+i*20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180,180,180), 1)
    cv2.imshow("Eye Tracker (PC Inference)", disp)

    raw = cv2.waitKeyEx(1)
    key = raw & 0xFF
    if key == ord('q') or raw == 27: break
    elif key in CLASS_KEYS:
        current_class = CLASS_KEYS[key]
        print(f"  类别切换: {current_class}")
    elif key == 32:  # 空格保存
        cnt = save_counters[current_class]
        fname = f"{current_class}_{cnt:03d}.jpg"
        fpath = os.path.join(SAVE_DIR, current_class, fname)
        cv2.imwrite(fpath, eye_gray)
        save_counters[current_class] += 1
        print(f"  已保存: {fname}")
    elif raw == 2424832: EYE_CX = max(CROP_SZ//2, EYE_CX - 2)  # 左
    elif raw == 2555904: EYE_CX = min(w - CROP_SZ//2, EYE_CX + 2)  # 右
    elif raw == 2490368: EYE_CY = max(CROP_SZ//2, EYE_CY - 2)  # 上
    elif raw == 2621440: EYE_CY = min(h - CROP_SZ//2, EYE_CY + 2)  # 下
    elif key == ord('s'):  # 调试保存，自动编号
        fname = f'debug_{debug_idx:02d}.jpg'
        cv2.imwrite(fname, eye_gray)
        print(f"  保存: {fname} avg={eye_gray.mean():.0f}")
        debug_idx += 1
    elif key == ord('+') or key == ord('='): CROP_SZ = min(100, CROP_SZ + 4)
    elif key == ord('-') or key == ord('_'): CROP_SZ = max(20, CROP_SZ - 4)

ser.close()
cv2.destroyAllWindows()
# 保存坐标
import json
with open(COORDS_FILE, 'w') as f:
    json.dump({'cx': EYE_CX, 'cy': EYE_CY, 'crop': CROP_SZ}, f)
print(f"坐标已保存: ({EYE_CX}, {EYE_CY}) size={CROP_SZ}")
