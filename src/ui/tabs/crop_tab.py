
import sys
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QFileDialog, QGraphicsView, 
                               QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, 
                               QSlider, QFrame, QMessageBox, QSplitter, QGroupBox)
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPixmap, QColor, QPen, QBrush, QPainter, QCursor

# ==============================================================================
# 1. ZOOM CONTROL (Copied and adapted from TranslatorTab)
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
# 2. CROP BOX ITEM (Resizable Rectangle)
# ==============================================================================
class CropBoxItem(QGraphicsRectItem):
    # Handles 
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

    def __init__(self, x, y, w, h):
        super().__init__(x, y, w, h)
        
        # Style cho khung crop
        self.setPen(QPen(QColor("#0078d4"), 2, Qt.DashLine))
        self.setBrush(QBrush(QColor(0, 120, 212, 50))) # Màu xanh nhạt trong suốt
        
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
        
        # Đảm bảo width/height không âm
        if rect.width() < 10: rect.setWidth(10)
        if rect.height() < 10: rect.setHeight(10)

        self.setRect(rect)
        self.mousePressPos = mousePos

# ==============================================================================
# 3. CROP CANVAS
# ==============================================================================
class CropCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor("#e5e5e5")))
        
        # Widget Zoom
        self.zoom_widget = ZoomControl(self)
        self.zoom_widget.zoom_changed.connect(lambda s: (self.resetTransform(), self.scale(s, s)))
        self.zoom_widget.hide()

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
# 4. CROP TAB MAIN
# ==============================================================================
class CropTab(QWidget):
    def __init__(self):
        super().__init__()
        self.current_image_item = None
        self.current_image_path = None
        self.crop_box = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Style chung
        self.setStyleSheet("""
            QWidget { background-color: #ffffff; color: #333; font-family: 'Segoe UI'; font-size: 13px; }
            QGroupBox { font-weight: bold; border: 1px solid #e0e0e0; border-radius: 6px; margin-top: 20px; background-color: #fafafa; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #0078d4; }
            QPushButton { background-color: #f3f3f3; border: 1px solid #d1d1d1; border-radius: 4px; padding: 6px 12px; }
            QPushButton:hover { background-color: #e1f0fa; border-color: #0078d4; color: #0078d4; }
            QPushButton#primary_btn { background-color: #0078d4; color: white; border: 1px solid #0078d4; }
            QPushButton#primary_btn:hover { background-color: #106ebe; }
            QLabel#section_title { font-weight: bold; color: #555; margin-bottom: 5px; }
        """)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e0e0e0; }")

        # Left Panel
        splitter.addWidget(self.create_left_panel())
        
        # Center Canvas
        self.canvas = CropCanvas()
        splitter.addWidget(self.canvas)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 1500])

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def create_left_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(260)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        layout.addWidget(QLabel("CẮT ẢNH (CROP)", objectName="section_title"))

        # --- Nút Mở Ảnh ---
        btn_open = QPushButton("📂 Mở Ảnh")
        btn_open.setFixedHeight(40)
        btn_open.clicked.connect(self.open_image)
        layout.addWidget(btn_open)

        # --- Công cụ ---
        group_tools = QGroupBox("CÔNG CỤ")
        vbox_tools = QVBoxLayout()
        
        self.btn_create_box = QPushButton("🔲 Tạo Khung Crop")
        self.btn_create_box.clicked.connect(self.create_default_crop_box)
        vbox_tools.addWidget(self.btn_create_box)

        self.btn_reset = QPushButton("↺ Reset Khung")
        self.btn_reset.clicked.connect(self.reset_crop_box)
        vbox_tools.addWidget(self.btn_reset)

        group_tools.setLayout(vbox_tools)
        layout.addWidget(group_tools)

        layout.addStretch()

        # --- Nút Lưu Ảnh ---
        self.btn_save = QPushButton("💾 Lưu Ảnh Đã Cắt")
        self.btn_save.setObjectName("primary_btn")
        self.btn_save.setFixedHeight(45)
        self.btn_save.clicked.connect(self.save_cropped_image)
        layout.addWidget(self.btn_save)

        panel.setLayout(layout)
        return panel

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Mở Ảnh", "", "Images (*.jpg *.png *.webp *.jpeg)")
        if file_path:
            self.current_image_path = file_path
            self.canvas.scene.clear()
            self.crop_box = None
            
            pixmap = QPixmap(file_path)
            self.current_image_item = QGraphicsPixmapItem(pixmap)
            self.current_image_item.setZValue(-1)
            self.canvas.scene.addItem(self.current_image_item)
            self.canvas.fitInView(self.current_image_item, Qt.KeepAspectRatio)
            self.canvas.zoom_widget.show()

            # Tự động tạo khung crop full ảnh ban đầu
            self.create_default_crop_box()

    def create_default_crop_box(self):
        if not self.current_image_item:
            return

        # Xóa box cũ nếu có
        if self.crop_box:
            self.canvas.scene.removeItem(self.crop_box)
        
        rect = self.current_image_item.boundingRect()
        # Tạo khung crop mặc định nhỏ hơn ảnh 1 chút (80%)
        w, h = rect.width(), rect.height()
        new_w, new_h = w * 0.8, h * 0.8
        new_x, new_y = (w - new_w) / 2, (h - new_h) / 2
        
        self.crop_box = CropBoxItem(new_x, new_y, new_w, new_h)
        self.crop_box.setZValue(10)
        self.canvas.scene.addItem(self.crop_box)
        self.crop_box.setSelected(True)

    def reset_crop_box(self):
        if self.current_image_item:
            self.create_default_crop_box()

    def save_cropped_image(self):
        if not self.current_image_item or not self.crop_box:
            QMessageBox.warning(self, "Lỗi", "Chưa có ảnh hoặc chưa tạo khung crop!")
            return

        # 1. Lấy vùng rect của box
        crop_rect = self.crop_box.rect()
        
        # 2. Map sang coordinate của Pixmap (nếu box bị move)
        # Vì CropBoxItem add trực tiếp vào scene cùng cấp với PixmapItem (ở (0,0)), 
        # nên rect.x/y chính là toạ độ trên ảnh.
        # Tuy nhiên cần đảm bảo nó nằm trong ảnh.
        img_rect = self.current_image_item.boundingRect()
        
        # Intersection để đảm bảo không crop ra ngoài ảnh
        final_rect = crop_rect.intersected(img_rect)
        
        if final_rect.isEmpty():
            QMessageBox.warning(self, "Lỗi", "Vùng chọn nằm ngoài ảnh!")
            return

        pixmap = self.current_image_item.pixmap()
        cropped_pixmap = pixmap.copy(final_rect.toRect())
        
        # 3. Lưu file
        save_path, _ = QFileDialog.getSaveFileName(self, "Lưu Ảnh", "", "PNG (*.png);;JPG (*.jpg);;WEBP (*.webp)")
        if save_path:
            cropped_pixmap.save(save_path)
            QMessageBox.information(self, "Thành công", f"Đã lưu ảnh tại:\n{save_path}")

