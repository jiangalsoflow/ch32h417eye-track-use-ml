"""Validate V3: raw Otsu stats, no morphological ops. """
import os
import sys
import numpy as np
import cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

def detect_v3(mirrored_crop):
    """
    Pure Otsu statistics. No morphological ops.
    mirrored_crop: uint8 (40,40), horizontally flipped.
    """
    mean_val = float(np.mean(mirrored_crop))
    std_val = float(np.std(mirrored_crop))

    # Blind: very bright + low texture
    if mean_val > 100 and std_val < 28:
        return 0

    blur = cv2.GaussianBlur(mirrored_crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    thresh_f = thresh.astype(np.float32) / 255.0  # 0 or 1

    dark_total = float(np.sum(thresh_f))
    dark_pct = dark_total / 1600.0

    col_dk = np.sum(thresh_f, axis=0)   # (40,)
    row_dk = np.sum(thresh_f, axis=1)   # (40,)

    left_sum  = float(np.sum(col_dk[:16]))
    right_sum = float(np.sum(col_dk[24:]))
    top_sum   = float(np.sum(row_dk[:13]))
    bot_sum   = float(np.sum(row_dk[27:]))

    lr = left_sum / max(right_sum, 0.5)
    rl = right_sum / max(left_sum, 0.5)
    tb = top_sum / max(bot_sum, 0.5)
    bt = bot_sum / max(top_sum, 0.5)

    # too few dark pixels → blind or up
    if dark_total < 30:
        if mean_val > 70:
            return 0  # blind (bright, no dark)
        return 5  # up (darker, but very little dark → iris concealed)

    # blind fallback: very bright
    if mean_val > 105:
        return 0

    # down: bottom 1/3 has much more dark than top 1/3
    if bt > 1.8 or (bot_sum > top_sum * 1.5 and dark_pct > 0.15):
        return 2

    # up: top 1/3 heavy, low dark%
    if tb > 2.5 and dark_pct < 0.20:
        return 5

    # left: left 40% has much more dark than right 40%
    if lr > 2.2:
        return 3

    # right: right 40% has more dark
    if rl > 1.6:
        return 4

    # center: balanced-ish
    return 1


def main():
    print("=" * 70)
    print("Validating V3 Algorithm on images_latest/")
    print("Pure Otsu dark pixel projection, no morphology")
    print("=" * 70)

    confusion = np.zeros((6, 6), dtype=int)
    per_class = {cls: {'total': 0, 'correct': 0} for cls in CLASSES}

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
            pred = detect_v3(mirrored)
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

    print("\n" + "=" * 70)
    print("Misclassified:")
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
            pred = detect_v3(mirrored)
            if pred != ti:
                dark_pct = get_dark_pct(mirrored)
                print(f"  {tcls:>8}/ {f:30s} -> pred {CLASSES[pred]:>6}  (dark%={dark_pct:.3f})")


def get_dark_pct(crop):
    blur = cv2.GaussianBlur(crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return float(np.sum(thresh / 255)) / 1600.0


if __name__ == '__main__':
    main()
