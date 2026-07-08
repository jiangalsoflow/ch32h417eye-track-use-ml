import os
import sys
import numpy as np
import cv2
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf

IMAGES_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_new')
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']

print("=" * 70)
print("Model Score Distribution Analysis on images_new/")
print("=" * 70)

print("\nLoading model...")
model = tf.keras.models.load_model(MODEL_PATH)
model.predict(np.zeros((1, 32, 32, 3), dtype=np.float32), verbose=0)
print("Model loaded.\n")

all_scores = []
class_stats = {c: {'top1': [], 'top2': [], 'correct': 0, 'total': 0, 'all_scores': []} for c in CLASSES}

for ci, cls in enumerate(CLASSES):
    cls_dir = os.path.join(IMAGES_DIR, cls)
    if not os.path.isdir(cls_dir):
        continue
    files = [f for f in sorted(os.listdir(cls_dir)) if f.lower().endswith('.jpg')]

    X = []
    for f in files:
        fpath = os.path.join(cls_dir, f)
        img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        img = cv2.resize(img, (32, 32))
        img_rgb = np.stack([img] * 3, axis=-1).astype(np.float32) / 255.0
        X.append(img_rgb)

    if not X:
        continue

    X = np.array(X)
    preds = model.predict(X, verbose=0)

    for ri, scores in enumerate(preds):
        ranked = sorted(enumerate(scores), key=lambda x: -x[1])
        top1_idx, top1_val = ranked[0]
        top2_idx, top2_val = ranked[1]

        class_stats[cls]['top1'].append(top1_val)
        class_stats[cls]['top2'].append(top2_val)
        class_stats[cls]['total'] += 1
        if top1_idx == ci:
            class_stats[cls]['correct'] += 1

        for si, sv in enumerate(scores):
            class_stats[cls]['all_scores'].append((si, sv))

        all_scores.append(scores)

all_scores = np.array(all_scores)

print(f"Total images analyzed: {all_scores.shape[0]}")
true_labels_all = []
offset = 0
for ti in range(6):
    n = class_stats[CLASSES[ti]]['total']
    true_labels_all.extend([ti] * n)
true_labels_all = np.array(true_labels_all)
overall_acc = np.mean(np.argmax(all_scores, axis=1) == true_labels_all)
print(f"Overall accuracy: {overall_acc:.4f}")

print("\n" + "-" * 70)
print(f"{'Class':>8} | {'Count':>5} | {'Acc':>6} | {'Top1 mean':>10} | {'Top1 range':>20} | {'Top2 mean':>10} | {'Zeros(<1e-4)':>12}")
print("-" * 70)

overall_top1 = []
overall_top2 = []
overall_zeros = []

for ci, cls in enumerate(CLASSES):
    st = class_stats[cls]
    if st['total'] == 0:
        continue
    top1_arr = np.array(st['top1'])
    top2_arr = np.array(st['top2'])

    all_cls_scores = np.array([s for idx, s in st['all_scores'] if idx != ci])
    zero_rate = np.mean(all_cls_scores < 1e-4)

    acc = st['correct'] / st['total']

    print(f"{cls:>8} | {st['total']:>5} | {acc:>5.1%} | {top1_arr.mean():>10.6f} | {top1_arr.min():.6f}~{top1_arr.max():.6f} | {top2_arr.mean():>10.6f} | {zero_rate:>11.1%}")

    overall_top1.extend(st['top1'])
    overall_top2.extend(st['top2'])
    overall_zeros.extend([s for idx, s in st['all_scores'] if idx != ci])

print("-" * 70)
overall_top1_arr = np.array(overall_top1)
overall_top2_arr = np.array(overall_top2)
overall_zeros_arr = np.array(overall_zeros)
overall_zero_rate = np.mean(overall_zeros_arr < 1e-4)

print(f"{'ALL':>8} | {all_scores.shape[0]:>5} | {'--':>6} | {overall_top1_arr.mean():>10.6f} | {overall_top1_arr.min():.6f}~{overall_top1_arr.max():.6f} | {overall_top2_arr.mean():>10.6f} | {overall_zero_rate:>11.1%}")

print("\n" + "=" * 70)
print("Detailed score distribution (percentiles of non-dominant classes)")
print("=" * 70)
non_dom = overall_zeros_arr[overall_zeros_arr >= 1e-6]
if len(non_dom) > 0:
    for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        val = np.percentile(non_dom, pct)
        print(f"  P{pct:>2}: {val:.8f}")

print(f"\n  Count of non-zero scores (>1e-6): {len(non_dom)} / {len(overall_zeros_arr)}")
print(f"  Count of scores < 1e-4: {np.sum(overall_zeros_arr < 1e-4)}")
print(f"  Count of scores < 1e-5: {np.sum(overall_zeros_arr < 1e-5)}")
print(f"  Max non-dominant score: {overall_zeros_arr.max():.8f}")

print("\n" + "=" * 70)
print("Top1 score distribution (all classes combined)")
print("=" * 70)
for pct in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    val = np.percentile(overall_top1_arr, pct)
    print(f"  P{pct:>2}: {val:.6f}")

print(f"\n  Mean top1: {overall_top1_arr.mean():.6f}")
print(f"  Std  top1: {overall_top1_arr.std():.6f}")
print(f"  Min  top1: {overall_top1_arr.min():.6f}")
print(f"  Max  top1: {overall_top1_arr.max():.6f}")

print("\n" + "=" * 70)
print("Per-class confusion matrix (predicted column vs true row)")
print("=" * 70)
print(f"{'':>8} | " + " | ".join(f"{c:>7}" for c in CLASSES))
print("-" * 70)

confusion = np.zeros((6, 6), dtype=int)
offset = 0
for ti, tcls in enumerate(CLASSES):
    n = class_stats[tcls]['total']
    if n == 0:
        continue
    true_labels = np.full(n, ti)
    pred_labels = np.argmax(all_scores[offset:offset+n], axis=1)
    for pi in range(6):
        confusion[ti][pi] = np.sum(pred_labels == pi)
    offset += n

for ti, tcls in enumerate(CLASSES):
    row = confusion[ti]
    print(f"{tcls:>8} | " + " | ".join(f"{c:>7d}" for c in row))
