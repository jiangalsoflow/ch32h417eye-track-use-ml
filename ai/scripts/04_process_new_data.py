"""
Step 4: Process New Data
- Read images from 6 folders
- Simulate infrared effect
- Augment and save to dataset
"""
import cv2
import numpy as np
import os
from pathlib import Path

# Paths
SOURCE_DIR = r'D:\AI Module\Eye_Tracking'
DATASET_DIR = r'D:\AI Module\Eye_Tracking\dataset'

# 6 categories
CATEGORIES = ['blind', 'center', 'down', 'left', 'right', 'up']

def read_img(path):
    with open(path, 'rb') as f:
        data = f.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img

def save_img(path, img):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _, buf = cv2.imencode('.jpg', img)
    with open(path, 'wb') as f:
        f.write(buf)

def simulate_infrared(img):
    """模拟红外效果：瞳孔变亮，背景变暗"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # 反转灰度值（模拟红外效果）
    ir = 255 - gray
    # 增强对比度
    ir = cv2.normalize(ir, None, 0, 255, cv2.NORM_MINMAX)
    # 转回3通道
    ir_3ch = cv2.cvtColor(ir, cv2.COLOR_GRAY2BGR)
    return ir_3ch

def augment_image(img, num_augments=15):
    """生成增强图像"""
    augmented = [img]
    h, w = img.shape[:2]

    for i in range(num_augments):
        aug = img.copy()

        # 随机旋转 (-10 ~ +10 度)
        angle = np.random.uniform(-10, 10)
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        aug = cv2.warpAffine(aug, M, (w, h))

        # 随机亮度调整
        brightness = np.random.uniform(0.8, 1.2)
        aug = cv2.convertScaleAbs(aug, alpha=brightness, beta=0)

        # 随机噪声
        noise = np.random.normal(0, 5, aug.shape).astype(np.uint8)
        aug = cv2.add(aug, noise)

        augmented.append(aug)

    return augmented

def process_all_categories():
    """处理所有类别"""
    print('=== Processing New Data ===')

    for category in CATEGORIES:
        print(f'\nProcessing: {category}')

        # 源文件夹
        src_dir = os.path.join(SOURCE_DIR, category)

        if not os.path.exists(src_dir):
            print(f'  Folder not found: {src_dir}')
            continue

        # 获取所有图片
        img_files = [f for f in os.listdir(src_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        print(f'  Found {len(img_files)} images')

        all_processed = []

        for img_file in img_files:
            img_path = os.path.join(src_dir, img_file)
            img = read_img(img_path)

            if img is None:
                print(f'  Failed to read: {img_file}')
                continue

            # 调整大小
            img = cv2.resize(img, (64, 64))

            # 模拟红外效果
            ir_img = simulate_infrared(img)

            # 数据增强
            augmented = augment_image(ir_img, num_augments=15)
            all_processed.extend(augmented)

        # 分割训练集和测试集 (80% / 20%)
        split_idx = int(len(all_processed) * 0.8)
        train_imgs = all_processed[:split_idx]
        test_imgs = all_processed[split_idx:]

        # 保存训练集
        for i, img in enumerate(train_imgs):
            save_path = os.path.join(DATASET_DIR, 'train', category, f'{category}_{i:03d}.jpg')
            save_img(save_path, img)

        # 保存测试集
        for i, img in enumerate(test_imgs):
            save_path = os.path.join(DATASET_DIR, 'test', category, f'{category}_{i:03d}.jpg')
            save_img(save_path, img)

        print(f'  Train: {len(train_imgs)} images')
        print(f'  Test: {len(test_imgs)} images')

    print('\n=== Processing Complete ===')

if __name__ == '__main__':
    process_all_categories()
