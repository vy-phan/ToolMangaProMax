import os
from pathlib import Path
from PIL import Image

def merge_images_vertical(folder_path, output_path):
    # Logic ghép ảnh dọc
    folder = Path(folder_path)
    images = sorted([f for f in folder.iterdir() if f.suffix.lower() in ['.jpg', '.png', '.webp']])
    if not images: return "Không tìm thấy ảnh"

    # Mở tất cả ảnh
    img_objs = [Image.open(f).convert('RGB') for f in images]
    
    # Tính kích thước
    max_width = max(img.width for img in img_objs)
    total_height = sum(img.height for img in img_objs)
    
    # Tạo canvas (Lưu ý: Nếu quá dài PIL sẽ lỗi, cần cắt nhỏ như tool cũ. 
    # Ở đây demo ghép 1 file cho gọn)
    canvas = Image.new('RGB', (max_width, total_height), (255, 255, 255))
    
    y_offset = 0
    for img in img_objs:
        canvas.paste(img, (0, y_offset))
        y_offset += img.height
        
    canvas.save(output_path, quality=90)
    return "Ghép thành công!"

def create_pdf(folder_path, output_path):
    folder = Path(folder_path)
    images = sorted([f for f in folder.iterdir() if f.suffix.lower() in ['.jpg', '.png', '.webp']])
    if not images: return "Không tìm thấy ảnh"
    
    img_list = []
    first_img = None
    
    for f in images:
        img = Image.open(f).convert('RGB')
        if first_img is None:
            first_img = img
        else:
            img_list.append(img)
            
    if first_img:
        first_img.save(output_path, "PDF", resolution=100.0, save_all=True, append_images=img_list)
        return "Tạo PDF thành công!"
    return "Lỗi tạo PDF"