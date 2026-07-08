"""测试不同模型方案的准确率和大小"""
import os, sys, cv2, numpy as np
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

CLASSES = ['blind','center','down','left','right','up']
DATASET = os.path.join(os.path.dirname(__file__), '..', 'ai', 'dataset')
IMG_SIZE = 32

def load_data(split):
    imgs, labels = [], []
    for ci, cls in enumerate(CLASSES):
        d = os.path.join(DATASET, split, cls)
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            if not f.endswith('.jpg'): continue
            data = np.fromfile(os.path.join(d,f), dtype=np.uint8)
            img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                img = np.stack([img]*3, axis=-1).astype(np.float32)/255.0
                imgs.append(img); labels.append(ci)
    return np.array(imgs), np.array(labels)

print("Loading data...")
X_train, y_train = load_data('train')
X_test, y_test = load_data('test')
y_train_oh = keras.utils.to_categorical(y_train, 6)
y_test_oh = keras.utils.to_categorical(y_test, 6)
print(f"Train: {len(X_train)}, Test: {len(X_test)}\n")

results = []

# === 1. 原始模型 ===
print("=== 1. 原始模型 ===")
m = keras.models.load_model(os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5'))
_, acc = m.evaluate(X_test, y_test_oh, verbose=0)
params = m.count_params()
print(f"  准确率: {acc*100:.1f}%, 参数: {params}")
results.append(("原始 (3Conv+2Dense)", acc, params, 0))

# === 2. INT8 量化 ===
print("\n=== 2. INT8 量化 ===")
converter = tf.lite.TFLiteConverter.from_keras_model(m)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
def rep_data():
    for i in range(min(100, len(X_test))):
        yield [X_test[i:i+1].astype(np.float32)]
converter.representative_dataset = rep_data
tflite = converter.convert()
with open('eye_int8.tflite','wb') as f: f.write(tflite)
interp = tf.lite.Interpreter(model_content=tflite)
interp.allocate_tensors()
inp_det = interp.get_input_details()
out_det = interp.get_output_details()
ok = 0
for i in range(len(X_test)):
    interp.set_tensor(inp_det[0]['index'], X_test[i:i+1].astype(np.float32))
    interp.invoke()
    if np.argmax(interp.get_tensor(out_det[0]['index'])) == y_test[i]: ok += 1
acc_int8 = ok / len(y_test)
print(f"  准确率: {acc_int8*100:.1f}%, 大小: {len(tflite)/1024:.1f}KB")
results.append(("INT8 量化", acc_int8, 0, len(tflite)/1024))

# === 3. 简化A: 2层卷积，无Dense隐藏层 ===
print("\n=== 3. 简化A (2Conv, no hidden Dense) ===")
ma = keras.Sequential([
    layers.Input((IMG_SIZE,IMG_SIZE,3)),
    layers.Conv2D(4,3,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(2), layers.Dropout(0.1),
    layers.Conv2D(8,3,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(2), layers.Dropout(0.1),
    layers.Flatten(), layers.Dense(6, activation='softmax')
])
ma.compile(optimizer=keras.optimizers.Adam(0.002), loss='categorical_crossentropy', metrics=['accuracy'])
ma.fit(X_train, y_train_oh, batch_size=16, epochs=100,
       validation_data=(X_test, y_test_oh),
       callbacks=[keras.callbacks.EarlyStopping(patience=20, restore_best_weights=True, verbose=0)], verbose=0)
_, acc_a = ma.evaluate(X_test, y_test_oh, verbose=0)
print(f"  准确率: {acc_a*100:.1f}%, 参数: {ma.count_params()}")
results.append(("简化A (2Conv)", acc_a, ma.count_params(), 0))

# === 4. 简化B: 3层卷积，少filter ===
print("\n=== 4. 简化B (3Conv small + 1Dense) ===")
mb = keras.Sequential([
    layers.Input((IMG_SIZE,IMG_SIZE,3)),
    layers.Conv2D(4,3,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(2),
    layers.Conv2D(8,3,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(2),
    layers.Conv2D(16,3,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(2),
    layers.Flatten(), layers.Dense(16), layers.BatchNormalization(), layers.Activation('relu'),
    layers.Dense(6, activation='softmax')
])
mb.compile(optimizer=keras.optimizers.Adam(0.002), loss='categorical_crossentropy', metrics=['accuracy'])
mb.fit(X_train, y_train_oh, batch_size=16, epochs=100,
       validation_data=(X_test, y_test_oh),
       callbacks=[keras.callbacks.EarlyStopping(patience=20, restore_best_weights=True, verbose=0)], verbose=0)
_, acc_b = mb.evaluate(X_test, y_test_oh, verbose=0)
print(f"  准确率: {acc_b*100:.1f}%, 参数: {mb.count_params()}")
results.append(("简化B (3Conv小)", acc_b, mb.count_params(), 0))

# === 5. 简化C: 极简 1层卷积 ===
print("\n=== 5. 简化C (1Conv, minimal) ===")
mc = keras.Sequential([
    layers.Input((IMG_SIZE,IMG_SIZE,3)),
    layers.Conv2D(8,5,padding='same'), layers.BatchNormalization(), layers.Activation('relu'),
    layers.MaxPooling2D(4),
    layers.Flatten(), layers.Dense(6, activation='softmax')
])
mc.compile(optimizer=keras.optimizers.Adam(0.002), loss='categorical_crossentropy', metrics=['accuracy'])
mc.fit(X_train, y_train_oh, batch_size=16, epochs=100,
       validation_data=(X_test, y_test_oh),
       callbacks=[keras.callbacks.EarlyStopping(patience=20, restore_best_weights=True, verbose=0)], verbose=0)
_, acc_c = mc.evaluate(X_test, y_test_oh, verbose=0)
print(f"  准确率: {acc_c*100:.1f}%, 参数: {mc.count_params()}")
results.append(("简化C (1Conv)", acc_c, mc.count_params(), 0))

# === 汇总 ===
print("\n" + "="*60)
print(f"{'模型':<25} {'准确率':>8} {'参数量':>10} {'大小KB':>8}")
print("-"*60)
for name, acc, params, size_kb in results:
    size_str = f"{size_kb:.0f}" if size_kb > 0 else "-"
    print(f"{name:<25} {acc*100:>7.1f}% {params:>10} {size_str:>8}")
