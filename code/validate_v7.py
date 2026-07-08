"""Validate V7: centroid + min_loc + dark_count. No morphology."""
import os, sys, numpy as np, cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

P = {
    'blind_mean':    95,
    'blind_std':     28,
    'blind_min_val': 35,   # darkest pixel > this → blind (bright)
    'down_my':       18,   # min_y > this → down
    'left_mx':       10,   # min_x < this → left
    'left_dx':      -5,    # centroid dx < this → left
    'up_n':         780,   # dark_count > this → up
    'right_dx':     -1,    # centroid dx > this → right candidate
    'right_mx':     12,    # min_x > this → confirm right (not left-ish)
}


def extract(mirrored_crop):
    mean_val = float(np.mean(mirrored_crop))
    std_val  = float(np.std(mirrored_crop))

    blur = cv2.GaussianBlur(mirrored_crop, (3, 3), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    ys, xs = np.where(thresh > 0)
    n_dark = len(ys)

    cx, cy, dx, dy = -1, -1, 0, 0
    if n_dark > 0:
        cx = float(np.mean(xs))
        cy = float(np.mean(ys))
        dx = cx - 19.5
        dy = cy - 19.5

    min_val, _, min_loc, _ = cv2.minMaxLoc(blur)
    mx, my = float(min_loc[0]), float(min_loc[1])
    min_v = float(min_val)

    return {
        'mean': mean_val, 'std': std_val,
        'dark_count': n_dark, 'cx': cx, 'cy': cy, 'dx': dx, 'dy': dy,
        'min_x': mx, 'min_y': my, 'min_val': min_v,
    }


def classify(f):
    if f['dark_count'] == 0:
        return 0

    n = f['dark_count']
    dx = f['dx']; dy = f['dy']
    mx = f['min_x']; my = f['min_y']; mv = f['min_val']

    # Blind checks
    if f['mean'] > P['blind_mean'] and f['std'] < P['blind_std']:
        return 0
    if mv > P['blind_min_val']:
        return 0
    if n < 20:
        return 0

    # Down: darkest pixel uniquely in lower part of image
    if my > P['down_my']:
        return 2

    # Left: darkest pixel far left OR centroid strongly left
    if mx < P['left_mx'] or dx < P['left_dx']:
        return 3

    # Up: high dark pixel count (looking up = more lashes+eyebrow visible)
    if n > P['up_n']:
        return 5

    # Right: centroid not-left AND min_x not extremely left
    if dx > P['right_dx'] and mx > P['right_mx']:
        return 4

    # Center
    return 1


def evaluate():
    confusion = np.zeros((6, 6), dtype=int)
    details = {c: {'c': 0, 't': 0, 'mis': []} for c in CLASSES}

    for ti, tcls in enumerate(CLASSES):
        d = os.path.join(BASE_DIR, tcls)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.jpg'): continue
            img = cv2.imread(os.path.join(d, fn), 0)
            if img is None: continue
            f = extract(cv2.flip(img, 1))
            pred = classify(f)
            confusion[ti][pred] += 1
            details[tcls]['t'] += 1
            if pred == ti:
                details[tcls]['c'] += 1
            else:
                details[tcls]['mis'].append(fn)

    return confusion, details


def report(confusion, details):
    for ti, tcls in enumerate(CLASSES):
        n = details[tcls]['t']
        c = details[tcls]['c']
        row = " ".join(f"{confusion[ti][pi]:>5d}" for pi in range(6))
        print(f"{tcls:>8}: {c:>3}/{n:<3}={c/n:.1%}  [{row}]")
    tc = sum(d['c'] for d in details.values())
    ta = sum(d['t'] for d in details.values())
    print(f"{'TOTAL':>8}: {tc:>3}/{ta:<3}={tc/ta:.1%}")
    print("\nMIS:")
    for cls in CLASSES:
        m = details[cls]['mis']
        if m:
            s = ', '.join(m[:5]) + (' ...' if len(m)>5 else '')
            print(f"  {cls:>8}: {len(m)}/{details[cls]['t']}  {s}")


if __name__ == '__main__':
    confusion, details = evaluate()
    report(confusion, details)
