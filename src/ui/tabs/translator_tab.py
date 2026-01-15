import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTextEdit, QGroupBox, QFileDialog, 
                               QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, 
                               QGraphicsRectItem, QGraphicsTextItem, QSlider,
                               QColorDialog, QComboBox, QSpinBox, QSplitter, 
                               QGridLayout, QFrame, QMessageBox, QMenu, QProgressBar)
from PySide6.QtCore import Qt, QPointF, Signal, QSize
from PySide6.QtGui import QPixmap, QColor, QFont, QPen, QBrush, QAction, QIcon, QPainter, QCursor , QKeySequence, QShortcut
from core.translator_engine import TranslatorEngine
from PySide6.QtCore import Qt, QPointF, Signal, QSize, QRectF


def merge_ocr_boxes(boxes, y_threshold=30, x_threshold=50):
    """
    Gộp các box nằm gần nhau theo chiều dọc thành 1 box lớn.
    boxes: List các dict [{'rect': (x,y,w,h), 'text': '...', 'conf': ...}]
    """
    if not boxes:
        return []

    # 1. Sắp xếp box từ trên xuống dưới, trái sang phải
    # (Sắp xếp theo Y trước, nếu Y lệch ít thì coi như bằng nhau và xếp theo X)
    boxes.sort(key=lambda b: (b['rect'][1], b['rect'][0]))

    merged_boxes = []
    
    # Lấy box đầu tiên làm mốc
    current_box = boxes[0]

    for i in range(1, len(boxes)):
        next_box = boxes[i]
        
        # Lấy thông số box hiện tại (A)
        x1, y1, w1, h1 = current_box['rect']
        r1 = x1 + w1
        b1 = y1 + h1 # Đáy của box A

        # Lấy thông số box tiếp theo (B)
        x2, y2, w2, h2 = next_box['rect']
        r2 = x2 + w2
        
        # --- ĐIỀU KIỆN GỘP ---
        # 1. Khoảng cách dọc: Đỉnh box B - Đáy box A < ngưỡng (nghĩa là chúng rất gần nhau)
        vertical_gap = y2 - b1
        is_vertically_close = vertical_gap < y_threshold

        # 2. Thẳng hàng ngang: Chúng phải chồng lấn nhau theo chiều ngang 
        # (Để tránh gộp 1 chữ bên trái trang với 1 chữ bên phải trang dù chúng cùng dòng)
        # Tính vùng chồng lấn (overlap)
        overlap_start = max(x1, x2)
        overlap_end = min(r1, r2)
        overlap_width = overlap_end - overlap_start
        
        # Nếu overlap > 0 tức là có thẳng hàng (hoặc dùng ngưỡng âm nhỏ nếu muốn lỏng hơn)
        is_horizontally_aligned = overlap_width > -x_threshold 

        if is_vertically_close and is_horizontally_aligned:
            # === THỰC HIỆN GỘP ===
            # 1. Toạ độ bao trùm cả 2 box
            new_x = min(x1, x2)
            new_y = min(y1, y2)
            new_w = max(x1+w1, x2+w2) - new_x
            new_h = max(y1+h1, y2+h2) - new_y
            
            # 2. Nối text (thêm dấu cách)
            new_text = current_box['text'] + " " + next_box['text']
            
            # Cập nhật current_box
            current_box['rect'] = (new_x, new_y, new_w, new_h)
            current_box['text'] = new_text
            # (Có thể tính lại conf trung bình nếu cần, ở đây giữ nguyên)
            
        else:
            # Nếu không gộp được, chốt box cũ và chuyển sang box mới
            merged_boxes.append(current_box)
            current_box = next_box

    # Đừng quên thêm box cuối cùng
    merged_boxes.append(current_box)
    
    return merged_boxes

