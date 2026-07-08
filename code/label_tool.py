import os
import sys
import cv2
import shutil

RAW_DIR = r'E:\dvp-uart\Match\collected_data\raw'
LABEL_DIR = r'E:\dvp-uart\Match\collected_data\labeled'

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
KEY_MAP = {ord('1'): 0, ord('2'): 1, ord('3'): 2, ord('4'): 3, ord('5'): 4, ord('6'): 5}

def get_unlabeled():
    labeled = set()
    for cls in CLASSES:
        cls_dir = os.path.join(LABEL_DIR, cls)
        if os.path.isdir(cls_dir):
            for f in os.listdir(cls_dir):
                labeled.add(f)
    unlabeled = []
    for f in sorted(os.listdir(RAW_DIR)):
        if f.lower().endswith('.jpg') and f not in labeled:
            unlabeled.append(f)
    return unlabeled

def main():
    files = get_unlabeled()
    if not files:
        print("All images labeled!")
        return

    total = len(files)
    idx = 0
    cv2.namedWindow('Label Tool', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Label Tool', 320, 320)

    while 0 <= idx < len(files):
        fname = files[idx]
        fpath = os.path.join(RAW_DIR, fname)
        img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"Cannot read {fpath}, skipping")
            idx += 1
            continue

        h, w = img.shape[:2]
        scale = min(280 / w, 280 / h)
        if scale < 1:
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))

        display = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        oh, ow = display.shape[:2]
        info = f"[{idx+1}/{total}] {fname}"
        cv2.putText(display, info, (5, oh - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        shortcut_str = "  ".join(f"{i+1}={CLASSES[i]}" for i in range(6))
        cv2.putText(display, shortcut_str, (5, oh - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 255, 100), 1)
        cv2.putText(display, "r: prev  q: quit", (5, oh - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1)

        cv2.imshow('Label Tool', display)
        key = cv2.waitKey(0) & 0xFF

        if key == ord('q') or key == 27:
            break
        elif key == ord('r'):
            idx -= 1
            continue
        elif key in KEY_MAP:
            cls_idx = KEY_MAP[key]
            cls_name = CLASSES[cls_idx]
            dst_dir = os.path.join(LABEL_DIR, cls_name)
            dst_path = os.path.join(dst_dir, fname)
            shutil.copy2(fpath, dst_path)
            print(f"[{idx+1}/{total}] {fname} -> {cls_name}")
            idx += 1
            continue
        else:
            continue

    cv2.destroyAllWindows()
    remaining = len(get_unlabeled())
    print(f"Done. {total - remaining} labeled, {remaining} remaining.")

if __name__ == '__main__':
    main()
