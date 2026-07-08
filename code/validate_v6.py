"""Validate V6: Otsu dark pixel centroid + area. No morphology.
Pure statistics approach - the center of mass of ALL dark pixels
naturally indicates pupil direction, with eyelash noise averaged out.
"""
import os, sys, numpy as np, cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

# ── parameters ────────────────────────────────────────
P = {
    'blind_mean':       95,
    'blind_std':        28,
    'up_area_max':      80,    # Otsu dark pixel count < this → up
    'down_area_min':   200,    # Otsu dark pixel count > this → down (iris full exposure)
    'left_dx':          -6.0,  # dx < this → left (mirrored: centroid left of center)
    'right_dx':          4.0,  # dx > this → right
    'up_dy':           -5.0,  # dy < this → up (fallback)
    'down_dy':           4.0,  # dy > this → down (fallback)
    'center_max_dx':     3.5,  # |dx| < this → center candidate
    'center_max_dy':     4.0,  # |dy| < this → center candidate
}


def extract(mirrored_crop):
    """Extract features from mirrored 40x40. No morphological ops."""
    mean_val = float(np.mean(mirrored_crop))
    std_val  = float(np.std(mirrored_crop))

    blur = cv2.GaussianBlur(mirrored_crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    ys, xs = np.where(thresh > 0)
    n_dark = len(ys)

    if n_dark == 0:
        return {'mean': mean_val, 'std': std_val, 'dark_count': 0,
                'cx': -1, 'cy': -1, 'dx': 0, 'dy': 0}

    cx = float(np.mean(xs))
    cy = float(np.mean(ys))
    dx = cx - 19.5
    dy = cy - 19.5

    return {'mean': mean_val, 'std': std_val, 'dark_count': n_dark,
            'cx': cx, 'cy': cy, 'dx': dx, 'dy': dy}


def classify(f):
    if f['dark_count'] == 0:
        return 0  # blind

    n = f['dark_count']
    dx = f['dx']
    dy = f['dy']

    # Blind: bright + low texture
    if f['mean'] > P['blind_mean'] and f['std'] < P['blind_std']:
        return 0

    # Very few dark pixels → blank/blind
    if n < 20:
        if f['mean'] > 80:
            return 0
        return 1

    # Up: partial iris → few dark pixels
    if n < P['up_area_max']:
        return 5

    # Down: full iris exposed → many dark pixels
    if n > P['down_area_min']:
        return 2

    # Left: dark centroid shifted left in mirrored image
    if dx < P['left_dx']:
        return 3

    # Right: dark centroid shifted right
    if dx > P['right_dx']:
        return 4

    # Center: centroid near center
    if abs(dx) < P['center_max_dx'] and abs(dy) < P['center_max_dy']:
        return 1

    # Fallback: use dominant axis
    if abs(dy) > abs(dx):
        if dy < P['up_dy']:
            return 5
        elif dy > P['down_dy']:
            return 2
    else:
        if dx < 0:
            return 3
        else:
            return 4

    return 1


def evaluate(override=None):
    saved = dict(P)
    if override:
        P.update(override)

    confusion = np.zeros((6, 6), dtype=int)
    details = {c: {'correct': 0, 'total': 0, 'mis': []} for c in CLASSES}

    for ti, tcls in enumerate(CLASSES):
        d = os.path.join(BASE_DIR, tcls)
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.lower().endswith('.jpg'):
                continue
            img = cv2.imread(os.path.join(d, fname), cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            f = extract(cv2.flip(img, 1))
            pred = classify(f)
            confusion[ti][pred] += 1
            details[tcls]['total'] += 1
            if pred == ti:
                details[tcls]['correct'] += 1
            else:
                details[tcls]['mis'].append(fname)

    P.update(saved)
    return confusion, details


def report(confusion, details):
    tc = sum(d['correct'] for d in details.values())
    ta = sum(d['total'] for d in details.values())
    print(f"\n{'True':>8} | {'Pred':>6} " + " | ".join(f"{c:>5}" for c in CLASSES) + f" | {'Acc':>6}")
    print("-" * 85)
    for ti, tcls in enumerate(CLASSES):
        n = details[tcls]['total']
        if n == 0: continue
        c = details[tcls]['correct']
        row = " ".join(f"{confusion[ti][pi]:>5d}" for pi in range(6))
        print(f"{tcls:>8} | {'':>6} " + row + f" | {c/n:>5.1%}")
    print("-" * 85)
    if ta > 0:
        s = " ".join(f"{np.sum(confusion[:, pi]):>5d}" for pi in range(6))
        print(f"{'TOTAL':>8} | {'':>6} " + s + f" | {tc/ta:>5.1%}")
    print("\nMIS:")
    for cls in CLASSES:
        m = details[cls]['mis']
        if m:
            print(f"  {cls:>8}: {len(m)}/{details[cls]['total']} — {', '.join(m[:8])}{' ...' if len(m)>8 else ''}")


if __name__ == '__main__':
    import sys

    if '--diag' in sys.argv:
        print(f"{'Class':>8} | {'n':>4} | {'dark':>6} | {'dx':>7} | {'dy':>7} | {'mean':>6} | {'std':>5}")
        print("-" * 60)
        for cls in CLASSES:
            d = os.path.join(BASE_DIR, cls)
            if not os.path.isdir(d): continue
            dcs, dxs, dys, ms, ss = [], [], [], [], []
            for fn in sorted(os.listdir(d)):
                if not fn.endswith('.jpg'): continue
                img = cv2.imread(os.path.join(d, fn), 0)
                if img is None: continue
                f = extract(cv2.flip(img, 1))
                dcs.append(f['dark_count']); dxs.append(f['dx']); dys.append(f['dy'])
                ms.append(f['mean']); ss.append(f['std'])
            dc = np.array(dcs); dx = np.array(dxs); dy = np.array(dys)
            m = np.array(ms); s = np.array(ss)
            print(f"{cls:>8} | {len(dc):>4} | {dc.mean():>6.0f} | {dx.mean():>+7.1f} | {dy.mean():>+7.1f} | {m.mean():>6.1f} | {s.mean():>5.1f}")
    else:
        print("V6: Otsu dark pixel centroid + dark pixel count")
        confusion, details = evaluate()
        report(confusion, details)
