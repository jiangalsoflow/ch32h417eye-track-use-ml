"""Validate V5: morphology pipeline + multi-feature decision tree."""
import os, sys, numpy as np, cv2, json

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

# ── tunable parameters ──────────────────────────────────
P = {
    'blind_mean':      95,      # mean > this → blind candidate
    'blind_std':        28,     # std < this → blind candidate
    'comp_min_area':     3,     # min component area
    'comp_max_area':   400,     # max component area
    'comp_min_circ':     0.30,  # min circularity
    'comp_max_dist':    20,     # max distance from center
    'comp_min_cy':      12,     # eyebrow rejection (y coordinate)
    'up_area_max':      55,     # area < this → up candidate
    'up_top_ratio':      0.55,  # top half dark ratio > this → up
    'down_area_min':   150,     # area > this → down candidate
    'left_ratio':        0.55,  # left half dark ratio > this → left
    'right_ratio':       0.50,  # right half dark ratio > this → right
    'center_dx_max':     3.0,   # |dx| < this → center x
    'center_dy_max':     3.0,   # |dy| < this → center y
    'cx_left':          17,     # cx < this → left (fallback)
    'cx_right':         22,     # cx > this → right (fallback)
    'cy_up':            17,     # cy < this → up (fallback)
    'cy_down':          22,     # cy > this → down (fallback)
}


