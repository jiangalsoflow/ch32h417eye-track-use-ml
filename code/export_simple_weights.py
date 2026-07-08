"""导出简化模型权重到 weights_simple.c"""
import os; os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np, tensorflow as tf, cv2

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')
OUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'CH32H417', 'sdk_ch32h417', 'DVP', 'DVP_UART_Test2.1', 'Common', 'weights_simple.c')

model = tf.keras.models.load_model(MODEL_PATH)

def arr_to_c(name, arr):
    flat = arr.flatten()
    vals = ',\n  '.join(', '.join(f'{x:.8f}f' for x in flat[i:i+8]) for i in range(0, len(flat), 8))
    return f'const float {name}[{len(flat)}] = {{\n  {vals}\n}};\n'

out = []
out.append('// Auto-generated weights for simplified eye tracking model')
out.append('// Architecture: Conv(8,3x3) + BN + ReLU + MaxPool(4) + Dense(6)\n')

k, b = model.get_layer('conv2d').get_weights()
out.append(arr_to_c('w_conv', np.transpose(k, (3,2,0,1))))
out.append(arr_to_c('b_conv', b))

gamma, beta, mean, var = model.get_layer('batch_normalization').get_weights()
out.append(arr_to_c('bn_gamma', gamma))
out.append(arr_to_c('bn_beta', beta))
out.append(arr_to_c('bn_mean', mean))
out.append(arr_to_c('bn_var', var))

k, b = model.get_layer('dense').get_weights()
out.append(arr_to_c('w_dense', k.T))
out.append(arr_to_c('b_dense', b))

result = '\n'.join(out)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(result)
print(f'Exported: {OUT_PATH} ({len(result)/1024:.1f} KB)')

# Verify
CLASSES = ['blind','center','down','left','right','up']
DATASET = os.path.join(os.path.dirname(__file__), '..', 'ai', 'dataset')
total = correct = 0
for ci, cls in enumerate(CLASSES):
    d = os.path.join(DATASET, 'test', cls)
    if not os.path.isdir(d): continue
    for f in os.listdir(d):
        if not f.endswith('.jpg'): continue
        data = np.fromfile(os.path.join(d,f), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        if img is None: continue
        img = cv2.resize(img, (32,32))
        img_rgb = np.stack([img]*3, axis=-1).astype(np.float32)/255.0
        out = model.predict(np.expand_dims(img_rgb, 0), verbose=0)[0]
        total += 1
        if np.argmax(out) == ci: correct += 1
print(f'Verification: {correct}/{total} = {correct/total*100:.1f}%')
