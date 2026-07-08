"""导出 INT8 量化权重到 C 代码"""
import os; os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import numpy as np, tensorflow as tf, cv2

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ai', 'models', 'eye_tracking_simple.h5')
OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'CH32H417', 'sdk_ch32h417', 'DVP', 'DVP_UART', 'Common')

# Load representative data for calibration
CLASSES = ['blind','center','down','left','right','up']
DATASET = os.path.join(os.path.dirname(__file__), '..', 'ai', 'dataset')
def load(split):
    imgs,labels=[],[]
    for ci,cls in enumerate(CLASSES):
        d=os.path.join(DATASET,split,cls)
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            if not f.endswith('.jpg'): continue
            data=np.fromfile(os.path.join(d,f),dtype=np.uint8)
            img=cv2.imdecode(data,cv2.IMREAD_GRAYSCALE)
            if img is not None:
                img=cv2.resize(img,(32,32))
                img=np.stack([img]*3,axis=-1).astype(np.float32)/255.0
                imgs.append(img);labels.append(ci)
    return np.array(imgs),np.array(labels)
X_train,_ = load('train')

# Convert to INT8 TFLite
model = tf.keras.models.load_model(MODEL_PATH)
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
def rep_data():
    for i in range(min(200, len(X_train))):
        yield [X_train[i:i+1].astype(np.float32)]
converter.representative_dataset = rep_data
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
tflite = converter.convert()

# Parse TFLite
interp = tf.lite.Interpreter(model_content=tflite)
interp.allocate_tensors()

# Extract weight tensors by index (from the tensor list output)
# [2] dense bias int32, [3] dense weights int8, [4] conv bias int32, [5] conv weights int8
conv_w = interp.get_tensor(5)   # [8,3,3,3] int8
conv_b = interp.get_tensor(4)   # [8] int32
dense_w = interp.get_tensor(3)  # [6,512] int8
dense_b = interp.get_tensor(2)  # [6] int32

# Quantization parameters
inp_det = interp.get_input_details()[0]
out_det = interp.get_output_details()[-1]
inp_scale, inp_zp = inp_det['quantization']
out_scale, out_zp = out_det['quantization']

# Get intermediate quantization from tensor details
conv_out_scale = interp.get_tensor_details()[6]['quantization_parameters']['scales'][0]
conv_out_zp = interp.get_tensor_details()[6]['quantization_parameters']['zero_points'][0]
conv_w_scales = interp.get_tensor_details()[5]['quantization_parameters']['scales']

print(f"Input: scale={inp_scale:.8f} zp={inp_zp}")
print(f"Conv out: scale={conv_out_scale:.8f} zp={conv_out_zp}")
print(f"Conv weights: {conv_w.shape} dtype={conv_w.dtype}")
print(f"Conv bias: {conv_b.shape} dtype={conv_b.dtype}")
print(f"Dense weights: {dense_w.shape} dtype={dense_w.dtype}")
print(f"Dense bias: {dense_b.shape} dtype={dense_b.dtype}")
print(f"Output: scale={out_scale:.8f} zp={out_zp}")

# Compute requantization multiplier for Conv
# After INT32 accumulation: output_int8 = clamp(acc * requant_scale + conv_out_zp)
# requant_scale = input_scale * weight_scale_per_channel / output_scale
conv_requant_scale = np.zeros(8, dtype=np.float32)
for c in range(8):
    conv_requant_scale[c] = inp_scale * conv_w_scales[c] / conv_out_scale

# Dense requantization
dense_w_scale = interp.get_tensor_details()[3]['quantization_parameters']['scales'][0]
dense_requant_scale = conv_out_scale * dense_w_scale / out_scale

print(f"\nConv requant scales: {conv_requant_scale}")
print(f"Dense requant scale: {dense_requant_scale:.8f}")

# Write C code
def arr_c(name, arr, dtype):
    flat = arr.flatten()
    if dtype == 'int8':
        vals = ',\n  '.join(', '.join(f'{int(x)}' for x in flat[i:i+16]) for i in range(0, len(flat), 16))
        return f'const signed char {name}[{len(flat)}] = {{\n  {vals}\n}};\n'
    elif dtype == 'int32':
        vals = ',\n  '.join(', '.join(f'{int(x)}' for x in flat[i:i+8]) for i in range(0, len(flat), 8))
        return f'const int {name}[{len(flat)}] = {{\n  {vals}\n}};\n'
    elif dtype == 'float':
        vals = ',\n  '.join(', '.join(f'{x:.8f}f' for x in flat[i:i+8]) for i in range(0, len(flat), 8))
        return f'const float {name}[{len(flat)}] = {{\n  {vals}\n}};\n'

out = []
out.append('// Auto-generated INT8 quantized weights')
out.append('// Conv(8,3x3)+BN+ReLU+MaxPool(4)+Dense(6)\n')
out.append(arr_c('conv_w', conv_w, 'int8'))
out.append(arr_c('conv_b', conv_b, 'int32'))
out.append(arr_c('dense_w', dense_w, 'int8'))
out.append(arr_c('dense_b', dense_b, 'int32'))
out.append(arr_c('conv_requant_scale', conv_requant_scale, 'float'))

out.append(f'#define INPUT_SCALE {inp_scale:.8f}f')
out.append(f'#define INPUT_ZP {inp_zp}')
out.append(f'#define CONV_OUT_SCALE {conv_out_scale:.8f}f')
out.append(f'#define CONV_OUT_ZP {conv_out_zp}')
out.append(f'#define DENSE_REQUANT_SCALE {dense_requant_scale:.8f}f')
out.append(f'#define OUTPUT_SCALE {out_scale:.8f}f')
out.append(f'#define OUTPUT_ZP {out_zp}')

result = '\n'.join(out)
out_path = os.path.join(OUT_DIR, 'weights_int8.c')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(result)
print(f'\nExported: {out_path} ({len(result)/1024:.1f} KB)')
