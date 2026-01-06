import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QComboBox, QTextEdit, 
                               QProgressBar, QGroupBox, QGridLayout, 
                               QRadioButton, QButtonGroup, QSpinBox, 
                               QFileDialog, QMessageBox, QStyle, QApplication)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QCursor

# Import từ Core
from core.workers import ScanWorker
from core.downloader import DownloadAndProcessWorker

class DownloaderTab(QWidget):
    def __init__(self, scrapers):
        super().__init__()
        self.scrapers = scrapers
        self.current_images = []
        
        self.init_ui()
        
        # --- TRẠNG THÁI BAN ĐẦU ---
        # Tìm tham chiếu group_input
        self.group_input = self.findChild(QGroupBox, "group_input")
        
        # Disable các bước sau
        self.group_config.setEnabled(False)
        self.group_action.setEnabled(False)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20) # Tăng khoảng cách giữa các nhóm cho thoáng

        # CSS chung cho GroupBox (Xóa nền đen, chữ màu xanh dễ nhìn)
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
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                color: #0078d4; /* Màu xanh dương đậm dễ nhìn */
                font-size: 11px;
            }
        """

        # ======================================================================
        # BƯỚC 1: INPUT
        # ======================================================================
        self.group_input = QGroupBox(" BƯỚC 1: NHẬP DỮ LIỆU ")
        self.group_input.setObjectName("group_input")
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
        
        self.btn_scan = QPushButton(" QUÉT DỮ LIỆU")
        icon_scan = self.style().standardIcon(QStyle.SP_BrowserReload)
        self.btn_scan.setIcon(icon_scan)
        self.btn_scan.setCursor(Qt.PointingHandCursor)
        self.btn_scan.setMinimumHeight(35)
        self.btn_scan.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; font-weight: bold; border-radius: 4px; } 
            QPushButton:hover { background-color: #0063b1; }
        """)
        self.btn_scan.clicked.connect(self.start_scan)
        
        # Sắp xếp Grid thẳng hàng
        input_layout.addWidget(QLabel("🔌 Plugin:"), 0, 0)
        input_layout.addWidget(self.combo_source, 0, 1)
        
        input_layout.addWidget(QLabel("🔗 Url:"), 1, 0)
        input_layout.addWidget(self.input_url, 1, 1)
        
        input_layout.addWidget(self.btn_scan, 0, 2, 2, 1) # Nút scan chiếm 2 hàng
        input_layout.setColumnStretch(1, 3) # Cột giữa giãn rộng
        
        self.group_input.setLayout(input_layout)
        main_layout.addWidget(self.group_input)

        # ======================================================================
        # BƯỚC 2: CẤU HÌNH (GỌN GÀNG HƠN)
        # ======================================================================
        self.group_config = QGroupBox(" BƯỚC 2: CẤU HÌNH XUẤT FILE ")
        self.group_config.setStyleSheet(groupbox_style)
        
        # Dùng Grid Layout để căn thẳng tắp
        config_layout = QGridLayout()
        config_layout.setVerticalSpacing(15)
        config_layout.setHorizontalSpacing(10)

        # --- Row 1: Chế độ xuất ---
        lbl_mode = QLabel("🛠️ Chế độ:")
        
        self.radio_single = QRadioButton("Ảnh Rời ( Tải Thô)")
        self.radio_merge = QRadioButton("Ghép Dọc ( Manga )")
        self.radio_pdf = QRadioButton("PDF Sách ")
        self.radio_merge.setChecked(True)
        
        self.bg_mode = QButtonGroup()
        self.bg_mode.addButton(self.radio_single)
        self.bg_mode.addButton(self.radio_merge)
        self.bg_mode.addButton(self.radio_pdf)
        
        layout_radios = QHBoxLayout()
        layout_radios.addWidget(self.radio_single)
        layout_radios.addWidget(self.radio_merge)
        layout_radios.addWidget(self.radio_pdf)
        layout_radios.addStretch() # Đẩy sang trái

        config_layout.addWidget(lbl_mode, 0, 0)
        config_layout.addLayout(layout_radios, 0, 1, 1, 5) # Chiếm hết chiều ngang còn lại

        # --- Row 2: Định dạng & Chất lượng ---
        # Cột 1: Định dạng
        lbl_fmt = QLabel("🖼️ Định dạng:")
        self.combo_format = QComboBox()
        self.combo_format.addItems(["JPG (Chuẩn)", "PNG (Nét căng)", "WEBP (Nhẹ nhất)"])
        
        # Cột 2: Chất lượng
        lbl_qual = QLabel("🎨 Chất lượng:")
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(60, 100)
        self.spin_quality.setValue(95)
        self.spin_quality.setSuffix(" %")
        self.spin_quality.setFixedWidth(70)
        
        # Label hiển thị Min-Max
        lbl_range = QLabel("(60 - 100)")
        lbl_range.setStyleSheet("color: #777; font-size: 11px; font-style: italic;")

        # Add vào Grid (Thẳng hàng)
        # Cấu trúc: Label | Combo | Spacer | Label | SpinBox | Range
        config_layout.addWidget(lbl_fmt, 1, 0)
        config_layout.addWidget(self.combo_format, 1, 1)
        
        # Thêm cột trống ở giữa để tách ra
        config_layout.setColumnMinimumWidth(2, 30) 
        
        config_layout.addWidget(lbl_qual, 1, 3)
        config_layout.addWidget(self.spin_quality, 1, 4)
        config_layout.addWidget(lbl_range, 1, 5)
        
        config_layout.setColumnStretch(6, 1) # Đẩy mọi thứ sang trái

        self.group_config.setLayout(config_layout)
        main_layout.addWidget(self.group_config)

        # ======================================================================
        # BƯỚC 3: LOGGING
        # ======================================================================
        group_log = QGroupBox(" LOG HỆ THỐNG ")
        group_log.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 6px; margin-top: 10px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #555; }
        """)
        log_layout = QVBoxLayout()
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setStyleSheet("background-color: #0a0a0a; color: #00ff00; border: none;")
        log_layout.addWidget(self.log_area)
        
        group_log.setLayout(log_layout)
        main_layout.addWidget(group_log)

        # ======================================================================
        # BƯỚC 4: ACTION
        # ======================================================================
        self.group_action = QGroupBox(" BƯỚC 3: THỰC THI ")
        self.group_action.setStyleSheet("""
            QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 6px; margin-top: 10px; } 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #27ae60; }
        """)
        action_layout = QHBoxLayout()
        
        self.lbl_status = QLabel("⚠️ VUI LÒNG QUÉT DỮ LIỆU TRƯỚC")
        self.lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")
        
        self.btn_download = QPushButton(" TIẾN HÀNH TẢI & XỬ LÝ")
        icon_download = self.style().standardIcon(QStyle.SP_DialogSaveButton)
        self.btn_download.setIcon(icon_download)
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.setMinimumHeight(45)
        self.btn_download.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #219150; }
            QPushButton:disabled { background-color: #999; color: #ccc; }
        """)
        self.btn_download.clicked.connect(self.start_download)
        
        action_layout.addWidget(self.lbl_status)
        action_layout.addStretch()
        action_layout.addWidget(self.btn_download)
        
        self.group_action.setLayout(action_layout)
        main_layout.addWidget(self.group_action)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #ddd; color: black; border: 1px solid #bbb; height: 10px; border-radius: 5px; margin-top: 5px;} 
            QProgressBar::chunk { background-color: #0078d4; border-radius: 5px; }
        """)
        main_layout.addWidget(self.progress)

        self.setLayout(main_layout)

    # --- TÍNH NĂNG: AUTO DETECT DOMAIN ---
    def auto_detect_source(self):
        url = self.input_url.text().strip().lower()
        if not url: return

        for name, scraper in self.scrapers.items():
            if scraper.domain in url:
                index = self.combo_source.findText(name)
                if index != -1 and index != self.combo_source.currentIndex():
                    self.combo_source.setCurrentIndex(index)
                    self.lbl_status.setText(f"🤖 ĐÃ TỰ CHỌN: {name}")
                    self.lbl_status.setStyleSheet("color: #0078d4; font-weight: bold;")
                break

    # --- LOGIC ---
    def log(self, msg, level="info"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {
            "info": "#d4d4d4", "success": "#a6e22e", 
            "warning": "#e6db74", "error": "#f92672", 
            "process": "#66d9ef", "url": "#569cd6", "index": "#ae81ff"
        }
        c = colors.get(level, colors["info"])
        html_msg = f'<span style="color: #666;">[{time_str}]</span> <span style="color: {c};">{msg}</span>'
        self.log_area.append(html_msg)
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def start_scan(self):
        url = self.input_url.text().strip()
        source = self.combo_source.currentText()
        if not url: return
        
        self.log_area.clear()
        self.log(f"Đang kết nối tới: {source}...", "process")
        
        self.group_config.setEnabled(False)
        self.group_action.setEnabled(False)
        self.lbl_status.setText("⏳ ĐANG QUÉT DỮ LIỆU...")
        self.lbl_status.setStyleSheet("color: #f0ad4e; font-weight: bold;")
        
        self.btn_scan.setEnabled(False)
        self.input_url.setEnabled(False)
        
        scraper = self.scrapers[source]
        self.scan_worker = ScanWorker(scraper, url)
        self.scan_worker.finished.connect(self.on_scan_done)
        self.scan_worker.error.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scan_done(self, images):
        self.btn_scan.setEnabled(True)
        self.input_url.setEnabled(True)
        self.current_images = images
        
        if not images:
            self.log("Không tìm thấy ảnh nào.", "warning")
            self.lbl_status.setText("❌ KHÔNG TÌM THẤY ẢNH")
            self.lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")
            return
            
        self.log(f"--- KẾT QUẢ TÌM KIẾM ---", "info")
        display_limit = 100 
        for i, img_url in enumerate(images):
            if i >= display_limit:
                self.log(f"... và {len(images) - display_limit} ảnh khác ...", "warning")
                break
            msg = f"<span style='color:#ae81ff'>[{i+1:03d}]</span> {img_url}"
            self.log_area.append(msg)
            
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
        self.log(f"⚡ Đã tìm thấy tổng cộng: {len(images)} ảnh.", "success")
        
        self.group_config.setEnabled(True)
        self.group_action.setEnabled(True)
        self.lbl_status.setText(f"✅ SẴN SÀNG: {len(images)} ẢNH")
        self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold;")

    def on_scan_error(self, err):
        self.btn_scan.setEnabled(True)
        self.input_url.setEnabled(True)
        self.log(f"Lỗi: {err}", "error")
        self.lbl_status.setText("❌ LỖI KẾT NỐI")
        self.lbl_status.setStyleSheet("color: #d9534f; font-weight: bold;")

    def start_download(self):
        save_dir = QFileDialog.getExistingDirectory(self, "Chọn Thư Mục Lưu")
        if not save_dir: return
        
        is_merge = self.radio_merge.isChecked()
        is_pdf = self.radio_pdf.isChecked()
        quality = self.spin_quality.value()
        fmt_text = self.combo_format.currentText()
        
        if "JPG" in fmt_text: fmt = "jpg"
        elif "PNG" in fmt_text: fmt = "png"
        else: fmt = "webp"
        
        self.log(f"Khởi động tiến trình tải...", "process")
        self.btn_download.setEnabled(False)
        self.group_config.setEnabled(False)
        self.group_input.setEnabled(False)
        
        self.worker = DownloadAndProcessWorker(self.current_images, save_dir, fmt, is_merge, is_pdf, quality)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
        
    def on_finished(self, msg):
        self.btn_download.setEnabled(True)
        self.group_config.setEnabled(True)
        self.group_input.setEnabled(True)
        
        self.log(msg, "success")
        self.progress.setValue(100)
        self.lbl_status.setText("🎉 HOÀN TẤT")
        QMessageBox.information(self, "Thông báo", msg)