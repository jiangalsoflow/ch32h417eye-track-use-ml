import os
import sys
import cv2
import shutil
import glob
import numpy as np
import argparse

CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

COLORS = [
    (0, 165, 255),   # blind  - orange
    (0, 255, 0),     # center - green
    (0, 200, 255),   # down   - yellow
    (255, 0, 0),     # left   - blue
    (0, 0, 255),     # right  - red
    (255, 0, 255),   # up     - magenta
]

KEY_MAP = {
    ord('1'): 0, ord('2'): 1, ord('3'): 2,
    ord('4'): 3, ord('5'): 4, ord('6'): 5,
}


def get_unclassified(src_dir):
    files = []
    if not os.path.isdir(src_dir):
        return files
    for f in sorted(os.listdir(src_dir)):
        fpath = os.path.join(src_dir, f)
        if os.path.isfile(fpath) and f.lower().endswith('.jpg'):
            files.append(f)
    return files


def ensure_dirs(src_dir):
    for cls in CLASSES:
        d = os.path.join(src_dir, cls)
        if not os.path.isdir(d):
            os.makedirs(d)


def move_file(fname, cls_name, src_dir):
    src = os.path.join(src_dir, fname)
    dst_dir = os.path.join(src_dir, cls_name)
    dst = os.path.join(dst_dir, fname)
    shutil.move(src, dst)


def main():
    parser = argparse.ArgumentParser(description='Manual classifier for eye images')
    parser.add_argument('--dir', type=str,
                        default=os.path.join(os.path.dirname(__file__), '..', 'images_latest'),
                        help='Directory containing .jpg files to classify')
    args = parser.parse_args()
    src_dir = os.path.abspath(args.dir)

    if not os.path.isdir(src_dir):
        print(f"ERROR: directory not found: {src_dir}")
        sys.exit(1)

    ensure_dirs(src_dir)

    files = get_unclassified(src_dir)
    total_initial = len(files)
    if not files:
        print(f"No unclassified images in {src_dir}")
        return

    total = total_initial
    idx = 0
    cv2.namedWindow('Classify Latest', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Classify Latest', 520, 440)

    while True:
        files = get_unclassified(src_dir)
        total = len(files)

        if idx >= total:
            idx = max(0, total - 1)
        if total == 0:
            break

        fname = files[idx]
        fpath = os.path.join(src_dir, fname)
        img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            idx += 1
            continue

        canvas = np.zeros((440, 520, 3), dtype=np.uint8)

        img_scaled = cv2.resize(img, (360, 360), interpolation=cv2.INTER_NEAREST)
        img_bgr = cv2.cvtColor(img_scaled, cv2.COLOR_GRAY2BGR)
        canvas[10:370, 10:370] = img_bgr

        cv2.putText(canvas, f"[{idx + 1}/{total}] {fname}",
                    (10, 398), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        classified_count = total_initial - total
        cv2.putText(canvas, f"done: {classified_count}  rem: {total}",
                    (10, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)

        y_btn = 20
        for i, cls in enumerate(CLASSES):
            color = COLORS[i]
            cv2.putText(canvas, f"{i + 1}: {cls}", (400, y_btn),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            y_btn += 45

        cv2.putText(canvas, "BKSP: prev", (400, y_btn),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        cv2.putText(canvas, "DEL: skip", (400, y_btn + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
        cv2.putText(canvas, "Q: quit", (400, y_btn + 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        cv2.imshow('Classify Latest', canvas)
        key = cv2.waitKey(0) & 0xFF

        if key == ord('q') or key == 27:
            break
        elif key == 8:
            idx = max(0, idx - 1)
        elif key == 255:
            idx += 1
        elif key == ord('r'):
            idx = 0
        elif key in KEY_MAP:
            cls_idx = KEY_MAP[key]
            cls_name = CLASSES[cls_idx]
            move_file(fname, cls_name, src_dir)
            print(f"[{idx + 1}/{total}] {fname} -> {cls_name}")
            if idx >= total - 1:
                idx = max(0, total - 2)
        else:
            continue

    cv2.destroyAllWindows()
    remaining = len(get_unclassified(src_dir))
    print(f"\nDone. {total_initial - remaining} classified, {remaining} remaining.")


if __name__ == '__main__':
    main()
