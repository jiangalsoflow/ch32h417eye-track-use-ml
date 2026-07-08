"""
方案A训练脚本 — 1层卷积，改进训练方法
架构: Conv(8,3×3)+BN+ReLU+MaxPool(4)+Dense(6) — 和 MCU INT8 模型一致
改进:
  - 合并 images_new/ + images/ 旧数据（~80张/类）
  - 亮度增强（不破坏瞳孔位置）
  - /255 归一化（保持和 INT8 量化兼容）
  - 更多训练轮次 + 学习率调度
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import numpy as np
import cv2
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# ======== 配置 ========
IMG_SIZE = 32
BATCH = 16
EPOCHS = 300
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
SEED = 42

LABELED_DIR = os.path.join(os.path.dirname(__file__), '..', 'collected_data', 'labeled')
MODEL_DIR = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models')
MODEL_NAME = 'eye_tracking_simple.h5'

np.random.seed(SEED)
tf.random.set_seed(SEED)


def load_all_images():
    """加载 labeled 数据"""
    all_imgs = {cls: [] for cls in CLASSES}
    for cls in CLASSES:
        d = os.path.join(LABELED_DIR, cls)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith('.jpg'): continue
            img = cv2.imread(os.path.join(d, f), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                all_imgs[cls].append(img)
    return all_imgs


def preprocess(img):
    """预处理：resize → 3通道 → /255 归一化（和 INT8 量化兼容）"""
    img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
    img_rgb = np.stack([img] * 3, axis=-1).astype(np.float32) / 255.0
    return img_rgb


def augment_brightness(img_rgb, max_delta=0.08):
    """亮度增强 — 随机调整 ±max_delta"""
    delta = np.random.uniform(-max_delta, max_delta)
    return np.clip(img_rgb + delta, 0, 1)


def augment_contrast(img_rgb, factor_range=(0.85, 1.15)):
    """对比度增强 — 围绕均值缩放"""
    factor = np.random.uniform(*factor_range)
    mean = img_rgb.mean()
    return np.clip(mean + (img_rgb - mean) * factor, 0, 1)


def build_dataset(all_imgs, augment=True):
    """构建数据集，80/20 划分，平衡各类数据量"""
    X_train, y_train = [], []
    X_test, y_test = [], []

    # 先确定每类的最大数据量（用于平衡增强）
    max_count = max(len(v) for v in all_imgs.values())

    for ci, cls in enumerate(CLASSES):
        entries = all_imgs[cls]
        if len(entries) == 0:
            continue

        indices = np.random.permutation(len(entries))
        split = max(1, int(len(indices) * 0.8))

        # 计算该类需要的增强倍数（数据少的类多增强）
        n_train = split
        aug_per_img = max(1, max_count // max(1, n_train) - 1)
        aug_per_img = min(aug_per_img, 5)  # 上限5倍

        for i, idx in enumerate(indices):
            img = entries[idx]
            img_rgb = preprocess(img)

            if i < split:
                X_train.append(img_rgb)
                y_train.append(ci)
                if augment:
                    for _ in range(aug_per_img):
                        X_train.append(augment_brightness(img_rgb))
                        y_train.append(ci)
                    for _ in range(max(0, aug_per_img // 2)):
                        X_train.append(augment_contrast(img_rgb))
                        y_train.append(ci)
            else:
                X_test.append(img_rgb)
                y_test.append(ci)

    return (np.array(X_train), np.array(y_train),
            np.array(X_test), np.array(y_test))


def build_model():
    """1层卷积 — 和 MCU INT8 模型架构一致"""
    return keras.Sequential([
        layers.Input((IMG_SIZE, IMG_SIZE, 3)),
        layers.Conv2D(8, 3, padding='same'),
        layers.BatchNormalization(),
        layers.Activation('relu'),
        layers.MaxPooling2D(4),  # 32×32 → 8×8
        layers.Flatten(),
        layers.Dense(6, activation='softmax')
    ])


if __name__ == '__main__':
    print('=== 方案A: 1层卷积 + 改进训练 ===')

    # 加载
    all_imgs = load_all_images()
    total = 0
    for cls in CLASSES:
        n = len(all_imgs[cls])
        total += n
        print(f'  {cls}: {n}张')
    print(f'  总计: {total}张')

    # 构建数据集
    X_train, y_train, X_test, y_test = build_dataset(all_imgs, augment=True)

    # 打印各类训练样本数
    print(f'\n各类训练样本数（含增强）:')
    for ci, cls in enumerate(CLASSES):
        n = (y_train == ci).sum()
        print(f'  {cls}: {n}张')
    y_train_oh = keras.utils.to_categorical(y_train, len(CLASSES))
    y_test_oh = keras.utils.to_categorical(y_test, len(CLASSES))
    print(f'\n训练集: {len(X_train)}张 (含增强)')
    print(f'测试集: {len(X_test)}张')
    print(f'输入: mean={X_train.mean():.4f} std={X_train.std():.4f} range=[{X_train.min():.2f},{X_train.max():.2f}]')

    # 模型
    model = build_model()
    model.summary()

    model.compile(
        optimizer=keras.optimizers.Adam(0.002),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    callbacks = [
        keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', factor=0.5, patience=25, min_lr=1e-6, verbose=1),
        keras.callbacks.EarlyStopping(
            monitor='val_accuracy', patience=60, restore_best_weights=True, verbose=1),
    ]

    # 计算类别权重（平衡数据量差异）
    class_counts = np.bincount(y_train, minlength=len(CLASSES))
    class_weights = {i: len(y_train) / (len(CLASSES) * max(1, c)) for i, c in enumerate(class_counts)}
    print(f'\n类别权重: { {CLASSES[i]: f"{w:.2f}" for i, w in class_weights.items()} }')

    history = model.fit(
        X_train, y_train_oh,
        batch_size=BATCH,
        epochs=EPOCHS,
        validation_data=(X_test, y_test_oh),
        callbacks=callbacks,
        class_weight=class_weights,
        verbose=1
    )

    # 评估
    train_loss, train_acc = model.evaluate(X_train, y_train_oh, verbose=0)
    test_loss, test_acc = model.evaluate(X_test, y_test_oh, verbose=0)
    print(f'\n训练集: {train_acc:.1%}')
    print(f'测试集: {test_acc:.1%}')

    # 逐类
    y_pred = model.predict(X_test, verbose=0)
    print(f'\n逐类准确率:')
    for ci, cls in enumerate(CLASSES):
        mask = y_test == ci
        if mask.sum() > 0:
            acc = (y_pred[mask].argmax(axis=1) == ci).mean()
            print(f'  {cls}: {acc:.0%} ({mask.sum()}张)')

    # 保存
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, MODEL_NAME)
    model.save(model_path)
    print(f'\n已保存: {model_path}')
    print(f'下一步: python code/export_int8_weights.py')
