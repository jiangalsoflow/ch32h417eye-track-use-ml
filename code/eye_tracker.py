"""
眼动追踪实时显示器 — 读取串口推理结果并可视化
"""
import serial, time, sys

SERIAL_PORT = "COM3"
BAUDRATE = 2000000

DIRECTIONS = ["blind", "center", "down", "left", "right", "up"]

# 箭头符号映射
ARROWS = {
    "blind":  " x ",
    "center": " + ",
    "down":   " v ",
    "left":   " < ",
    "right":  " > ",
    "up":     " ^ ",
}

def main():
    print(f"连接 {SERIAL_PORT} @ {BAUDRATE} ...")
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)
    ser.setDTR(False)
    ser.setRTS(False)
    time.sleep(0.5)
    ser.reset_input_buffer()
    print("已连接，等待推理数据...\n")

    count = {d: 0 for d in DIRECTIONS}
    total = 0
    last_dir = None
    start_time = time.time()

    try:
        while True:
            line = ser.readline()
            if not line:
                continue

            text = line.decode("ascii", errors="replace").strip()
            if not text:
                continue

            # 解析方向（取第一个词）
            direction = text.split()[0].lower()
            if direction not in DIRECTIONS:
                continue  # 跳过非推理输出

            total += 1
            count[direction] += 1
            arrow = ARROWS.get(direction, " ? ")

            # 实时显示
            pct = count[direction] / total * 100
            print(f"  {arrow}  {direction:8s}  ({count[direction]}/{total} = {pct:.0f}%)")

            last_dir = direction

    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        fps = total / elapsed if elapsed > 0 else 0

        print(f"\n\n--- 统计 ---")
        print(f"总帧数: {total}")
        print(f"运行时间: {elapsed:.1f} 秒")
        print(f"平均速率: {fps:.1f} 帧/秒")
        print()
        for d in DIRECTIONS:
            if count[d] > 0:
                pct = count[d] / total * 100
                print(f"  {d:8s}: {count[d]:4d} ({pct:.1f}%)")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
