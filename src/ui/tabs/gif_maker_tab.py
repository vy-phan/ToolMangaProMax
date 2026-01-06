import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTextEdit, 
                               QProgressBar, QGroupBox, QGridLayout, 
                               QSpinBox, QFileDialog, QMessageBox, QStyle)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.gif_maker import GifMakerWorker

class GifMakerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.source_dir = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Style chung (Không nền đen, chữ xanh)
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
        # 1. INPUT
        # ======================================================================
        group_input = QGroupBox(" 1. CHỌN THƯ MỤC ẢNH ")
        group_input.setStyleSheet(groupbox_style)
        input_layout = QHBoxLayout()
        
        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("Đường dẫn chứa các file ảnh (1.jpg, 2.jpg...)...")
        self.txt_source.setReadOnly(True)
        
        self.btn_source = QPushButton(" Chọn Folder")
        self.btn_source.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.btn_source.setCursor(Qt.PointingHandCursor)
        self.btn_source.clicked.connect(self.select_source_folder)
        
        input_layout.addWidget(self.txt_source)
        input_layout.addWidget(self.btn_source)
        group_input.setLayout(input_layout)
        main_layout.addWidget(group_input)

        # ======================================================================
        # 2. CẤU HÌNH (TỐC ĐỘ, TÊN FILE)
        # ======================================================================
        group_config = QGroupBox(" 2. CẤU HÌNH GIF ")
        group_config.setStyleSheet(groupbox_style)
        config_layout = QGridLayout()
        config_layout.setVerticalSpacing(15)

        # Tên file Output
        self.txt_filename = QLineEdit()
        self.txt_filename.setPlaceholderText("Ví dụ: animation (không cần đuôi .gif)")
        self.txt_filename.setText("output_animation")

        # Tốc độ (Duration)
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(10, 5000)
        self.spin_duration.setValue(200) # Mặc định 200ms
        self.spin_duration.setSuffix(" ms")
        self.spin_duration.setSingleStep(10)
        
        lbl_hint_speed = QLabel("(Thấp = Nhanh, Cao = Chậm. VD: 100ms=Nhanh, 500ms=Chậm)")
        lbl_hint_speed.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")

        # Kích thước (Optional)
        self.spin_width = QSpinBox()
        self.spin_width.setRange(0, 5000)
        self.spin_width.setValue(0)
        self.spin_width.setSuffix(" px")
        self.spin_width.setSpecialValueText("Giữ nguyên gốc (Auto)")
        
        lbl_hint_size = QLabel("(Nhập chiều rộng muốn resize. Để 0 nếu muốn giữ nguyên)")
        lbl_hint_size.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")

        # Layout Grid
        config_layout.addWidget(QLabel("📂 Tên file đầu ra:"), 0, 0)
        config_layout.addWidget(self.txt_filename, 0, 1, 1, 2)
        
        config_layout.addWidget(QLabel("⏱️ Thời gian/khung:"), 1, 0)
        config_layout.addWidget(self.spin_duration, 1, 1)
        config_layout.addWidget(lbl_hint_speed, 1, 2)

        config_layout.addWidget(QLabel("📏 Chiều rộng (Width):"), 2, 0)
        config_layout.addWidget(self.spin_width, 2, 1)
        config_layout.addWidget(lbl_hint_size, 2, 2)

        group_config.setLayout(config_layout)
        main_layout.addWidget(group_config)

        # ======================================================================
        # 3. LOG & RUN
        # ======================================================================
        group_log = QGroupBox(" NHẬT KÝ XỬ LÝ ")
        group_log.setStyleSheet(groupbox_style)
        log_layout = QVBoxLayout()
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        self.log_area.setStyleSheet("background-color: #0a0a0a; color: #00ff00; border: none;")
        log_layout.addWidget(self.log_area)
        
        group_log.setLayout(log_layout)
        main_layout.addWidget(group_log)

        self.btn_run = QPushButton(" TẠO ẢNH ĐỘNG (GIF)")
        self.btn_run.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(45)
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_run.clicked.connect(self.start_maker)
        
        main_layout.addWidget(self.btn_run)
        
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setStyleSheet("QProgressBar { background-color: #ddd; color: black; border: 1px solid #bbb; height: 10px; border-radius: 5px; } QProgressBar::chunk { background-color: #0078d4; border-radius: 5px; }")
        main_layout.addWidget(self.progress)

        self.setLayout(main_layout)

    # --- LOGIC ---
    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa ảnh")
        if folder:
            self.source_dir = folder
            self.txt_source.setText(folder)

    def log(self, msg, level="info"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {"info": "#d4d4d4", "success": "#a6e22e", "error": "#f92672", "process": "#66d9ef"}
        c = colors.get(level, "#d4d4d4")
        self.log_area.append(f'<span style="color: #666;">[{time_str}]</span> <span style="color: {c};">{msg}</span>')
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def start_maker(self):
        if not self.source_dir:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn thư mục chứa ảnh!")
            return

        filename = self.txt_filename.text().strip()
        if not filename:
            filename = "output_animation"
        if not filename.lower().endswith('.gif'):
            filename += ".gif"

        # Đường dẫn output nằm ngay trong folder nguồn
        import os
        output_path = os.path.join(self.source_dir, filename)

        self.btn_run.setEnabled(False)
        self.log_area.clear()
        
        self.worker = GifMakerWorker(
            self.source_dir, 
            output_path, 
            self.spin_duration.value(),
            self.spin_width.value()
        )
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, msg):
        self.btn_run.setEnabled(True)
        self.log(msg, "success")
        QMessageBox.information(self, "Thông báo", msg)