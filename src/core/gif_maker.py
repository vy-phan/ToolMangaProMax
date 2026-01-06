import os
import re
from pathlib import Path
from PIL import Image, ImageSequence
from PySide6.QtCore import QThread, Signal

class GifMakerWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str, str) # msg, level
    finished_signal = Signal(str)

    def __init__(self, source_dir, output_path, duration, resize_width=0):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.output_path = Path(output_path)
        self.duration = duration    # Thời gian mỗi khung hình (ms)
        self.resize_width = resize_width # 0 là giữ nguyên gốc
        self.is_running = True

    def natural_sort_key(self, s):
        """Hàm sắp xếp tự nhiên: 1, 2, 10 thay vì 1, 10, 2"""
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', str(s))]

    def run(self):
        self.log_signal.emit(f"Đang quét ảnh từ: {self.source_dir}", "process")
        
        # 1. Quét và sắp xếp file
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_files = [
            f for f in self.source_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in valid_exts
        ]
        
        # Sắp xếp theo tên file tự nhiên
        image_files.sort(key=lambda x: self.natural_sort_key(x.name))
        
        total = len(image_files)
        if total < 2:
            self.finished_signal.emit("Cần ít nhất 2 ảnh để tạo GIF!")
            return

        self.log_signal.emit(f"Tìm thấy {total} ảnh. Đang xử lý...", "info")
        
        frames = []
        
        # Lấy kích thước chuẩn từ ảnh đầu tiên (hoặc theo width người dùng nhập)
        first_img = Image.open(image_files[0])
        base_w, base_h = first_img.size
        
        if self.resize_width > 0:
            ratio = self.resize_width / float(base_w)
            target_size = (self.resize_width, int(float(base_h) * float(ratio)))
        else:
            target_size = (base_w, base_h)
            
        first_img.close()

        # 2. Xử lý từng khung hình
        for idx, file_path in enumerate(image_files):
            if not self.is_running: break
            
            try:
                img = Image.open(file_path)
                
                # Resize cho đồng bộ
                if img.size != target_size:
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                
                # Xử lý nền trong suốt (Transparency) -> Nền trắng
                # GIF không hỗ trợ alpha channel tốt như PNG, nên dán lên nền trắng là an toàn nhất
                background = Image.new("RGB", target_size, (255, 255, 255))
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    if img.mode != 'RGBA': img = img.convert('RGBA')
                    background.paste(img, (0, 0), mask=img)
                    frames.append(background)
                else:
                    frames.append(img.convert("RGB"))
                
                self.log_signal.emit(f"Đã thêm khung hình: {file_path.name}", "info")
                
            except Exception as e:
                self.log_signal.emit(f"Lỗi ảnh {file_path.name}: {e}", "error")

            # Cập nhật tiến độ (90% là load ảnh, 10% là save gif)
            percent = int(((idx + 1) / total) * 90)
            self.progress_signal.emit(percent)

        if not frames:
            self.finished_signal.emit("Không có khung hình nào hợp lệ.")
            return

        # 3. Lưu file GIF
        self.log_signal.emit(f"Đang render file GIF (Duration: {self.duration}ms)...", "process")
        try:
            frames[0].save(
                self.output_path,
                save_all=True,
                append_images=frames[1:],
                optimize=False,     # False để giữ chất lượng tốt hơn
                duration=self.duration,
                loop=0              # 0 = Lặp vô tận
            )
            self.progress_signal.emit(100)
            self.finished_signal.emit(f"Tạo GIF thành công!\nFile: {self.output_path}")
        except Exception as e:
            self.finished_signal.emit(f"Lỗi khi lưu GIF: {e}")

    def stop(self):
        self.is_running = False