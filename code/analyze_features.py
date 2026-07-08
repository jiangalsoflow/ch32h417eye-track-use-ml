import os
import sys
import numpy as np
import cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

def analyze_image(img):
    """Extract features from 40x40 grayscale image. Returns dict."""
    h, w = 40, 40
    r = {}

    r['mean'] = float(np.mean(img))
    r['std'] = float(np.std(img))
    r['min'] = int(np.min(img))
    r['max'] = int(np.max(img))

    mid = np.median(img)
    dark_mask = (img < mid).astype(np.float32)
    dark_pct = float(np.mean(dark_mask))
    r['dark_pct'] = dark_pct

    # Row-projections: sum of dark pixels per row (top 13 rows vs bottom 27)
    row_dark = np.sum(dark_mask, axis=1)
    r['top_dark'] = float(np.mean(row_dark[:13]))
    r['bot_dark'] = float(np.mean(row_dark[13:]))

    # Col-projections: sum of dark pixels per col (left 16 vs right 24)
    col_dark = np.sum(dark_mask, axis=0)
    r['left_dark'] = float(np.mean(col_dark[:16]))
    r['right_dark'] = float(np.mean(col_dark[16:]))

    # Darkest pixel position (global minimum)
    min_idx = np.argmin(img)
    r['min_y'] = min_idx // 40
    r['min_x'] = min_idx % 40

    # Otsu dark region analysis
    blur = cv2.GaussianBlur(img, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel5)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        opened, connectivity=8)

    best_area = 0
    best_cx = -1
    best_cy = -1
    best_circ = 0

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < 3 or area > 300:
            continue
        comp_mask = (labels == i).astype(np.uint8)
        conts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not conts:
            continue
        c = conts[0]
        area_c = cv2.contourArea(c)
        peri = cv2.arcLength(c, True)
        circ = 4 * np.pi * area_c / (peri * peri) if peri > 0 else 0
        if circ < 0.3:
            continue
        cx, cy = centroids[i]
        dist = np.sqrt((cx - 19.5) ** 2 + (cy - 19.5) ** 2)
        if dist > 20:
            continue
        if area_c > best_area:
            best_area = area_c
            best_cx = cx
            best_cy = cy
            best_circ = circ

    r['pupil_area'] = best_area
    r['pupil_cx'] = best_cx
    r['pupil_cy'] = best_cy
    r['pupil_circ'] = best_circ
    r['dx'] = best_cx - 19.5 if best_cx > 0 else 0
    r['dy'] = best_cy - 19.5 if best_cy > 0 else 0

    # Simple row/col projection of raw grayscale (not dark mask)
    r['raw_top_mean'] = float(np.mean(img[:13, :]))
    r['raw_bot_mean'] = float(np.mean(img[13:, :]))
    r['raw_left_mean'] = float(np.mean(img[:, :16]))
    r['raw_right_mean'] = float(np.mean(img[:, 16:]))

    # Upper-left vs upper-right vs lower-left vs lower-right
    r['quad_tl'] = float(np.mean(img[:20, :20]))
    r['quad_tr'] = float(np.mean(img[:20, 20:]))
    r['quad_bl'] = float(np.mean(img[20:, :20]))
    r['quad_br'] = float(np.mean(img[20:, 20:]))

    return r


