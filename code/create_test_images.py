"""
Create test images with clear patterns to diagnose horizontal/vertical alignment issues.
"""
import numpy as np
import cv2
from PIL import Image

# Create test image 1: Vertical lines for horizontal alignment check
def create_vertical_lines_test():
    img = np.zeros((600, 800), dtype=np.uint8)
    
    # Add vertical lines at specific positions
    for x in [50, 100, 200, 400, 600, 750]:
        img[:, x:x+2] = 255  # 2-pixel wide white line
    
    # Add a gradient background
    for x in range(800):
        img[:, x] = np.minimum(img[:, x], x // 4)
    
    # Save as JPEG
    Image.fromarray(img).save(r'E:\dvp-uart\Match\test_images\test_vertical_lines.jpg', quality=95)
    print(f"Created test_vertical_lines.jpg: {img.shape}, min={img.min()}, max={img.max()}")
    return img

# Create test image 2: Horizontal lines for vertical alignment check
def create_horizontal_lines_test():
    img = np.zeros((600, 800), dtype=np.uint8)
    
    # Add horizontal lines at specific positions
    for y in [50, 100, 200, 300, 400, 500, 550]:
        img[y:y+2, :] = 255  # 2-pixel tall white line
    
    # Add a gradient background
    for y in range(600):
        img[y, :] = np.minimum(img[y, :], y // 3)
    
    # Save as JPEG
    Image.fromarray(img).save(r'E:\dvp-uart\Match\test_images\test_horizontal_lines.jpg', quality=95)
    print(f"Created test_horizontal_lines.jpg: {img.shape}, min={img.min()}, max={img.max()}")
    return img

# Create test image 3: Checkerboard for overall alignment check
def create_checkerboard_test():
    img = np.zeros((600, 800), dtype=np.uint8)
    
    # Create 20x20 pixel checkerboard
    block_size = 20
    for y in range(0, 600, block_size):
        for x in range(0, 800, block_size):
            if ((x // block_size) + (y // block_size)) % 2 == 0:
                img[y:y+block_size, x:x+block_size] = 255
    
    # Save as JPEG
    Image.fromarray(img).save(r'E:\dvp-uart\Match\test_images\test_checkerboard.jpg', quality=95)
    print(f"Created test_checkerboard.jpg: {img.shape}, min={img.min()}, max={img.max()}")
    return img

# Create test image 4: Border pattern for edge detection
def create_border_test():
    img = np.zeros((600, 800), dtype=np.uint8)
    
    # Add white border (10 pixels)
    img[:10, :] = 255  # Top
    img[-10:, :] = 255  # Bottom
    img[:, :10] = 255  # Left
    img[:, -10:] = 255  # Right
    
    # Add gradient interior
    for y in range(10, 590):
        for x in range(10, 790):
            img[y, x] = min(255, (x + y) // 4)
    
    # Save as JPEG
    Image.fromarray(img).save(r'E:\dvp-uart\Match\test_images\test_border.jpg', quality=95)
    print(f"Created test_border.jpg: {img.shape}, min={img.min()}, max={img.max()}")
    return img

if __name__ == '__main__':
    create_vertical_lines_test()
    create_horizontal_lines_test()
    create_checkerboard_test()
    create_border_test()
    print("\nAll test images created in E:\\dvp-uart\\Match\\test_images\\")
