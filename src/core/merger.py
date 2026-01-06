import os
import re
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QThread, Signal

MAX_HEIGHT_WEBP = 16383
MAX_HEIGHT_JPG = 60000

class MergerWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str, str) # msg, level
    finished_signal = Signal(str)

    # Đã xóa tham số target_width
    def __init__(self, source_dir, output_format, quality):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.output_format = output_format.lower()
        self.quality = quality
        self.is_running = True

    def natural_sort_key(self, s):
        return [int(text) if text.isdigit() else text.lower()
                for text in re.split(r'(\d+)', str(s))]

    def run(self):
        self.log_signal.emit(f"Đang quét ảnh từ: {self.source_dir}", "process")
        
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        image_files = [
            f for f in self.source_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in valid_exts
        ]
        
        image_files.sort(key=lambda x: self.natural_sort_key(x.name))
        
        total = len(image_files)
        if total < 2:
            self.finished_signal.emit("Cần ít nhất 2 ảnh để ghép!")
            return

        self.log_signal.emit(f"Tìm thấy {total} ảnh. Đang phân tích kích thước...", "info")

        images_objs = []
        max_w = 0
        
        # Load ảnh và tìm chiều rộng lớn nhất (max_w)
        for idx, f in enumerate(image_files):
            if not self.is_running: break
            try:
                img = Image.open(f)
                if img.mode != 'RGB': 
                    img = img.convert('RGB')
                
                images_objs.append(img)
                max_w = max(max_w, img.width)
                
                self.progress_signal.emit(int((idx / total) * 30))
            except Exception as e:
                self.log_signal.emit(f"Lỗi load {f.name}: {e}", "warning")

        if not images_objs:
            self.finished_signal.emit("Không có ảnh hợp lệ.")
            return

        # Mặc định luôn dùng chiều rộng lớn nhất làm chuẩn
        final_width = max_w
        self.log_signal.emit(f"Tự động căn chỉnh theo chiều rộng: {final_width}px", "info")

        limit_h = MAX_HEIGHT_WEBP if self.output_format == 'webp' else MAX_HEIGHT_JPG
        
        batch = []
        current_h = 0
        part = 1
        total_imgs = len(images_objs)
        
        for idx, img in enumerate(images_objs):
            if not self.is_running: break
            
            # Resize các ảnh nhỏ hơn về bằng final_width
            if img.width != final_width:
                ratio = final_width / img.width
                new_h = int(img.height * ratio)
                img = img.resize((final_width, new_h), Image.Resampling.LANCZOS)
            
            if current_h + img.height > limit_h and batch:
                self.save_batch(batch, final_width, current_h, part)
                part += 1
                batch = [img]
                current_h = img.height
            else:
                batch.append(img)
                current_h += img.height
            
            self.progress_signal.emit(30 + int((idx / total_imgs) * 60))

        if batch:
            self.save_batch(batch, final_width, current_h, part)
            
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"Hoàn tất! Đã ghép thành {part} file.")

    def save_batch(self, batch_imgs, w, h, part):
        try:
            canvas = Image.new('RGB', (w, h), (255, 255, 255))
            y = 0
            for img in batch_imgs:
                canvas.paste(img, (0, y))
                y += img.height
            
            out_name = f"Merged_Part{part:02d}.{self.output_format}"
            out_path = self.source_dir / out_name
            
            if self.output_format == 'webp':
                canvas.save(out_path, 'WEBP', quality=self.quality, method=6)
            elif self.output_format == 'png':
                canvas.save(out_path, 'PNG', optimize=True)
            else:
                canvas.save(out_path, 'JPEG', quality=self.quality, optimize=True)
                
            self.log_signal.emit(f"-> Đã lưu: {out_name} (Cao: {h}px)", "success")
        except Exception as e:
            self.log_signal.emit(f"Lỗi lưu file part {part}: {e}", "error")

    def stop(self):
        self.is_running = False