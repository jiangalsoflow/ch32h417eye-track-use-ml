"""Validate V4: nearest-neighbor against class mean templates."""
import os
import sys
import numpy as np
import cv2

BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'images_latest')
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']


def load_mean_templates(holdout_count=5):
    """
    Build mean template per class, leaving holdout_count images
    from each class for testing.
    Returns (templates: {class: (40,40) float}, test_set: [(img, true_class, fname), ...])
    """
    templates = {}
    test_set = []

    for cls in CLASSES:
        d = os.path.join(BASE_DIR, cls)
        if not os.path.isdir(d):
            continue
        files = sorted([f for f in os.listdir(d) if f.lower().endswith('.jpg')])

        if len(files) <= holdout_count:
            holdout = 1
        else:
            holdout = holdout_count

        train_files = files[holdout:]
        test_files = files[:holdout]

        train_imgs = []
        for f in train_files:
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            mirrored = cv2.flip(img, 1).astype(np.float32) / 255.0
            train_imgs.append(mirrored)

        if train_imgs:
            templates[cls] = np.mean(train_imgs, axis=0)

        for f in test_files:
            fpath = os.path.join(d, f)
            img = cv2.imread(fpath, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            mirrored = cv2.flip(img, 1).astype(np.float32) / 255.0
            test_set.append((mirrored, CLASSES.index(cls), f))

    return templates, test_set


def nearest_neighbor(img, templates):
    best_cls = 'center'
    best_dist = float('inf')
    for cls_name, tmpl in templates.items():
        dist = np.sum((img - tmpl) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_cls = cls_name
    return CLASSES.index(best_cls), best_dist


def main():
    print("=" * 70)
    print("V4: Nearest-Neighbor against Class Mean Templates")
    print("=" * 70)

    for hc in [5, 8, 10, 12, 14]:
        templates, test_set = load_mean_templates(holdout_count=hc)

        confusion = np.zeros((6, 6), dtype=int)
        correct = 0
        total = 0

        for img, true_idx, fname in test_set:
            pred_idx, dist = nearest_neighbor(img, templates)
            confusion[true_idx][pred_idx] += 1
            total += 1
            if pred_idx == true_idx:
                correct += 1

        if total == 0:
            continue

        acc = correct / total
        print(f"\nHoldout per class: {hc} (training on N-hc, testing on hc)")
        print(f"Test samples: {total}, accuracy: {acc:.1%}")

        # Per-class breakdown
        for ti, tcls in enumerate(CLASSES):
            n = np.sum(confusion[ti])
            if n == 0:
                continue
            c = confusion[ti][ti]
            row = " ".join(f"{confusion[ti][pi]:>5d}" for pi in range(6))
            print(f"  {tcls:>8}: {c:>3}/{n:<3} = {c/n:.1%}   [{row}]")


if __name__ == '__main__':
    main()