def extract_features(mirrored_crop):
    """Returns dict of features, or None if no pupil found."""
    mean_val = float(np.mean(mirrored_crop))
    std_val = float(np.std(mirrored_crop))

    blur = cv2.GaussianBlur(mirrored_crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Step 3: 3x3 close → fill small holes inside pupil (iRIS reflection)
    kernel3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel3)

    # Step 4: 5x5 open → kill lashes, keep pupil
    kernel5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel5)

    # Global dark pixel stats (on opened image)
    dark_f = (opened > 0).astype(np.float32)
    dark_total = float(np.sum(dark_f))
    dark_pct = dark_total / 1600.0

    col_dk = np.sum(dark_f, axis=0)
    row_dk = np.sum(dark_f, axis=1)

    left_total = float(np.sum(col_dk[:20]))
    right_total = float(np.sum(col_dk[20:]))
    top_total = float(np.sum(row_dk[:20]))
    bot_total = float(np.sum(row_dk[20:]))

    if dark_total > 0:
        left_ratio = left_total / dark_total
        top_ratio = top_total / dark_total
    else:
        left_ratio = 0.5
        top_ratio = 0.5

    # Step 5: connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        opened, connectivity=8)

    best_area = 0
    best_cx = -1
    best_cy = -1
    best_circ = 0

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < P['comp_min_area'] or area > P['comp_max_area']:
            continue

        comp_mask = (labels == i).astype(np.uint8)
        conts, _ = cv2.findContours(comp_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not conts:
            continue
        c = conts[0]
        area_c = cv2.contourArea(c)
        peri = cv2.arcLength(c, True)
        if peri == 0:
            continue
        circ = 4 * np.pi * area_c / (peri * peri)
        if circ < P['comp_min_circ']:
            continue

        cx, cy = centroids[i]
        dist = np.sqrt((cx - 19.5) ** 2 + (cy - 19.5) ** 2)
        if dist > P['comp_max_dist']:
            continue
        if cy < P['comp_min_cy']:
            continue

        if area > best_area:
            best_area = area
            best_cx = cx
            best_cy = cy
            best_circ = circ

    return {
        'mean': mean_val, 'std': std_val,
        'dark_pct': dark_pct, 'dark_total': dark_total,
        'left_ratio': left_ratio, 'top_ratio': top_ratio,
        'pupil_area': best_area, 'pupil_cx': best_cx,
        'pupil_cy': best_cy, 'pupil_circ': best_circ,
        'dx': best_cx - 19.5 if best_cx > 0 else 0,
        'dy': best_cy - 19.5 if best_cy > 0 else 0,
    }


def classify(f):
    """Decision tree using extracted features. Returns class_idx."""
    # Blind: bright + low texture
    if f['mean'] > P['blind_mean'] and f['std'] < P['blind_std']:
        return 0  # blind

    # No pupil component found → check dark stats for blind vs center fallback
    if f['pupil_area'] < P['comp_min_area']:
        if f['dark_pct'] < 0.06:
            return 0  # blind (hardly any dark)
        if f['mean'] > 85:
            return 0  # blind
        return 1  # center fallback

    area = f['pupil_area']
    left_r = f['left_ratio']
    top_r = f['top_ratio']
    dx = f['dx']
    dy = f['dy']
    cx = f['pupil_cx']
    cy = f['pupil_cy']

    # Up: small pupil + top-heavy dark
    if area < P['up_area_max'] and top_r > P['up_top_ratio']:
        return 5

    # Down: large pupil (iris fully exposed)
    if area > P['down_area_min']:
        return 2

    # Left: dark biased to left side of mirrored image
    if left_r > P['left_ratio']:
        return 3

    # Right: dark biased to right side
    right_r = 1.0 - left_r
    if right_r > P['right_ratio']:
        return 4

    # Center: pupil near center
    if abs(dx) < P['center_dx_max'] and abs(dy) < P['center_dy_max']:
        return 1

    # Fallback by centroid position
    if cx > 0 and cy > 0:
        if cy < P['cy_up']:
            return 5
        elif cy > P['cy_down']:
            return 2
        elif cx < P['cx_left']:
            return 3
        elif cx > P['cx_right']:
            return 4

    return 1  # center fallback


def evaluate(params_override=None):
    """Run evaluation, return (confusion_matrix, per_class_correct, per_class_total, details)."""
    global P
    saved = dict(P)
    if params_override:
        P.update(params_override)

    confusion = np.zeros((6, 6), dtype=int)
    details = {c: {'correct': 0, 'total': 0, 'mis': []} for c in CLASSES}

    for ti, tcls in enumerate(CLASSES):
        d = os.path.join(BASE_DIR, tcls)
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.lower().endswith('.jpg'):
                continue
            fpath = os.path.join(d, fname)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            mirrored = cv2.flip(img, 1)
            f = extract_features(mirrored)
            pred = classify(f)

            confusion[ti][pred] += 1
            details[tcls]['total'] += 1
            if pred == ti:
                details[tcls]['correct'] += 1
            else:
                details[tcls]['mis'].append(fname)

    P.update(saved)  # restore
    return confusion, details


def print_report(confusion, details):
    total_correct = sum(d['correct'] for d in details.values())
    total_all = sum(d['total'] for d in details.values())

    print(f"\n{'True':>8} | {'Pred':>6} " + " | ".join(f"{c:>5}" for c in CLASSES) + f" | {'Acc':>6}")
    print("-" * 85)
    for ti, tcls in enumerate(CLASSES):
        n = details[tcls]['total']
        if n == 0:
            continue
        c = details[tcls]['correct']
        row = " ".join(f"{confusion[ti][pi]:>5d}" for pi in range(6))
        print(f"{tcls:>8} | {'':>6} " + row + f" | {c/n:>5.1%}")
    print("-" * 85)
    if total_all > 0:
        summary = " ".join(f"{np.sum(confusion[:, pi]):>5d}" for pi in range(6))
        print(f"{'TOTAL':>8} | {'':>6} " + summary + f" | {total_correct / total_all:>5.1%}")


def show_mis(details):
    print("\nMisclassified:")
    for cls in CLASSES:
        mis = details[cls]['mis']
        if mis:
            print(f"  {cls:>8}: {len(mis)}/{details[cls]['total']} — {', '.join(mis[:5])} ..." if len(mis) > 5 else f"  {cls:>8}: {len(mis)}/{details[cls]['total']} — {', '.join(mis)}")


# ── main ─────────────────────────────────────────────
if __name__ == '__main__':
    import sys
    if '--diag' in sys.argv:
        print("=" * 70)
        print("Feature diagnostic per class")
        print("=" * 70)
        for cls in CLASSES:
            d = os.path.join(BASE_DIR, cls)
            if not os.path.isdir(d):
                continue
            areas, left_r, top_r, dxs, dys, dark_ct = [], [], [], [], [], []
            found = 0
            for fname in sorted(os.listdir(d)):
                if not fname.lower().endswith('.jpg'):
                    continue
                img = cv2.imread(os.path.join(d, fname), cv2.IMREAD_GRAYSCALE)
                if img is None: continue
                mirrored = cv2.flip(img, 1)
                f = extract_features(mirrored)
                if f['pupil_area'] > 0:
                    areas.append(f['pupil_area'])
                    left_r.append(f['left_ratio'])
                    top_r.append(f['top_ratio'])
                    dxs.append(f['dx'])
                    dys.append(f['dy'])
                    found += 1
                dark_ct.append(f['dark_total'])
            print(f"\n{cls:>8}: {found}/{len(dark_ct)} pupil found")
            if areas:
                a = np.array(areas)
                print(f"  area   : mean={a.mean():.0f} min={a.min():.0f} max={a.max():.0f}  <50:{np.sum(a<50)}  >150:{np.sum(a>150)}")
            if left_r:
                lr = np.array(left_r)
                print(f"  left_r : mean={lr.mean():.3f} min={lr.min():.3f} max={lr.max():.3f}  >0.55:{np.sum(lr>0.55)}  <0.45:{np.sum(lr<0.45)}")
            if dxs:
                dx = np.array(dxs); dy = np.array(dys)
                print(f"  dx     : mean={dx.mean():+.1f} std={dx.std():.1f}  |x|<3:{np.sum(np.abs(dx)<3)}")
                print(f"  dy     : mean={dy.mean():+.1f} std={dy.std():.1f}  |y|<3:{np.sum(np.abs(dy)<3)}")
            if dark_ct:
                dc = np.array(dark_ct)
                print(f"  dark_tot: mean={dc.mean():.0f} min={dc.min():.0f} max={dc.max():.0f}  <100:{np.sum(dc<100)}")
            print(f"  blind trigger: mean={np.mean([f['mean'] for f in [extract_features(cv2.flip(cv2.imread(os.path.join(d, fn), 0), 1)) for fn in sorted(os.listdir(d)) if fn.endswith('.jpg')]]) if sorted(os.listdir(d)) else 0:.1f}")
    else:
        print("=" * 70)
        print("V5 Baseline: morphology + multi-feature decision tree")
        print("=" * 70)
        confusion, details = evaluate()
        print_report(confusion, details)
        show_mis(details)
