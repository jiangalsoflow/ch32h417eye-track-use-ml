import traceback

try:
    print("[1] 启动", flush=True)
    import numpy as np
    from PIL import Image

    path = r'E:\dvp-uart\Match\code\uart_return.txt'
    with open(path, 'rb') as f:
        data = f.read()
    print(f"[2] 文件读取完成，共 {len(data)} 字节", flush=True)

    # --------------------------
    # 1. 提取标准JPEG数据（魔数匹配）
    # --------------------------
    print("\n[3] 提取JPEG数据", flush=True)
    jpeg_start = data.find(b'\xff\xd8')  # JPEG标准起始标记
    jpeg_end = data.find(b'\xff\xd9', jpeg_start)  # JPEG标准结束标记

    if jpeg_start >= 0 and jpeg_end >= 0:
        jpeg_data = data[jpeg_start : jpeg_end + 2]  # 包含FFD9结尾
        print(f"  找到标准JPEG，长度 {len(jpeg_data)} 字节", flush=True)

        # 保存原始JPEG文件
        with open(r'E:\dvp-uart\Match\code\received.jpg', 'wb') as f:
            f.write(jpeg_data)
        print("  已保存 received.jpg", flush=True)

        # 解码并分析
        recv_img = Image.open(r'E:\dvp-uart\Match\code\received.jpg').convert('L')
        recv_arr = np.array(recv_img)
        print(f"  解码尺寸: {recv_arr.shape[1]} x {recv_arr.shape[0]}", flush=True)
        print(f"  灰度范围: min={recv_arr.min()}, max={recv_arr.max()}, mean={recv_arr.mean():.1f}", flush=True)

        # 和参考图对比
        ref_path = r'E:\dvp-uart\Match\test_images\test4_gray_levels.jpg'
        try:
            ref_img = Image.open(ref_path).convert('L')
            ref_arr = np.array(ref_img)
            print(f"\n  参考图尺寸: {ref_arr.shape[1]} x {ref_arr.shape[0]}", flush=True)

            if ref_arr.shape == recv_arr.shape:
                diff = np.abs(recv_arr.astype(int) - ref_arr.astype(int))
                total = recv_arr.size
                print(f"  差值统计: mean={diff.mean():.2f}, max={diff.max()}", flush=True)
                for threshold in [5, 10, 20, 50]:
                    pct = np.sum(diff < threshold) * 100 / total
                    print(f"    差值 < {threshold}: {pct:.1f}%")
                
                diff_img = np.clip(diff * 5, 0, 255).astype(np.uint8)
                Image.fromarray(diff_img).save(r'E:\dvp-uart\Match\code\diff.png')
                print("  已保存 diff.png (x5 增强)", flush=True)
            else:
                print("  尺寸不一致，跳过差值对比", flush=True)
        except Exception as e:
            print(f"  参考图读取失败: {e}", flush=True)

        # 保存解码后的灰度图
        recv_img.save(r'E:\dvp-uart\Match\code\mcu_decoded.png')
        print("  已保存 mcu_decoded.png", flush=True)

    else:
        print("  未找到标准JPEG数据", flush=True)

    # --------------------------
    # 2. 兼容查找自定义分段（如果后续添加了标记）
    # --------------------------
    print("\n[4] 查找自定义分段", flush=True)
    
    def find_section(start_marker, end_marker):
        s = data.find(start_marker)
        if s < 0:
            return None
        s += len(start_marker)
        while s < len(data) and data[s] in (0x0d, 0x0a):
            s += 1
        e = data.find(end_marker, s)
        if e < 0:
            return None
        while e > s and data[e-1] in (0x0d, 0x0a):
            e -= 1
        return data[s:e]

    diag = find_section(b'DIAG_START', b'DIAG_END')
    if diag:
        print("  找到DIAG段", flush=True)
        for line in diag.split(b'\n'):
            line = line.strip(b'\r')
            if line:
                print(f"    {line.decode('utf-8', errors='replace')}")
    else:
        print("  未找到DIAG段", flush=True)

    pixel_data = find_section(b'PIXEL_START', b'PIXEL_END')
    if pixel_data:
        print(f"  找到像素段，长度 {len(pixel_data)} 字节", flush=True)
    else:
        print("  未找到PIXEL段", flush=True)

    # --------------------------
    # 3. 打印JPEG之后的剩余数据长度
    # --------------------------
    if jpeg_end >= 0:
        remaining = len(data) - (jpeg_end + 2)
        print(f"\n[5] JPEG之后剩余数据: {remaining} 字节", flush=True)
        if remaining > 0:
            # 打印剩余数据前100字节，方便排查后面是什么内容
            tail = data[jpeg_end+2 : jpeg_end+2+100]
            print(f"  剩余数据开头: {repr(tail)}", flush=True)

    print("\n=== 程序执行完成 ===", flush=True)

except Exception:
    traceback.print_exc()
    input("\n按回车退出")