# ==============================================================================
# 1. OCR BOX ITEM 
# ==============================================================================
class OCRBoxItem(QGraphicsRectItem):
    # Các vùng tương tác
    handleTopLeft = 1
    handleTopMiddle = 2
    handleTopRight = 3
    handleMiddleLeft = 4
    handleMiddleRight = 5
    handleBottomLeft = 6
    handleBottomMiddle = 7
    handleBottomRight = 8

    handleCursors = {
        handleTopLeft: Qt.SizeFDiagCursor,
        handleTopMiddle: Qt.SizeVerCursor,
        handleTopRight: Qt.SizeBDiagCursor,
        handleMiddleLeft: Qt.SizeHorCursor,
        handleMiddleRight: Qt.SizeHorCursor,
        handleBottomLeft: Qt.SizeBDiagCursor,
        handleBottomMiddle: Qt.SizeVerCursor,
        handleBottomRight: Qt.SizeFDiagCursor,
    }

    def __init__(self, x, y, w, h, text, parent_tab, index=0):
        super().__init__(x, y, w, h)
        self.index = index
        self.text_raw = text
        self.text_trans = ""
        self.parent_tab = parent_tab

        self.current_text_color = QColor("black")
        self.current_bg_color = QColor("white")
        self.current_font = "Comic Sans MS"  # Font mặc định
        self.current_size = 14               # Size mặc định
        
        # Màu mặc định
        self.current_text_color = QColor("black")
        self.current_bg_color = QColor("white")

        self.setPen(QPen(QColor("#ff0000"), 2, Qt.DashLine))
        self.setBrush(QBrush(QColor(255, 255, 255, 10)))
        
        self.setFlags(
            QGraphicsRectItem.ItemIsMovable | 
            QGraphicsRectItem.ItemIsSelectable | 
            QGraphicsRectItem.ItemIsFocusable |
            QGraphicsRectItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None

        # --- TEXT ITEM ---
        self.text_item = QGraphicsTextItem(self)
        self.text_item.setDefaultTextColor(self.current_text_color)
        self.text_item.setVisible(False) 
        self.text_item.setZValue(10) # [FIX] Đảm bảo chữ luôn nằm trên cùng
        
        # --- BACKGROUND ITEM ---
        self.bg_item = QGraphicsRectItem(self.rect(), self)
        self.bg_item.setBrush(QBrush(self.current_bg_color))
        self.bg_item.setPen(QPen(Qt.NoPen))
        self.bg_item.setZValue(5) # [FIX] Nền nằm giữa (trên ảnh gốc, dưới chữ)
        self.bg_item.setVisible(False)

    def set_translated_text(self, text, font_family=None, font_size=None):
        self.text_trans = text
        
        # Nếu có truyền tham số mới thì cập nhật, không thì dùng cái cũ của box
        if font_family: self.current_font = font_family
        if font_size: self.current_size = font_size
        
        # Cấu hình Font từ thuộc tính đã lưu
        font = QFont(self.current_font, self.current_size)
        font.setBold(True)
        self.text_item.setFont(font)
        
        # ... (Giữ nguyên phần HTML và hiển thị bên dưới) ...
        html_content = f"<div style='text-align: center; line-height: 1.2;'>{text}</div>"
        self.text_item.setHtml(html_content)
        self.text_item.setDefaultTextColor(self.current_text_color)
        self.bg_item.setBrush(QBrush(self.current_bg_color))
        
        self.text_item.setVisible(True)
        self.bg_item.setVisible(True)
        self.setPen(QPen(QColor("#0078d4"), 2))
        self.update_visuals()

    def update_style(self, text_color=None, bg_color=None, font_family=None, font_size=None):
        if text_color: 
            self.current_text_color = text_color
            self.text_item.setDefaultTextColor(text_color)
        if bg_color: 
            self.current_bg_color = bg_color
            self.bg_item.setBrush(QBrush(bg_color))
        if font_family and font_size:
            self.text_item.setFont(QFont(font_family, font_size))
            
        self.update_visuals()

    def update_visuals(self):
        """[FIX LỖI HIỂN THỊ] Cập nhật lại vị trí text theo box cha"""
        rect = self.rect()
        
        # 1. Cập nhật kích thước nền trắng
        self.bg_item.setRect(rect)
        
        # 2. Cập nhật độ rộng chữ để tự xuống dòng
        self.text_item.setTextWidth(rect.width())
        
        # 3. [QUAN TRỌNG] Di chuyển chữ về đúng toạ độ (x, y) của khung
        self.text_item.setPos(rect.x(), rect.y())

    # --- Mouse Events ---
    def handleAt(self, point):
        rect = self.rect()
        margin = 10.0
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        left, right, top, bottom = x, x+w, y, y+h
        
        if (point.x() - left) < margin and (point.y() - top) < margin: return self.handleTopLeft
        if (right - point.x()) < margin and (point.y() - top) < margin: return self.handleTopRight
        if (point.x() - left) < margin and (bottom - point.y()) < margin: return self.handleBottomLeft
        if (right - point.x()) < margin and (bottom - point.y()) < margin: return self.handleBottomRight
        if (point.x() - left) < margin: return self.handleMiddleLeft
        if (right - point.x()) < margin: return self.handleMiddleRight
        if (point.y() - top) < margin: return self.handleTopMiddle
        if (bottom - point.y()) < margin: return self.handleBottomMiddle
        return None

    def hoverMoveEvent(self, moveEvent):
        if self.isSelected():
            handle = self.handleAt(moveEvent.pos())
            cursor = Qt.ArrowCursor if handle is None else self.handleCursors[handle]
            self.setCursor(cursor)
        super().hoverMoveEvent(moveEvent)

    def hoverLeaveEvent(self, moveEvent):
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(moveEvent)

    def mousePressEvent(self, mouseEvent):
        self.handleSelected = self.handleAt(mouseEvent.pos())
        if self.handleSelected:
            self.mousePressPos = mouseEvent.pos()
            self.mousePressRect = self.rect()
        else:
            super().mousePressEvent(mouseEvent)
        self.parent_tab.update_inspector_from_box(self)

    def mouseMoveEvent(self, mouseEvent):
        if self.handleSelected is not None:
            self.interactiveResize(mouseEvent.pos())
        else:
            super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        super().mouseReleaseEvent(mouseEvent)
        self.handleSelected = None
        self.mousePressPos = None
        self.mousePressRect = None
        self.update()

    def interactiveResize(self, mousePos):
        rect = self.rect()
        diff = mousePos - self.mousePressPos
        self.prepareGeometryChange()
        
        if self.handleSelected == self.handleTopLeft: rect.setTopLeft(rect.topLeft() + diff)
        elif self.handleSelected == self.handleTopMiddle: rect.setTop(rect.top() + diff.y())
        elif self.handleSelected == self.handleTopRight: rect.setTopRight(rect.topRight() + diff)
        elif self.handleSelected == self.handleMiddleLeft: rect.setLeft(rect.left() + diff.x())
        elif self.handleSelected == self.handleMiddleRight: rect.setRight(rect.right() + diff.x())
        elif self.handleSelected == self.handleBottomLeft: rect.setBottomLeft(rect.bottomLeft() + diff)
        elif self.handleSelected == self.handleBottomMiddle: rect.setBottom(rect.bottom() + diff.y())
        elif self.handleSelected == self.handleBottomRight: rect.setBottomRight(rect.bottomRight() + diff)
        
        self.setRect(rect)
        self.update_visuals() # Cập nhật hiển thị khi kéo
        self.mousePressPos = mousePos

    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("❌ Xóa khung này")
        action = menu.exec(event.screenPos())
        if action == delete_action:
            self.delete_self()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.delete_self()
        else:
            super().keyPressEvent(event)

    def delete_self(self):
        self.scene().removeItem(self)
        if self.parent_tab.current_box == self:
            self.parent_tab.current_box = None
            self.parent_tab.txt_raw.clear()
            self.parent_tab.txt_trans.clear()
# ==============================================================================
# 2. ZOOM CONTROL
# ==============================================================================
class ZoomControl(QFrame):
    zoom_changed = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(32, 160)
        self.setStyleSheet("""
            QFrame { background-color: rgba(30, 30, 30, 180); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 30); }
            QPushButton { background-color: transparent; color: white; border: none; font-size: 16px; font-weight: bold; border-radius: 14px; }
            QPushButton:hover { background-color: rgba(255, 255, 255, 50); }
            QSlider::groove:vertical { background: #555; width: 4px; border-radius: 2px; margin: 0 14px; }
            QSlider::handle:vertical { background: #0078d4; height: 10px; margin: 0 -3px; border-radius: 5px; }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(5)
        self.btn_plus = QPushButton("+")
        self.btn_minus = QPushButton("-")
        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(10, 300)
        self.slider.setValue(100)
        self.slider.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.btn_plus, 0, Qt.AlignCenter)
        layout.addWidget(self.slider, 1, Qt.AlignCenter)
        layout.addWidget(self.btn_minus, 0, Qt.AlignCenter)
        self.setLayout(layout)
        self.slider.valueChanged.connect(lambda v: self.zoom_changed.emit(v / 100.0))
        self.btn_plus.clicked.connect(lambda: self.slider.setValue(self.slider.value() + 10))
        self.btn_minus.clicked.connect(lambda: self.slider.setValue(self.slider.value() - 10))

# ==============================================================================
# 3. EDITOR CANVAS
# ==============================================================================
class EditorCanvas(QGraphicsView):
    # Tín hiệu phát ra khi vẽ xong: x, y, w, h
    box_drawn = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag) # Mặc định là chế độ kéo ảnh
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#e5e5e5")))
        
        # Widget Zoom
        self.zoom_widget = ZoomControl(self)
        self.zoom_widget.zoom_changed.connect(lambda s: (self.resetTransform(), self.scale(s, s)))
        self.zoom_widget.hide()

        # --- BIẾN CHO CHẾ ĐỘ VẼ ---
        self.is_drawing = False
        self.start_point = None
        self.temp_rect_item = None # Hình chữ nhật nét đứt khi đang kéo chuột

    def set_drawing_mode(self, enabled: bool):
        """Bật/Tắt chế độ vẽ"""
        self.is_drawing = enabled
        if enabled:
            self.setDragMode(QGraphicsView.NoDrag) # Tắt kéo ảnh
            self.setCursor(Qt.CrossCursor)         # Đổi con trỏ thành dấu cộng
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.ArrowCursor)

    # --- SỰ KIỆN CHUỘT ĐỂ VẼ ---
    def mousePressEvent(self, event):
        if self.is_drawing and event.button() == Qt.LeftButton:
            # Lấy toạ độ trong Scene (tính cả zoom/scroll)
            self.start_point = self.mapToScene(event.pos())
            
            # Tạo hình chữ nhật tạm thời để người dùng thấy mình đang vẽ
            self.temp_rect_item = QGraphicsRectItem()
            self.temp_rect_item.setPen(QPen(Qt.red, 2, Qt.DashLine))
            self.temp_rect_item.setBrush(QBrush(QColor(255, 0, 0, 30)))
            self.scene.addItem(self.temp_rect_item)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_drawing and self.start_point and self.temp_rect_item:
            current_point = self.mapToScene(event.pos())
            # Tạo hình chữ nhật từ điểm đầu đến điểm hiện tại (normalized để tránh lỗi âm)
            rect = QRectF(self.start_point, current_point).normalized()
            self.temp_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_drawing and self.start_point and self.temp_rect_item:
            # Kết thúc vẽ
            rect = self.temp_rect_item.rect()
            
            # Xóa hình tạm
            self.scene.removeItem(self.temp_rect_item)
            self.temp_rect_item = None
            self.start_point = None
            
            # Chỉ tạo box nếu kích thước đủ lớn (> 5px)
            if rect.width() > 5 and rect.height() > 5:
                self.box_drawn.emit(rect.x(), rect.y(), rect.width(), rect.height())
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.zoom_widget.move(self.width() - 40, self.height() - 170)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            val = self.zoom_widget.slider.value()
            delta = 10 if event.angleDelta().y() > 0 else -10
            self.zoom_widget.slider.setValue(val + delta)
        else:
            super().wheelEvent(event)

# ==============================================================================
# 4. TRANSLATOR TAB (MAIN)
# ==============================================================================
class TranslatorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_image_item = None
        self.current_image_path = None
        self.current_box = None
        
        self.engine = TranslatorEngine()
        self.setup_engine_connections()
        self.init_ui()

    def setup_engine_connections(self):
        self.engine.log_signal.connect(lambda msg: print(f"[AI] {msg}"))
        self.engine.error_signal.connect(lambda err: QMessageBox.warning(self, "Lỗi AI", err))
        self.engine.ocr_finished.connect(self.on_ocr_finished)
        self.engine.translation_finished.connect(self.on_single_translation_done)
        self.engine.batch_translation_done.connect(self.on_all_done)
        self.engine.progress_signal.connect(self.update_progress)
        self.engine.crop_ocr_finished.connect(self.on_crop_ocr_done)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Style (Giữ nguyên)
        self.setStyleSheet("""
            QWidget { background-color: #ffffff; color: #333; font-family: 'Segoe UI'; font-size: 13px; }
            QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 20px; background-color: #fafafa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #0078d4; }
            QPushButton { background-color: #f3f3f3; border: 1px solid #d1d1d1; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #e1f0fa; border-color: #0078d4; color: #0078d4; }
            QTextEdit, QLineEdit, QComboBox, QSpinBox { border: 1px solid #d1d1d1; border-radius: 3px; padding: 4px; background-color: #fff; }
            QPushButton#primary_btn { background-color: #0078d4; color: white; border: 1px solid #0078d4; }
            QPushButton#primary_btn:hover { background-color: #106ebe; }
            QLabel#section_title { font-weight: bold; color: #555; margin-bottom: 5px; }
        """)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")

        splitter.addWidget(self.create_left_panel())
        self.canvas = EditorCanvas()
        splitter.addWidget(self.canvas)
        splitter.addWidget(self.create_right_panel())
        
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([260, 1500, 280])
        splitter.setCollapsible(1, False)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        self.engine.initialize_ocr(lang='en')
        self.canvas.box_drawn.connect(self.on_manual_box_drawn)
        self.setup_shortcuts()

    def create_left_panel(self):
        # (Giữ nguyên phần này như code cũ của bạn)
        panel = QWidget()
        panel.setMinimumWidth(260)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        layout.addWidget(QLabel("QUẢN LÝ FILE", objectName="section_title"))
        btn_open = QPushButton("📂 Mở Ảnh Truyện ( Ctrl + O)")
        btn_open.setFixedHeight(35)
        btn_open.clicked.connect(self.open_image)
        layout.addWidget(btn_open)

        # --- NGÔN NGỮ ---
        group_lang = QGroupBox("CẤU HÌNH NGÔN NGỮ")
        grid_lang = QGridLayout()
        grid_lang.setVerticalSpacing(10)
        
        self.combo_src = QComboBox()
        self.combo_src.addItem("🇪🇸 Tây Ban Nha", "es") 
        self.combo_src.addItem("🇯🇵 Tiếng Nhật", "japan")
        self.combo_src.addItem("🇰🇷 Tiếng Hàn", "korean")
        self.combo_src.addItem("🇨🇳 Tiếng Trung", "chinese_cht")
        self.combo_src.addItem("🇺🇸 Tiếng Anh", "en")
        self.combo_src.currentIndexChanged.connect(self.change_ocr_language)

        self.combo_dest = QComboBox()
        self.combo_dest.addItems(["🇺🇸 Tiếng Anh", "🇻🇳 Tiếng Việt"])

        grid_lang.addWidget(QLabel("Nguồn:"), 0, 0)
        grid_lang.addWidget(self.combo_src, 1, 0)
        grid_lang.addWidget(QLabel("Đích:"), 2, 0)
        grid_lang.addWidget(self.combo_dest, 3, 0)
        group_lang.setLayout(grid_lang)
        layout.addWidget(group_lang)

        # --- THAO TÁC ---
        group_action = QGroupBox("CÔNG CỤ")
        vbox = QVBoxLayout()
        vbox.setSpacing(10)
        
        self.btn_draw_manual = QPushButton("✏️ Tạo Hộp ( Ctrl + D )")
        self.btn_draw_manual.setFixedHeight(35)
        self.btn_draw_manual.setCheckable(True)
        self.btn_draw_manual.clicked.connect(self.toggle_draw_mode)
        self.btn_draw_manual.setStyleSheet("""
            QPushButton:checked { background-color: #ffcccc; border: 2px solid #ff0000; color: #cc0000; font-weight: bold;}
        """)

        self.btn_ocr = QPushButton("🔍 1. Quét Chữ (OCR) ( F1 )")
        self.btn_ocr.setObjectName("primary_btn")
        self.btn_ocr.setFixedHeight(40)
        self.btn_ocr.clicked.connect(self.start_ocr)

        self.btn_translate = QPushButton("🌏 2. Dịch Tự Động ( F2 )")
        self.btn_translate.setFixedHeight(35)
        self.btn_translate.clicked.connect(self.start_translate)

        vbox.addWidget(self.btn_draw_manual)
        vbox.addWidget(self.btn_ocr)
        vbox.addWidget(self.btn_translate)
        group_action.setLayout(vbox)
        layout.addWidget(group_action)

        layout.addStretch()
        
        # --- TIẾN TRÌNH ---
        self.lbl_progress = QLabel("Sẵn sàng")
        self.lbl_progress.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.lbl_progress)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #e0e0e0; border-radius: 4px; } QProgressBar::chunk { background: #0078d4; border-radius: 4px; }")
        layout.addWidget(self.progress_bar)
        
        # Nút Xuất ảnh
        self.btn_export = QPushButton("💾 Xuất Ảnh ( Ctrl + S )") 
        self.btn_export.setObjectName("primary_btn")
        self.btn_export.setFixedHeight(40)
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.export_image)
        layout.addWidget(self.btn_export)

        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(280)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        layout.addWidget(QLabel("THUỘC TÍNH LAYER", objectName="section_title"))

        # --- NHÓM NỘI DUNG ---
        group_text = QGroupBox("NỘI DUNG")
        vbox_text = QVBoxLayout()
        vbox_text.setSpacing(8)

        # Text Gốc
        lbl_raw = QLabel("Text Gốc (OCR):")
        lbl_raw.setStyleSheet("font-weight: bold; color: #555;")
        vbox_text.addWidget(lbl_raw)

        self.txt_raw = QTextEdit()
        self.txt_raw.setPlaceholderText("Nhập nội dung gốc tại đây...")
        self.txt_raw.setMaximumHeight(80)
        self.txt_raw.setReadOnly(False) 
        self.txt_raw.setStyleSheet("background-color: #fff; color: #333; border: 1px solid #ccc;")
        self.txt_raw.textChanged.connect(self.update_raw_text_from_inspector)
        vbox_text.addWidget(self.txt_raw)

        vbox_text.addSpacing(10)

        # Bản Dịch
        lbl_trans = QLabel("Bản Dịch (Edit):")
        lbl_trans.setStyleSheet("font-weight: bold; color: #0078d4;")
        vbox_text.addWidget(lbl_trans)

        self.txt_trans = QTextEdit()
        self.txt_trans.setPlaceholderText("Nhập kết quả dịch...")
        self.txt_trans.setMinimumHeight(100)
        self.txt_trans.setStyleSheet("background-color: #fff; border: 1px solid #0078d4;")
        self.txt_trans.textChanged.connect(self.update_box_from_inspector)
        vbox_text.addWidget(self.txt_trans)

        group_text.setLayout(vbox_text)
        layout.addWidget(group_text)

        # --- NHÓM TYPOGRAPHY ---
        group_font = QGroupBox("TYPOGRAPHY")
        grid_font = QGridLayout()
        grid_font.setVerticalSpacing(12)
        grid_font.setHorizontalSpacing(8)
        
        self.combo_font = QComboBox() 
        self.combo_font.addItems(["Comic Sans MS", "Arial", "Times New Roman", "Segoe UI", "Verdana"])
        self.combo_font.setFixedHeight(30)
        # [FIX] Đã thêm kết nối này: Thay đổi font -> Cập nhật ngay
        self.combo_font.currentTextChanged.connect(self.update_box_from_inspector)
        
        self.spin_size = QSpinBox() 
        self.spin_size.setValue(14)
        self.spin_size.setRange(8, 200)
        self.spin_size.setSuffix(" px")
        self.spin_size.setFixedHeight(30)
        self.spin_size.valueChanged.connect(self.update_box_from_inspector)

        self.btn_minus_size = QPushButton("-")
        self.btn_minus_size.setFixedSize(30, 30)
        self.btn_minus_size.clicked.connect(self.decrease_font_size)

        self.btn_plus_size = QPushButton("+")
        self.btn_plus_size.setFixedSize(30, 30)
        self.btn_plus_size.clicked.connect(self.increase_font_size)

        self.btn_color = QPushButton()
        self.btn_color.setFixedSize(30, 30)
        self.btn_color.setCursor(Qt.PointingHandCursor)
        self.btn_color.setStyleSheet("background-color: black; border: 1px solid #aaa; border-radius: 4px;")
        self.btn_color.clicked.connect(self.pick_text_color)
        
        grid_font.addWidget(QLabel("Font:"), 0, 0)
        grid_font.addWidget(self.combo_font, 0, 1, 1, 3) 
        grid_font.addWidget(QLabel("Size:"), 1, 0)
        grid_font.addWidget(self.btn_minus_size, 1, 1)
        grid_font.addWidget(self.spin_size, 1, 2)
        grid_font.addWidget(self.btn_plus_size, 1, 3)
        grid_font.addWidget(QLabel("Màu Chữ:"), 2, 0)
        grid_font.addWidget(self.btn_color, 2, 1)
        
        group_font.setLayout(grid_font)
        layout.addWidget(group_font)

        # --- NHÓM BONG BÓNG ---
        group_bubble = QGroupBox("BONG BÓNG THOẠI")
        l_bubble = QVBoxLayout()
        
        self.btn_bg_color = QPushButton("⬜  Màu Nền (Background)")
        self.btn_bg_color.setCursor(Qt.PointingHandCursor)
        self.btn_bg_color.setFixedHeight(35)
        self.btn_bg_color.setStyleSheet("text-align: left; background-color: white; color: black; border: 1px solid #ccc; padding-left: 10px;")
        self.btn_bg_color.clicked.connect(self.pick_bg_color)
        
        l_bubble.addWidget(self.btn_bg_color)
        group_bubble.setLayout(l_bubble)
        layout.addWidget(group_bubble)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    # ==========================================================================
    # LOGIC
    # ==========================================================================
    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Mở Ảnh", "", "Images (*.jpg *.png *.webp)")
        if file_path:
            self.current_image_path = file_path
            self.canvas.scene.clear()
            self.current_box = None
            self.progress_bar.setValue(0)
            self.lbl_progress.setText("Đã mở ảnh")
            
            pixmap = QPixmap(file_path)
            self.current_image_item = QGraphicsPixmapItem(pixmap)
            self.current_image_item.setZValue(-1)
            self.canvas.scene.addItem(self.current_image_item)
            self.canvas.fitInView(self.current_image_item, Qt.KeepAspectRatio)
            self.canvas.zoom_widget.show()

    def update_raw_text_from_inspector(self):
            if self.current_box:
                self.current_box.text_raw = self.txt_raw.toPlainText()

    def change_ocr_language(self):
        lang_code = self.combo_src.currentData()
        self.engine.initialize_ocr(lang_code)

    def toggle_draw_mode(self):
        is_drawing = self.btn_draw_manual.isChecked()
        if is_drawing:
            self.btn_draw_manual.setText("🛑 Dừng Vẽ")
            self.canvas.set_drawing_mode(True)
            self.lbl_progress.setText("Đang ở chế độ vẽ tay (Kéo chuột trên ảnh)")
        else:
            self.btn_draw_manual.setText("✏️ Vẽ Khung Thủ Công")
            self.canvas.set_drawing_mode(False)
            self.lbl_progress.setText("Sẵn sàng")

    def start_ocr(self):
        if not self.current_image_path:
            QMessageBox.warning(self, "Lỗi", "Vui lòng mở ảnh trước!")
            return
        
        self.btn_ocr.setEnabled(False)
        self.lbl_progress.setText("Đang phân tích OCR...")
        self.progress_bar.setValue(0)
        self.engine.run_ocr(self.current_image_path)

    def on_ocr_finished(self, boxes):
        self.btn_ocr.setEnabled(True)
        merged_boxes = merge_ocr_boxes(boxes, y_threshold=25) 
        
        self.lbl_progress.setText(f"Xong! Tìm thấy {len(boxes)} dòng, gộp thành {len(merged_boxes)} câu.")
        self.progress_bar.setValue(100)
        
        for item in self.canvas.scene.items():
            if isinstance(item, OCRBoxItem):
                self.canvas.scene.removeItem(item)

        for i, b in enumerate(merged_boxes):
            x, y, w, h = b['rect']
            text = b['text']
            box_item = OCRBoxItem(x, y, w, h, text, self, i)
            self.canvas.scene.addItem(box_item)

    def on_manual_box_drawn(self, x, y, w, h):
        self.btn_draw_manual.setChecked(False)
        self.toggle_draw_mode()

        existing_indices = [item.index for item in self.canvas.scene.items() if isinstance(item, OCRBoxItem)]
        new_index = max(existing_indices) + 1 if existing_indices else 0

        # Tạo box với Text Gốc tạm thời là "Đang quét..."
        box_item = OCRBoxItem(x, y, w, h, "Đang quét...", self, new_index)
        box_item.text_trans = "..." 
        
        self.canvas.scene.addItem(box_item)
        self.update_inspector_from_box(box_item)
        
        # [QUAN TRỌNG] GỌI ENGINE ĐỂ QUÉT CHỮ TRONG VÙNG VỪA VẼ
        if self.current_image_path:
            self.engine.run_crop_ocr(self.current_image_path, x, y, w, h, new_index)

    def on_crop_ocr_done(self, index, text):
        """Khi AI quét xong vùng vẽ tay"""
        # Tìm box có index tương ứng
        target_box = None
        for item in self.canvas.scene.items():
            if isinstance(item, OCRBoxItem) and item.index == index:
                target_box = item
                break
        
        if target_box:
            # Cập nhật Text Gốc
            target_box.text_raw = text if text.strip() else ""
            
            # Nếu Text Gốc rỗng (vẽ nhầm chỗ trắng), báo hiệu cho người dùng
            if not target_box.text_raw:
                target_box.text_trans = "(Không tìm thấy chữ)"
            else:
                target_box.text_trans = "Chờ dịch..." 

            # Nếu box này đang được chọn, cập nhật luôn giao diện bên phải
            if self.current_box == target_box:
                self.update_inspector_from_box(target_box)

    def start_translate(self):
        items = [item for item in self.canvas.scene.items() if isinstance(item, OCRBoxItem)]
        if not items:
            QMessageBox.warning(self, "Lỗi", "Chưa có khung chữ nào!")
            return

        text_data = [(item.index, item.text_raw) for item in items]
        src_lang = self.combo_src.currentData()
        dest_lang = "vi" if self.combo_dest.currentIndex() == 1 else "en"
        
        self.lbl_progress.setText("Đang dịch thuật...")
        self.progress_bar.setValue(0)
        self.engine.run_batch_translation(text_data, src_lang, dest_lang)

    def on_single_translation_done(self, index, translated_text):
        for item in self.canvas.scene.items():
            if isinstance(item, OCRBoxItem) and item.index == index:
                # Dùng font/size đang lưu trong box (vì đây là dịch tự động hàng loạt)
                # Hoặc dùng mặc định nếu chưa set
                item.set_translated_text(translated_text, item.current_font, item.current_size)
                
                if self.current_box == item:
                    self.txt_trans.setText(translated_text)
                break

    def on_all_done(self):
        self.lbl_progress.setText("Đã dịch xong toàn bộ!")
        self.progress_bar.setValue(100)
        QMessageBox.information(self, "Xong", "Dịch thuật hoàn tất!")

    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def pick_text_color(self):
        color = QColorDialog.getColor(Qt.black, self, "Chọn màu chữ")
        if color.isValid():
            self.btn_color.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc; border-radius: 4px;")
            if self.current_box:
                self.current_box.update_style(text_color=color)

    def pick_bg_color(self):
        color = QColorDialog.getColor(Qt.white, self, "Chọn màu nền")
        if color.isValid():
            text_color = "white" if color.lightness() < 128 else "black"
            self.btn_bg_color.setStyleSheet(f"text-align: left; background-color: {color.name()}; color: {text_color}")
            if self.current_box:
                self.current_box.update_style(bg_color=color)

    # --- [CLEANED] CHỈ GIỮ LẠI 1 HÀM UPDATE INSPECTOR DUY NHẤT ---
    def update_inspector_from_box(self, box_item):
        """Load dữ liệu từ Box đang chọn lên thanh UI bên phải"""
        self.current_box = box_item
        
        # Block signals
        self.txt_raw.blockSignals(True)
        self.txt_trans.blockSignals(True)
        self.combo_font.blockSignals(True)
        self.spin_size.blockSignals(True)
        
        # Set Data
        self.txt_raw.setText(box_item.text_raw)
        self.txt_trans.setText(box_item.text_trans)
        self.combo_font.setCurrentText(box_item.current_font) 
        self.spin_size.setValue(box_item.current_size)

        # Set Colors UI
        c_text = box_item.current_text_color
        c_bg = box_item.current_bg_color
        self.btn_color.setStyleSheet(f"background-color: {c_text.name()}; border: 1px solid #ccc; border-radius: 4px;")
        lbl_color = "white" if c_bg.lightness() < 128 else "black"
        self.btn_bg_color.setStyleSheet(f"text-align: left; background-color: {c_bg.name()}; color: {lbl_color}")

        # Unblock signals
        self.txt_raw.blockSignals(False)
        self.txt_trans.blockSignals(False)
        self.combo_font.blockSignals(False)
        self.spin_size.blockSignals(False)

        # Highlight
        for item in self.canvas.scene.items():
            if isinstance(item, OCRBoxItem):
                item.setPen(QPen(QColor("#ff0000"), 2, Qt.DashLine))
        box_item.setPen(QPen(QColor("#0078d4"), 3, Qt.SolidLine))

    # --- [CLEANED] CHỈ GIỮ LẠI 1 HÀM UPDATE BOX DUY NHẤT ---
    def update_box_from_inspector(self):
        """Khi UI thay đổi (Text, Font, Size) -> Cập nhật vào Box"""
        if self.current_box:
            self.current_box.text_trans = self.txt_trans.toPlainText()
            
            # Lấy thông số từ UI
            font = self.combo_font.currentText()
            size = self.spin_size.value()
            
            # Cập nhật Box (Hàm này trong OCRBoxItem đã tự lưu font/size)
            self.current_box.set_translated_text(self.current_box.text_trans, font, size)

    def increase_font_size(self):
        val = self.spin_size.value()
        self.spin_size.setValue(val + 1)

    def decrease_font_size(self):
        val = self.spin_size.value()
        self.spin_size.setValue(val - 1)      

    def export_image(self):
        if not self.current_image_path or not self.current_image_item:
            QMessageBox.warning(self, "Lỗi", "Chưa có ảnh nào để xuất!")
            return

        dir_name = os.path.dirname(self.current_image_path)
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        default_name = os.path.join(dir_name, f"{base_name}_trans.webp")

        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Lưu Ảnh Dịch", 
            default_name, 
            "WEBP Image (*.webp);;JPG Image (*.jpg);;PNG Image (*.png)"
        )

        if not file_path:
            return

        self.canvas.clearFocus()
        self.current_box = None
        
        hidden_items = []
        for item in self.canvas.scene.items():
            if isinstance(item, OCRBoxItem):
                item.original_pen = item.pen()
                item.setPen(QPen(Qt.NoPen))
                hidden_items.append(item)

        rect = self.current_image_item.boundingRect()
        image_size = rect.size().toSize()
        
        image = QPixmap(image_size)
        image.fill(Qt.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        self.canvas.scene.render(painter, target=rect, source=rect)
        painter.end()

        quality = 95 if file_path.lower().endswith(('.jpg', '.jpeg')) else -1
        success = image.save(file_path, quality=quality)

        for item in hidden_items:
            item.setPen(item.original_pen)

        if success:
            QMessageBox.information(self, "Thành công", f"Đã lưu ảnh (WEBP) tại:\n{file_path}")
        else:
            QMessageBox.critical(self, "Lỗi", "Không thể lưu file ảnh!")

    def setup_shortcuts(self):
        """Cài đặt các phím tắt cho Tab Dịch Thuật"""
        
        # 1. Ctrl + O : Mở Ảnh
        self.shortcut_open = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_open.activated.connect(self.open_image)

        # 2. Ctrl + S : Lưu/Xuất Ảnh
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.export_image)

        # 3. Ctrl + D : Bật/Tắt chế độ Vẽ Thủ Công (Draw)
        self.shortcut_draw = QShortcut(QKeySequence("Ctrl+D"), self)
        # Mẹo: Gọi hàm click() của nút để nó tự đổi màu (Checked/Unchecked) trên giao diện luôn
        self.shortcut_draw.activated.connect(self.btn_draw_manual.click)

        # 4. F1 : Quét OCR
        self.shortcut_ocr = QShortcut(QKeySequence("F1"), self)
        self.shortcut_ocr.activated.connect(self.start_ocr)

        # 5. F2 : Dịch Tự Động
        self.shortcut_trans = QShortcut(QKeySequence("F2"), self)
        self.shortcut_trans.activated.connect(self.start_translate)