def main():
    print("=" * 70)
    print("Eye Direction Feature Analysis")
    print("=" * 70)

    all_features = {cls: [] for cls in CLASSES}

    for cls in CLASSES:
        d = os.path.join(BASE_DIR, cls)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.lower().endswith('.jpg'):
                continue
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            ft = analyze_image(img)
            ft['fname'] = f
            all_features[cls].append(ft)

    # ==== PER-CLASS STATISTICS ====
    print(f"\n{'Class':>8} | {'N':>3} | {'Mean':>6} | {'Std':>5} | "
          f"{'top_dk':>6} | {'bot_dk':>6} | {'l_dk':>6} | {'r_dk':>6} | "
          f"{'dx':>6} | {'dy':>6} | {'area':>5} | {'circ':>5}")
    print("-" * 90)

    for cls in CLASSES:
        fts = all_features[cls]
        if not fts:
            continue
        n = len(fts)

        mean_val = np.mean([f['mean'] for f in fts])
        std_val = np.mean([f['std'] for f in fts])
        top_dk = np.mean([f['top_dark'] for f in fts])
        bot_dk = np.mean([f['bot_dark'] for f in fts])
        l_dk = np.mean([f['left_dark'] for f in fts])
        r_dk = np.mean([f['right_dark'] for f in fts])

        dx_vals = [f['dx'] for f in fts if f['dx'] != 0]
        dy_vals = [f['dy'] for f in fts if f['dy'] != 0]
        dx_m = np.mean(dx_vals) if dx_vals else 0
        dy_m = np.mean(dy_vals) if dy_vals else 0

        area_vals = [f['pupil_area'] for f in fts if f['pupil_area'] > 0]
        area_m = np.mean(area_vals) if area_vals else 0
        circ_vals = [f['pupil_circ'] for f in fts if f['pupil_circ'] > 0]
        circ_m = np.mean(circ_vals) if circ_vals else 0

        print(f"{cls:>8} | {n:>3} | {mean_val:>6.1f} | {std_val:>5.1f} | "
              f"{top_dk:>6.1f} | {bot_dk:>6.1f} | {l_dk:>6.1f} | {r_dk:>6.1f} | "
              f"{dx_m:>+6.1f} | {dy_m:>+6.1f} | {area_m:>5.1f} | {circ_m:>5.2f}")

    # ==== DETAILED FEATURES ====
    print("\n" + "=" * 70)
    print("Quadrant brightness (TL=top-left, TR=top-right, BL=bot-left, BR=bot-right)")
    print("=" * 70)
    print(f"{'Class':>8} | {'N':>3} | {'TL':>6} | {'TR':>6} | {'BL':>6} | {'BR':>6} | "
          f"{'TL-BR':>7} | {'TR-BL':>7}")
    print("-" * 75)

    for cls in CLASSES:
        fts = all_features[cls]
        if not fts:
            continue
        tl = np.mean([f['quad_tl'] for f in fts])
        tr = np.mean([f['quad_tr'] for f in fts])
        bl = np.mean([f['quad_bl'] for f in fts])
        br = np.mean([f['quad_br'] for f in fts])
        print(f"{cls:>8} | {len(fts):>3} | {tl:>6.1f} | {tr:>6.1f} | {bl:>6.1f} | "
              f"{br:>6.1f} | {tl - br:>+7.1f} | {tr - bl:>+7.1f}")

    # ==== RAW MEAN PROJECTIONS ====
    print("\n" + "=" * 70)
    print("Raw grayscale half comparisons")
    print("=" * 70)
    print(f"{'Class':>8} | {'N':>3} | {'top_raw':>7} | {'bot_raw':>7} | "
          f"{'T-B':>6} | {'left_raw':>8} | {'right_raw':>8} | {'L-R':>6}")
    print("-" * 70)

    for cls in CLASSES:
        fts = all_features[cls]
        if not fts:
            continue
        tr = np.mean([f['raw_top_mean'] for f in fts])
        br = np.mean([f['raw_bot_mean'] for f in fts])
        lr = np.mean([f['raw_left_mean'] for f in fts])
        rr = np.mean([f['raw_right_mean'] for f in fts])
        print(f"{cls:>8} | {len(fts):>3} | {tr:>7.1f} | {br:>7.1f} | "
              f"{tr - br:>+6.1f} | {lr:>8.1f} | {rr:>8.1f} | {lr - rr:>+6.1f}")

    # ==== DARKEST PIXEL POSITION ====
    print("\n" + "=" * 70)
    print("Darkest pixel position (raw image, 40x40)")
    print("=" * 70)
    print(f"{'Class':>8} | {'min_y':>6} | {'min_x':>6} | {'min_val':>7}")
    print("-" * 35)

    for cls in CLASSES:
        fts = all_features[cls]
        if not fts:
            continue
        my = np.mean([f['min_y'] for f in fts])
        mx = np.mean([f['min_x'] for f in fts])
        mv = np.mean([f['min'] for f in fts])
        print(f"{cls:>8} | {my:>6.1f} | {mx:>6.1f} | {mv:>7.1f}")

    # ==== PUPIL DETECTED STATS ====
    print("\n" + "=" * 70)
    print("Pupil detection success rate & dx/dy distribution")
    print("=" * 70)
    print(f"{'Class':>8} | {'N':>3} | {'detected':>8} | {'dx_mean':>7} | {'dx_std':>6} | "
          f"{'dy_mean':>7} | {'dy_std':>6} | {'area_mean':>9}")
    print("-" * 70)

    for cls in CLASSES:
        fts = all_features[cls]
        n = len(fts)
        detected = sum(1 for f in fts if f['pupil_area'] > 0)
        dxs = [f['dx'] for f in fts if f['dx'] != 0]
        dys = [f['dy'] for f in fts if f['dy'] != 0]
        areas = [f['pupil_area'] for f in fts if f['pupil_area'] > 0]
        dx_m = np.mean(dxs) if dxs else 0
        dx_s = np.std(dxs) if dxs else 0
        dy_m = np.mean(dys) if dys else 0
        dy_s = np.std(dys) if dys else 0
        ar_m = np.mean(areas) if areas else 0
        print(f"{cls:>8} | {n:>3} | {detected:>5}/{n:<3} | {dx_m:>+7.2f} | {dx_s:>6.2f} | "
              f"{dy_m:>+7.2f} | {dy_s:>6.2f} | {ar_m:>9.1f}")


if __name__ == '__main__':
    main()
