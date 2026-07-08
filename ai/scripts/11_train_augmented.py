"""小数据集训练 — 数据增强版"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np, os, cv2, random

DATASET_DIR = r'D:\AI Module\Eye_Tracking\dataset'
MODEL_DIR = r'D:\AI Module\Eye_Tracking\models'

IMG_SIZE, BATCH, EPOCHS = 32, 16, 80
CLASSES = ['blind','center','down','left','right','up']

def load_images(split):
    imgs, labels = [], []
    for ci, cls in enumerate(CLASSES):
        d = os.path.join(DATASET_DIR, split, cls)
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

# 数据增强
data_aug = keras.Sequential([
    layers.RandomFlip('horizontal'),
    layers.RandomRotation(0.05),
    layers.RandomZoom(0.1),
    layers.RandomBrightness(0.15),
])

def build_model():
    return keras.Sequential([
        layers.Input((IMG_SIZE,IMG_SIZE,3)),
        data_aug,

        layers.Conv2D(8, 3, padding='same', kernel_regularizer=keras.regularizers.l2(0.0005)),
        layers.BatchNormalization(), layers.Activation('relu'),
        layers.MaxPooling2D(2), layers.Dropout(0.15),

        layers.Conv2D(16, 3, padding='same', kernel_regularizer=keras.regularizers.l2(0.0005)),
        layers.BatchNormalization(), layers.Activation('relu'),
        layers.MaxPooling2D(2), layers.Dropout(0.15),

        layers.Conv2D(32, 3, padding='same', kernel_regularizer=keras.regularizers.l2(0.0005)),
        layers.BatchNormalization(), layers.Activation('relu'),
        layers.MaxPooling2D(2), layers.Dropout(0.15),

        layers.Flatten(),
        layers.Dense(32, kernel_regularizer=keras.regularizers.l2(0.0005)),
        layers.BatchNormalization(), layers.Activation('relu'),
        layers.Dropout(0.3),

        layers.Dense(len(CLASSES), activation='softmax')
    ])

print('=== Training with Data Augmentation ===')
X_train, y_train = load_images('train')
X_test, y_test = load_images('test')
print(f'Train: {len(X_train)}  Test: {len(X_test)}')

y_train_oh = keras.utils.to_categorical(y_train, len(CLASSES))
y_test_oh = keras.utils.to_categorical(y_test, len(CLASSES))

model = build_model()
model.summary()

model.compile(optimizer=keras.optimizers.Adam(0.001),
              loss='categorical_crossentropy', metrics=['accuracy'])

callbacks = [
    keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=10, min_lr=1e-6),
    keras.callbacks.EarlyStopping(monitor='val_accuracy', patience=25, restore_best_weights=True),
]

history = model.fit(X_train, y_train_oh, batch_size=BATCH, epochs=EPOCHS,
                    validation_data=(X_test, y_test_oh), callbacks=callbacks, verbose=1)

test_loss, test_acc = model.evaluate(X_test, y_test_oh)
print(f'\nTest Accuracy: {test_acc:.4f}')

model.save(os.path.join(MODEL_DIR, 'eye_tracking_regularized.h5'))
print('Model saved.')

# 也导出TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite = converter.convert()
with open(os.path.join(MODEL_DIR, 'eye_tracking_regularized.tflite'), 'wb') as f:
    f.write(tflite)
print(f'TFLite: {len(tflite)/1024:.1f} KB')
print('=== Done ===')
