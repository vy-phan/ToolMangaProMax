import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                               QPushButton, QComboBox, QTextEdit, QGroupBox, 
                               QGridLayout, QStyle, QApplication, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import Worker có sẵn
from core.workers import ScanWorker

class GetLinksTab(QWidget):
    def __init__(self, scrapers):
        super().__init__()
        self.scrapers = scrapers
        self.formatted_result = "" # Biến lưu kết quả để copy
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Style chung (Giống tab Download cho đồng bộ)
        groupbox_style = """
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #aaa; 
                border-radius: 6px; 
                margin-top: 10px; 
                background-color: transparent;
            } 
            QGroupBox::title { 
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #0078d4; 
                font-size: 11px;
            }
        """

        # ======================================================================
        # PHẦN 1: NHẬP LIỆU (INPUT)
        # ======================================================================
        self.group_input = QGroupBox("1. NHẬP LINK TRUYỆN ")
        self.group_input.setStyleSheet(groupbox_style)
        
        input_layout = QGridLayout()
        input_layout.setVerticalSpacing(12)
        
        self.combo_source = QComboBox()
        self.combo_source.addItems(sorted(self.scrapers.keys()))
        self.combo_source.setMinimumHeight(30)
        
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("Ví dụ: https://omegascans.org/.../chapter-1")
        self.input_url.setClearButtonEnabled(True)
        self.input_url.setMinimumHeight(30)
        self.input_url.textChanged.connect(self.auto_detect_source)
        
        self.btn_scan = QPushButton(" LẤY LINK ẢNH")
        icon_scan = self.style().standardIcon(QStyle.SP_ArrowRight)
        self.btn_scan.setIcon(icon_scan)
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setMinimumHeight(35)
        self.btn_scan.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; font-weight: bold; border-radius: 4px; } 
            QPushButton:hover { background-color: #0063b1; }
        """)
        self.btn_scan.clicked.connect(self.start_scan)
        
        input_layout.addWidget(QLabel("🔌 Plugin:"), 0, 0)
        input_layout.addWidget(self.combo_source, 0, 1)
        
        input_layout.addWidget(QLabel("🔗 Url:"), 1, 0)
        input_layout.addWidget(self.input_url, 1, 1)
        
        input_layout.addWidget(self.btn_scan, 0, 2, 2, 1)
        input_layout.setColumnStretch(1, 3)
        
        self.group_input.setLayout(input_layout)
        main_layout.addWidget(self.group_input)

        # ======================================================================
        # PHẦN 2: KẾT QUẢ (OUTPUT)
        # ======================================================================
        self.group_result = QGroupBox("2. KẾT QUẢ (FORMAT: INDEX:URL) ")
        self.group_result.setStyleSheet(groupbox_style)
        result_layout = QVBoxLayout()

        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setPlaceholderText("Kết quả sẽ hiện ở đây...")
        self.txt_result.setFont(QFont("Consolas", 10))
        # Style trắng đen cơ bản, dễ nhìn
        self.txt_result.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9; color: #333;")
        
        # Nút Copy
        self.btn_copy = QPushButton(" COPY TO CLIPBOARD")
        icon_copy = self.style().standardIcon(QStyle.SP_DialogApplyButton)
        self.btn_copy.setIcon(icon_copy)
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setMinimumHeight(45)
        self.btn_copy.setEnabled(False) # Mặc định ẩn
        self.btn_copy.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 4px; margin-top: 5px; }
            QPushButton:hover { background-color: #219150; }
            QPushButton:disabled { background-color: #bbb; color: #eee; }
        """)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)

        result_layout.addWidget(self.txt_result)
        result_layout.addWidget(self.btn_copy)
        
        self.group_result.setLayout(result_layout)
        main_layout.addWidget(self.group_result)
        
        self.setLayout(main_layout)

    # --- LOGIC ---

    def auto_detect_source(self):
        url = self.input_url.text().strip().lower()
        if not url: return
        for name, scraper in self.scrapers.items():
            if scraper.domain in url:
                index = self.combo_source.findText(name)
                if index != -1 and index != self.combo_source.currentIndex():
                    self.combo_source.setCurrentIndex(index)
                break

    def start_scan(self):
        url = self.input_url.text().strip()
        source = self.combo_source.currentText()
        if not url: return

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText(" ĐANG XỬ LÝ...")
        self.txt_result.clear()
        self.btn_copy.setEnabled(False)

        scraper = self.scrapers[source]
        self.scan_worker = ScanWorker(scraper, url)
        self.scan_worker.finished.connect(self.on_scan_done)
        self.scan_worker.error.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_done(self, images):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText(" LẤY LINK ẢNH")
        
        if not images:
            self.txt_result.setText("Không tìm thấy ảnh nào!")
            return

        # Xử lý Format chuỗi: index:url
        # Tạo list các dòng
        lines = []
        for index, img_url in enumerate(images):
            # Format: 0:https://...
            line = f"{index}:{img_url}"
            lines.append(line)
        
        # Nối lại bằng xuống dòng
        self.formatted_result = "\n".join(lines)
        
        # Hiển thị
        self.txt_result.setPlainText(self.formatted_result)
        self.btn_copy.setEnabled(True)
        self.btn_copy.setText(f" COPY {len(images)} LINK VÀO CLIPBOARD")

    def on_scan_error(self, err):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText(" LẤY LINK ẢNH")
        self.txt_result.setText(f"Lỗi: {err}")

    def copy_to_clipboard(self):
        if not self.formatted_result: return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(self.formatted_result)
        
        QMessageBox.information(self, "Thành công", "Đã copy danh sách link vào Clipboard!")