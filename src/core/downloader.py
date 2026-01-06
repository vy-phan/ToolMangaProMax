import os
import shutil
import requests
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QThread, Signal

# Hằng số giới hạn
MAX_HEIGHT_WEBP = 16383 
MAX_HEIGHT_JPG = 60000

class DownloadAndProcessWorker(QThread):
    progress_signal = Signal(int)
    log_signal = Signal(str, str) # Msg, Level (info, success, error, url)
    finished_signal = Signal(str)

    def __init__(self, image_urls, save_dir, fmt='jpg', is_merge=False, is_pdf=False, quality=95):
        super().__init__()
        self.image_urls = image_urls
        self.save_dir = Path(save_dir)
        self.fmt = fmt.lower()
        self.is_merge = is_merge
        self.is_pdf = is_pdf
        self.quality = quality
        self.is_running = True

    def run(self):
        # 1. Tạo thư mục tạm
        temp_dir = self.save_dir / "temp_cache_v3"
        if temp_dir.exists(): shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_paths = []
        total = len(self.image_urls)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://google.com'
        }

        # --- GIAI ĐOẠN 1: TẢI ẢNH (RAW) ---
        self.log_signal.emit(f"Bắt đầu tải {total} ảnh về bộ nhớ tạm...", "process")
        
        with requests.Session() as session:
            session.headers.update(headers)
            for idx, url in enumerate(self.image_urls):
                if not self.is_running: break
                
                try:
                    fname = f"{idx:03d}.jpg" 
                    save_path = temp_dir / fname
                    
                    session.headers.update({'Referer': url})
                    
                    # LOG URL NHÌN CHO NGẦU
                    short_url = url if len(url) < 60 else url[:30] + "..." + url[-25:]
                    self.log_signal.emit(f"[GET] {short_url}", "url")
                    
                    resp = session.get(url, stream=True, timeout=20)
                    resp.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                            
                    downloaded_paths.append(str(save_path))
                    
                    # Cập nhật % (Dành 50% cho giai đoạn tải)
                    percent = int((idx / total) * 50)
                    self.progress_signal.emit(percent)
                    
                except Exception as e:
                    self.log_signal.emit(f"Lỗi tải ảnh {idx}: {e}", "error")

        if not downloaded_paths:
            self.finished_signal.emit("Thất bại: Không tải được ảnh nào.")
            return

        # --- GIAI ĐOẠN 2: XỬ LÝ (SINGLE / MERGE / PDF) ---
        self.log_signal.emit("Đang xử lý hình ảnh & Tối ưu hóa...", "process")
        
        try:
            if self.is_pdf:
                self.process_pdf(downloaded_paths, self.save_dir)
            elif self.is_merge:
                self.process_merge(downloaded_paths, self.save_dir, self.fmt)
            else:
                self.process_single(downloaded_paths, self.save_dir, self.fmt)
        except Exception as e:
             self.log_signal.emit(f"Lỗi nghiêm trọng khi xử lý: {e}", "error")
        finally:
            # Dọn dẹp
            try: shutil.rmtree(temp_dir)
            except: pass

        self.progress_signal.emit(100)
        self.finished_signal.emit("Tất cả tác vụ đã hoàn tất!")

    # --- LOGIC XỬ LÝ CHI TIẾT ---

    def process_single(self, paths, out_dir, fmt):
        """Xử lý từng ảnh"""
        total = len(paths)
        for i, p in enumerate(paths):
            try:
                img = Image.open(p)
                if img.mode != 'RGB': img = img.convert('RGB')
                
                out_name = f"{i:03d}.{fmt}"
                out_path = out_dir / out_name
                
                self.save_image(img, out_path, fmt)
                self.log_signal.emit(f"-> Đã lưu: {out_name}", "info")
                
                self.progress_signal.emit(50 + int((i/total)*50))
            except Exception as e:
                self.log_signal.emit(f"Lỗi convert ảnh {i}: {e}", "warning")

    def process_merge(self, paths, out_dir, fmt):
        """Ghép ảnh dọc"""
        images = []
        for p in paths:
            try:
                i = Image.open(p)
                if i.mode != 'RGB': i = i.convert('RGB')
                images.append(i)
            except: pass
        if not images: return

        limit_h = MAX_HEIGHT_WEBP if fmt == 'webp' else MAX_HEIGHT_JPG
        max_width = max(img.width for img in images)
        
        current_h = 0
        batch = []
        part = 1
        
        for img in images:
            # Resize về cùng chiều rộng để ghép cho đẹp (Optional)
            if img.width != max_width:
                 ratio = max_width / img.width
                 new_h = int(img.height * ratio)
                 img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

            if current_h + img.height > limit_h and batch:
                self.save_batch(batch, max_width, current_h, out_dir, part, fmt)
                part += 1
                batch = [img]
                current_h = img.height
            else:
                batch.append(img)
                current_h += img.height
                
        if batch:
            self.save_batch(batch, max_width, current_h, out_dir, part, fmt)

    def process_pdf(self, paths, out_dir):
        """Tạo file PDF duy nhất"""
        images_objs = []
        try:
            # Ảnh đầu tiên dùng để khởi tạo PDF
            first_img = Image.open(paths[0])
            if first_img.mode != 'RGB': first_img = first_img.convert('RGB')
            
            # Các ảnh còn lại
            for p in paths[1:]:
                try:
                    img = Image.open(p)
                    if img.mode != 'RGB': img = img.convert('RGB')
                    images_objs.append(img)
                except: pass
            
            out_name = "Chapter_Full.pdf"
            out_path = out_dir / out_name
            
            self.log_signal.emit(f"Đang đóng gói {len(images_objs)+1} trang vào PDF...", "process")
            
            # Lưu PDF
            first_img.save(
                out_path, 
                "PDF", 
                resolution=100.0, 
                save_all=True, 
                append_images=images_objs
            )
            
            self.log_signal.emit(f"-> Xuất PDF thành công: {out_name}", "success")
            
        except Exception as e:
            self.log_signal.emit(f"Lỗi tạo PDF: {e}", "error")

    def save_batch(self, batch_imgs, w, h, out_dir, part, fmt):
        """Lưu ảnh ghép"""
        canvas = Image.new('RGB', (w, h), (255, 255, 255))
        y = 0
        for img in batch_imgs:
            canvas.paste(img, (0, y))
            y += img.height
            
        out_name = f"Chapter_Merged_Part{part:02d}.{fmt}"
        out_path = out_dir / out_name
        self.save_image(canvas, out_path, fmt)
        self.log_signal.emit(f"-> Đã ghép: {out_name} (Cao: {h}px)", "success")

    def save_image(self, img, path, fmt):
        """Lưu ảnh với chất lượng (Quality) tùy chỉnh"""
        # Áp dụng Quality từ UI (self.quality)
        q = self.quality 
        
        if fmt == 'webp':
            img.save(path, 'WEBP', quality=q, method=6)
        elif fmt == 'png':
            # PNG là nén lossless, 'compress_level' khác 'quality'
            # Nhưng ta dùng optimize=True là đủ
            img.save(path, 'PNG', optimize=True)
        else:
            # JPG
            img.save(path, 'JPEG', quality=q, optimize=True)