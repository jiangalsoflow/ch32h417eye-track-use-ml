import numpy as np, cv2, os
BASE = r'E:\dvp-uart\Match\images_latest'
for cls in ['blind','center','down','left','right','up']:
    d = os.path.join(BASE, cls)
    xs, ys, vs = [], [], []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('.jpg'): continue
        img = cv2.imread(os.path.join(d, fn), 0)
        if img is None: continue
        m = cv2.flip(img, 1)
        b = cv2.GaussianBlur(m, (3,3), 0)
        _, _, _, mm = cv2.minMaxLoc(b)  # (minVal, maxVal, minLoc, maxLoc)
        ml = cv2.minMaxLoc(b)[2]
        xs.append(ml[0]); ys.append(ml[1]); vs.append(b[ml[1], ml[0]])
    print(f'{cls:>8}: min_x={np.mean(xs):>6.1f}  min_y={np.mean(ys):>6.1f}  min_val={np.mean(vs):>6.1f}  (x<15:{sum(1 for x in xs if x<15)}/{len(xs)})')
