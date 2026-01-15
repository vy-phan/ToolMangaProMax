import cv2
import numpy as np
import threading
import traceback
import os
from rapidocr_onnxruntime import RapidOCR
from deep_translator import GoogleTranslator
from PySide6.QtCore import QObject, Signal
from PIL import Image

class TranslatorEngine(QObject):
    # Signals giao tiếp với UI
    log_signal = Signal(str)
    progress_signal = Signal(int)
    ocr_finished = Signal(list)
    error_signal = Signal(str)
    crop_ocr_finished = Signal(int, str) 

    def __init__(self):
        super().__init__()
        self.ocr_model = None
        self.is_loading = False
        
    def initialize_ocr(self, lang='en'):
        """
        Khởi tạo RapidOCR.
        Lưu ý: RapidOCR bản ONNX mặc định dùng model đa ngữ (có thể đọc cả Anh, Trung, số...).
        Nó nhẹ và không cần load lại model phức tạp như Paddle.
        """
        if self.is_loading: return
        
        self.is_loading = True
        self.log_signal.emit(f"🚀 Đang khởi động AI Engine (Lightweight)...")
        
        def _load():
            try:
                # RapidOCR tự động tải model .onnx nhỏ (~15MB) về cache
                # det_use_gpu=False -> Ép chạy CPU cho máy yếu
                self.ocr_model = RapidOCR(det_use_gpu=False, cls_use_gpu=False, rec_use_gpu=False)
                
                self.is_loading = False
                self.log_signal.emit(f"✅ AI Sẵn sàng! (Chế độ siêu nhẹ ONNX)")
            except Exception as e:
                self.is_loading = False
                self.error_signal.emit(f"Lỗi khởi tạo OCR: {e}")

        threading.Thread(target=_load, daemon=True).start()

    def read_image_safe(self, path):
        """
        Đọc ảnh an toàn dùng PIL và Numpy (Bypass lỗi OpenCV)
        """
        try:
            # 1. Dùng PIL mở ảnh
            pil_img = Image.open(path)
            
            # 2. Convert sang RGB
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            # 3. Chuyển sang Numpy Array
            opencv_img = np.array(pil_img)
            
            # 4. [FIX LỖI] Đổi RGB -> BGR bằng kỹ thuật cắt lát Numpy (Slicing)
            # Thay vì dùng cv2.cvtColor, ta đảo ngược thứ tự kênh màu
            # [:, :, ::-1] nghĩa là: Lấy tất cả hàng, tất cả cột, đảo ngược kênh màu
            opencv_img = opencv_img[:, :, ::-1].copy()
            
            return opencv_img
            
        except Exception as e:
            print(f"Lỗi đọc ảnh ({path}): {e}")
            return None

    def run_ocr(self, image_path):
        """
        Quét chữ dùng RapidOCR + Cắt lát ảnh (Slicing)
        Đảm bảo không bao giờ tràn RAM với ảnh dài.
        """
        if not self.ocr_model:
            self.error_signal.emit("AI chưa sẵn sàng. Vui lòng đợi 5s...")
            return

        def _process():
            try:
                self.log_signal.emit("🔍 Đang xử lý ảnh...")
                
                # 1. Đọc ảnh
                img = self.read_image_safe(image_path)
                if img is None:
                    raise Exception("Không đọc được file ảnh.")
                
                h, w = img.shape[:2]
                
                # CẤU HÌNH CẮT LÁT
                # Với RapidOCR nhẹ hơn, ta có thể tăng kích thước lát cắt lên
                SLICE_HEIGHT = 2000 
                OVERLAP = 200 # Chồng lấn để không cắt đôi chữ
                
                all_detected_boxes = []
                
                # 2. Vòng lặp cắt
                for y in range(0, h, SLICE_HEIGHT - OVERLAP):
                    y_end = min(y + SLICE_HEIGHT, h)
                    
                    # Cắt ảnh
                    slice_img = img[y:y_end, 0:w]
                    
                    self.log_signal.emit(f"   ↳ Quét đoạn: {y}px - {y_end}px")
                    
                    # --- GỌI RAPID OCR ---
                    # Hàm trả về: result, elapse
                    # result format: [[box], text, score]
                    result, _ = self.ocr_model(slice_img)
                    
                    if result:
                        for line in result:
                            box = line[0]   # 4 điểm toạ độ [[x,y], [x,y]...]
                            text = line[1]  # Nội dung chữ
                            conf = line[2]  # Độ tin cậy
                            
                            # Lọc rác (độ tin cậy thấp)
                            if float(conf) < 0.5: continue

                            # Chuyển đổi toạ độ
                            xs = [p[0] for p in box]
                            ys = [p[1] for p in box]
                            
                            local_y_min = min(ys)
                            local_y_max = max(ys)
                            
                            # Logic chống trùng lặp (Overlap)
                            # Nếu hộp thoại nằm trọn trong vùng đã quét phía trên -> Bỏ qua
                            if y > 0 and local_y_max < OVERLAP:
                                continue
                                
                            x_min = min(xs)
                            x_max = max(xs)
                            y_min = local_y_min + y # Cộng thêm offset Y toàn cục
                            y_max = local_y_max + y
                            
                            width = x_max - x_min
                            height = y_max - y_min
                            
                            all_detected_boxes.append({
                                'rect': (x_min, y_min, width, height),
                                'text': text,
                                'conf': conf
                            })

                    if y_end >= h:
                        break

                self.log_signal.emit(f"✅ Hoàn tất! Tìm thấy {len(all_detected_boxes)} vùng văn bản.")
                self.ocr_finished.emit(all_detected_boxes)
                
            except Exception as e:
                traceback.print_exc()
                self.error_signal.emit(f"Lỗi OCR: {e}")
                self.ocr_finished.emit([]) 

        threading.Thread(target=_process, daemon=True).start()

    def translate_text(self, text, src='auto', dest='vi'):
        """Dịch văn bản (Google Translate)"""
        try:
            # Map mã ngôn ngữ cho Google
            # (RapidOCR không cần config lang đầu vào, nó tự nhận diện ký tự)
            lang_map = {
                'japan': 'ja', 'korean': 'ko', 'chinese_cht': 'zh-TW', 
                'en': 'en', 'es': 'es', 'auto': 'auto'
            }
            g_src = lang_map.get(src, 'auto')
            
            translated = GoogleTranslator(source=g_src, target=dest).translate(text)
            return translated
        except Exception as e:
            return f"[Lỗi dịch] {text}"
        
    translation_finished = Signal(int, str) 
    batch_translation_done = Signal()

    def run_batch_translation(self, text_list, src='auto', dest='vi'):
        """
        Dịch một danh sách các câu thoại (Chạy ngầm)
        text_list: List các string [(0, "Hello"), (1, "World")] - Kèm index để map ngược lại
        """
        def _process():
            try:
                self.log_signal.emit(f"🌏 Bắt đầu dịch {len(text_list)} câu thoại...")
                
                # Map ngôn ngữ
                lang_map = {'japan': 'ja', 'korean': 'ko', 'chinese_cht': 'zh-TW', 'en': 'en', 'es': 'es', 'auto': 'auto'}
                g_src = lang_map.get(src, 'auto')
                
                # Khởi tạo Translator (Dùng deep_translator)
                translator = GoogleTranslator(source=g_src, target=dest)
                
                total = len(text_list)
                for i, (index, text) in enumerate(text_list):
                    if not text.strip(): continue
                    
                    try:
                        # Dịch từng câu
                        translated = translator.translate(text)
                        
                        # Gửi kết quả về ngay lập tức
                        self.translation_finished.emit(index, translated)
                        self.log_signal.emit(f"   -> Dịch xong câu {index+1}/{total}")
                        
                    except Exception as e:
                        print(f"Lỗi dịch câu {index}: {e}")
                    
                    # Cập nhật tiến độ
                    self.progress_signal.emit(int(((i + 1) / total) * 100))
                
                self.batch_translation_done.emit()
                self.log_signal.emit("✅ Hoàn tất dịch thuật!")
                
            except Exception as e:
                self.error_signal.emit(f"Lỗi dịch thuật: {e}")

        threading.Thread(target=_process, daemon=True).start()   

    def inpaint_text_area(self, image_path, box_rect):
        """Xóa chữ (Inpainting)"""
        try:
            img = self.read_image_safe(image_path)
            x, y, w, h = map(int, box_rect)
            
            # Tạo mask
            mask = np.zeros(img.shape[:2], dtype=np.uint8)
            pad = 5 # Mở rộng vùng xóa
            
            # Giới hạn không cho pad tràn ra ngoài ảnh
            y1 = max(0, y - pad)
            y2 = min(img.shape[0], y + h + pad)
            x1 = max(0, x - pad)
            x2 = min(img.shape[1], x + w + pad)
            
            mask[y1:y2, x1:x2] = 255
            
            # Xóa
            inpainted_img = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
            return inpainted_img
        except Exception as e:
            print(f"Lỗi Inpaint: {e}")
            return None
        
    def run_crop_ocr(self, image_path, x, y, w, h, box_index):
        """Quét OCR cho một vùng cụ thể (dùng cho vẽ tay)"""
        def _process():
            try:
                if not self.ocr_model:
                    self.log_signal.emit("AI chưa sẵn sàng, vui lòng đợi...")
                    return

                # 1. Đọc ảnh gốc
                img = self.read_image_safe(image_path)
                if img is None: return

                # 2. Cắt vùng ảnh theo toạ độ (Lưu ý int)
                # Đảm bảo không cắt ra ngoài ảnh
                img_h, img_w = img.shape[:2]
                x1, y1 = max(0, int(x)), max(0, int(y))
                x2, y2 = min(img_w, int(x + w)), min(img_h, int(y + h))
                
                crop_img = img[y1:y2, x1:x2]

                if crop_img.size == 0: return

                # 3. Chạy OCR trên vùng cắt
                result, _ = self.ocr_model(crop_img)
                
                found_text = ""
                if result:
                    # Gộp tất cả các dòng tìm được trong khung vẽ tay thành 1 câu
                    found_text = " ".join([line[1] for line in result])
                
                # 4. Trả kết quả về UI
                self.crop_ocr_finished.emit(box_index, found_text)
                self.log_signal.emit(f"✏️ Đã quét vùng thủ công: {found_text}")

            except Exception as e:
                print(f"Lỗi Crop OCR: {e}")

        threading.Thread(target=_process, daemon=True).start()    