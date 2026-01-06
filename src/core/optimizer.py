import os
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QThread, Signal

class OptimizerWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str, str) # msg, level
    finished_signal = Signal(str)

    def __init__(self, source_dir, dest_dir, extensions, quality, is_same_folder, target_format):
        super().__init__()
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.extensions = extensions # List lọc đầu vào ['.jpg', '.png'...]
        self.quality = quality
        self.is_same_folder = is_same_folder
        self.target_format = target_format.lower() # 'original', 'jpg', 'png', 'webp'
        self.is_running = True

    def run(self):
        # 1. Quét file
        self.log_signal.emit(f"Đang quét ảnh trong: {self.source_dir}", "process")
        
        all_files = [
            f for f in self.source_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in self.extensions
        ]
        
        total = len(all_files)
        if total == 0:
            self.finished_signal.emit("Không tìm thấy file ảnh phù hợp!")
            return

        self.log_signal.emit(f"Tìm thấy {total} ảnh. Bắt đầu xử lý...", "info")
        success_count = 0
        
        # 2. Xử lý từng file
        for idx, file_path in enumerate(all_files):
            if not self.is_running: break
            
            try:
                img = Image.open(file_path)
                
                # --- A. XÁC ĐỊNH FORMAT ĐẦU RA ---
                if self.target_format == 'original':
                    out_ext = file_path.suffix.lower() # Giữ nguyên đuôi
                else:
                    out_ext = f".{self.target_format}" # Đổi đuôi (.jpg, .webp...)
                    # Fix lỗi đuôi .jpeg
                    if out_ext == '.jpg': out_ext = '.jpg' 

                # --- B. XỬ LÝ ẢNH (TRANSPARENCY) ---
                # Nếu đích là JPG nhưng ảnh gốc có Alpha (Transparency) -> Tô nền trắng
                if out_ext in ['.jpg', '.jpeg']:
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        # Tạo nền trắng
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode != 'RGBA': img = img.convert('RGBA')
                        # Dán ảnh lên nền trắng dùng kênh Alpha làm mask
                        bg.paste(img, mask=img.split()[3])
                        img = bg
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                
                # --- C. XÁC ĐỊNH TÊN FILE ---
                if self.is_same_folder:
                    # image.png -> image_optimized.webp
                    new_name = f"{file_path.stem}_optimized{out_ext}"
                else:
                    # image.png -> image.webp (ở folder khác)
                    new_name = f"{file_path.stem}{out_ext}"
                
                out_path = self.dest_dir / new_name
                self.dest_dir.mkdir(parents=True, exist_ok=True)

                # --- D. LƯU ẢNH ---
                # Map extension sang format của PIL
                save_fmt = {
                    '.jpg': 'JPEG', '.jpeg': 'JPEG', 
                    '.png': 'PNG', '.webp': 'WEBP'
                }.get(out_ext, 'JPEG')

                if save_fmt == 'PNG':
                    img.save(out_path, "PNG", optimize=True)
                elif save_fmt == 'WEBP':
                    img.save(out_path, "WEBP", quality=self.quality, method=6)
                else:
                    img.save(out_path, "JPEG", quality=self.quality, optimize=True)
                
                self.log_signal.emit(f"Đã lưu: {new_name}", "info")
                success_count += 1
                
            except Exception as e:
                self.log_signal.emit(f"Lỗi {file_path.name}: {e}", "error")

            percent = int(((idx + 1) / total) * 100)
            self.progress_signal.emit(percent)

        self.finished_signal.emit(f"Hoàn tất! Đã xử lý {success_count}/{total} ảnh.")

    def stop(self):
        self.is_running = False