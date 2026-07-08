"""Validate new area-based algorithm against images_latest/."""
import os
import sys
import numpy as np
import cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

def detect_v2(mirrored_crop):
    """
    New algorithm: area-based + dark projection. Returns class_idx.
    mirrored_crop: uint8 (40,40), horizontally flipped to match training convention.
    """
    mean_val = float(np.mean(mirrored_crop))
    std_val = float(np.std(mirrored_crop))

    # Step 1: Blind
    if mean_val > 85 and std_val < 30:
        return 0  # blind

    # Step 2: Otsu + 5x5 open → dark region
    blur = cv2.GaussianBlur(mirrored_crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel5)

    # Find best pupil component
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        opened, connectivity=8)

    best_area = 0
    best_idx = 0
    best_cx = 19.5
    best_cy = 19.5

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 3 or area > 400:
            continue
        comp_mask = (labels == i).astype(np.uint8)
        conts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not conts:
            continue
        c = conts[0]
        peri = cv2.arcLength(c, True)
        if peri == 0:
            continue
        circ = 4 * np.pi * cv2.contourArea(c) / (peri * peri)
        if circ < 0.30:
            continue
        cx, cy = centroids[i]
        dist = np.sqrt((cx - 19.5) ** 2 + (cy - 19.5) ** 2)
        if dist > 20:
            continue
        if cy < 14:  # eyebrow rejection
            continue
        if area > best_area:
            best_area = area
            best_idx = i
            best_cx = cx
            best_cy = cy

    if best_area < 3:
        return 0  # no dark region → blind

    # Step 3: Dark projection on opened image
    comp_mask = (labels == best_idx).astype(np.uint8)

    # Also use ALL opened dark pixels (not just best component)
    # for computing lateral bias (more robust)
    row_dk = np.sum(opened / 255, axis=1)  # (40,)
    col_dk = np.sum(opened / 255, axis=0)  # (40,)

    left_dk = float(np.sum(col_dk[:20]))
    right_dk = float(np.sum(col_dk[20:]))

    # Step 4: Classification
    # up: iris concealed by eyelid → dark area very small
    if best_area < 50:
        return 5  # up

    # down: iris fully exposed → dark area large
    if best_area > 170:
        return 2  # down

    # left: pupil on left side of mirrored image
    # (in mirrored: left_dk = right side of raw → class "left")
    if left_dk > 0 and left_dk > right_dk * 1.4:
        return 3  # left

    # right: pupil on right side of mirrored image
    if right_dk > 0 and right_dk > left_dk * 1.2:
        return 4  # right

    return 1  # center


def main():
    print("=" * 70)
    print("Validating V2 Algorithm on images_latest/")
    print("Features: area(up<50, down>170) + dark projection(l/r ratio)")
    print("=" * 70)

    confusion = np.zeros((6, 6), dtype=int)
    per_class = {cls: {'total': 0, 'correct': 0, 'areas': [], 'l_ratio': []} for cls in CLASSES}

    for ti, tcls in enumerate(CLASSES):
        d = os.path.join(BASE_DIR, tcls)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith('.jpg'):
                continue
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            # Mirror: training convention
            mirrored = cv2.flip(img, 1)

            pred = detect_v2(mirrored)
            confusion[ti][pred] += 1
            per_class[tcls]['total'] += 1
            if pred == ti:
                per_class[tcls]['correct'] += 1

    print(f"\n{'True':>8} | {'Pred':>6} " + " | ".join(f"{c:>5}" for c in CLASSES) + f" | {'Acc':>6}")
    print("-" * 70)
    total_correct = 0
    total_all = 0
    for ti, tcls in enumerate(CLASSES):
        n = per_class[tcls]['total']
        if n == 0:
            continue
        correct = per_class[tcls]['correct']
        total_correct += correct
        total_all += n
        acc = correct / n if n > 0 else 0
        row = [f"{confusion[ti][pi]:>5d}" for pi in range(6)]
        print(f"{tcls:>8} | {'':>6} " + " ".join(row) + f" | {acc:>5.1%}")

    print("-" * 70)
    if total_all > 0:
        print(f"{'TOTAL':>8} | {'':>6} " + " ".join(f"{np.sum(confusion[:, pi]):>5d}" for pi in range(6))
              + f" | {total_correct / total_all:>5.1%}")

    # Detailed: show misclassified examples
    print("\n" + "=" * 70)
    print("Misclassified examples:")
    print("=" * 70)
    for ti, tcls in enumerate(CLASSES):
        d = os.path.join(BASE_DIR, tcls)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith('.jpg'):
                continue
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            mirrored = cv2.flip(img, 1)
            pred = detect_v2(mirrored)
            if pred != ti:
                print(f"  {tcls:>8}/ {f:30s} -> predicted {CLASSES[pred]:>6}")

    # Per-class dark area stats
    print("\n" + "=" * 70)
    print("Dark area distribution by class (on mirrored, opened best component)")
    print("=" * 70)
    for cls in CLASSES:
        d = os.path.join(BASE_DIR, cls)
        if not os.path.isdir(d):
            continue
        areas = []
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith('.jpg'):
                continue
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            mirrored = cv2.flip(img, 1)
            blur = cv2.GaussianBlur(mirrored, (3, 3), 0)
            _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            kernel5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel5)
            num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
            best_area = 0
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                if 3 < area < 400 and area > best_area:
                    best_area = area
            areas.append(best_area)
        areas = np.array(areas)
        print(f"  {cls:>8}: n={len(areas):>3}  mean={areas.mean():>6.1f}  "
              f"min={areas.min():>5.0f}  max={areas.max():>5.0f}  "
              f"<50: {np.sum(areas < 50):>2}  >170: {np.sum(areas > 170):>2}")


if __name__ == '__main__':
    main()
