"""验证 MCU 推理引擎实现"""
import os; os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np
import cv2
import tensorflow as tf

MODEL_PATH = r'E:\dvp-uart\Match\ai\models\eye_tracking_simple.h5'
IMG_PATH = r'E:\dvp-uart\Match\ai\dataset\test\down\down_009.jpg'

# 加载模型
model = tf.keras.models.load_model(MODEL_PATH)

# 读取图像
img = cv2.imread(IMG_PATH, cv2.IMREAD_GRAYSCALE)
print(f'Original image: {img.shape}')
print(f'First 10: {img[0, :10]}')

# MCU 风格的最近邻 resize
src_h, src_w = img.shape
img_resized = np.zeros((32, 32), dtype=np.uint8)
for y in range(32):
    for x in range(32):
        src_x = x * src_w // 32
        src_y = y * src_h // 32
        if src_x >= src_w: src_x = src_w - 1
        if src_y >= src_h: src_y = src_h - 1
        img_resized[y, x] = img[src_y, src_x]

print(f'Resized (MCU style): {img_resized.shape}')
print(f'First 10: {img_resized[0, :10]}')

# 归一化
img_normalized = img_resized.astype(np.float32) / 255.0
print(f'Normalized first 10: {img_normalized[0, :10]}')

# 3通道 (HWC)
img_hwc = np.stack([img_normalized] * 3, axis=-1)
print(f'HWC shape: {img_hwc.shape}')

# Keras 推理
input_batch = np.expand_dims(img_hwc, 0)
keras_output = model.predict(input_batch, verbose=0)[0]
CLASSES = ['blind', 'center', 'down', 'left', 'right', 'up']
print(f'\nKeras output:')
for i, cls in enumerate(CLASSES):
    print(f'  {cls}: {keras_output[i]:.6f}')
print(f'  Predicted: {CLASSES[np.argmax(keras_output)]}')

# 手动推理（模拟 MCU）
print(f'\n=== 手动推理（模拟 MCU）===')

# 获取权重
w_conv, b_conv = model.get_layer('conv2d').get_weights()
print(f'Conv2D weights shape: {w_conv.shape}')  # (kh, kw, ic, oc)

gamma, beta, mean, var = model.get_layer('batch_normalization').get_weights()
print(f'BN params: gamma={gamma.shape}, beta={beta.shape}, mean={mean.shape}, var={var.shape}')

w_dense, b_dense = model.get_layer('dense').get_weights()
print(f'Dense weights shape: {w_dense.shape}')  # (in, out)

# BN 融合
eps = 1e-3
scale = gamma / np.sqrt(var + eps)
print(f'BN scale: {scale}')

# 融合后的 Conv 权重 (oc, ic, kh, kw)
w_fused = np.zeros((8, 3, 3, 3), dtype=np.float32)
b_fused = np.zeros(8, dtype=np.float32)

for oc in range(8):
    b_fused[oc] = (b_conv[oc] - mean[oc]) * scale[oc] + beta[oc]
    for ic in range(3):
        for ky in range(3):
            for kx in range(3):
                # Keras: (kh, kw, ic, oc)
                w_fused[oc, ic, ky, kx] = w_conv[ky, kx, ic, oc] * scale[oc]

print(f'Fused conv weights shape: {w_fused.shape}')
print(f'Fused bias: {b_fused}')

# Conv2D (same padding)
conv_out = np.zeros((32, 32, 8), dtype=np.float32)
for oc in range(8):
    for y in range(32):
        for x in range(32):
            sum_val = b_fused[oc]
            for ic in range(3):
                for ky in range(3):
                    for kx in range(3):
                        iy = y + ky - 1  # padding=1
                        ix = x + kx - 1
                        if 0 <= iy < 32 and 0 <= ix < 32:
                            sum_val += img_hwc[iy, ix, ic] * w_fused[oc, ic, ky, kx]
            # ReLU
            conv_out[y, x, oc] = max(0.0, sum_val)

print(f'Conv output shape: {conv_out.shape}')
print(f'Conv output sample: {conv_out[0, 0, :]}')

# MaxPool (4x4)
pool_out = np.zeros((8, 8, 8), dtype=np.float32)
for oc in range(8):
    for py in range(8):
        for px in range(8):
            max_val = -1e30
            for dy in range(4):
                for dx in range(4):
                    y = py * 4 + dy
                    x = px * 4 + dx
                    if conv_out[y, x, oc] > max_val:
                        max_val = conv_out[y, x, oc]
            pool_out[py, px, oc] = max_val

print(f'Pool output shape: {pool_out.shape}')
print(f'Pool output sample: {pool_out[0, 0, :]}')

# Flatten
flat = pool_out.flatten()
print(f'Flattened shape: {flat.shape}')

# Dense
dense_out = np.zeros(6, dtype=np.float32)
for c in range(6):
    sum_val = b_dense[c]
    for i in range(512):
        # Keras Dense: (in, out)
        sum_val += flat[i] * w_dense[i, c]
    dense_out[c] = sum_val

print(f'Dense output (before softmax): {dense_out}')

# Softmax
max_val = np.max(dense_out)
exp_out = np.exp(dense_out - max_val)
softmax_out = exp_out / np.sum(exp_out)

print(f'\nManual inference output:')
for i, cls in enumerate(CLASSES):
    print(f'  {cls}: {softmax_out[i]:.6f}')
print(f'  Predicted: {CLASSES[np.argmax(softmax_out)]}')

print(f'\n=== 对比 ===')
print(f'Keras vs Manual max diff: {np.max(np.abs(keras_output - softmax_out)):.6f}')
