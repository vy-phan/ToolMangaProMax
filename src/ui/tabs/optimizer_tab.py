import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QCheckBox, QTextEdit, 
                               QProgressBar, QGroupBox, QGridLayout, 
                               QSpinBox, QFileDialog, QMessageBox, QStyle, 
                               QRadioButton, QButtonGroup, QComboBox) # <--- Thêm QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from core.optimizer import OptimizerWorker

class OptimizerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.source_dir = ""
        self.dest_dir = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        groupbox_style = """
            QGroupBox { font-weight: bold; border: 1px solid #aaa; border-radius: 6px; margin-top: 10px; background-color: transparent; } 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #0078d4; font-size: 11px; }
        """

        # === 1. CHỌN THƯ MỤC NGUỒN ===
        group_input = QGroupBox(" 1. CHỌN THƯ MỤC ẢNH GỐC ")
        group_input.setStyleSheet(groupbox_style)
        input_layout = QHBoxLayout()
        
        self.txt_source = QLineEdit()
        self.txt_source.setPlaceholderText("Đường dẫn thư mục chứa ảnh cần tối ưu...")
        self.txt_source.setReadOnly(True)
        
        self.btn_source = QPushButton(" Chọn Folder")
        self.btn_source.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        self.btn_source.setCursor(Qt.PointingHandCursor)
        self.btn_source.clicked.connect(self.select_source_folder)
        
        input_layout.addWidget(self.txt_source)
        input_layout.addWidget(self.btn_source)
        group_input.setLayout(input_layout)
        main_layout.addWidget(group_input)

        # === 2. BỘ LỌC ĐẦU VÀO ===
        group_filter = QGroupBox(" 2. LỌC FILE ĐẦU VÀO ")
        group_filter.setStyleSheet(groupbox_style)
        filter_layout = QHBoxLayout()
        
        self.chk_all = QCheckBox("Tất cả (All)")
        self.chk_all.setChecked(True)
        self.chk_all.stateChanged.connect(self.toggle_extensions)
        
        self.chk_jpg = QCheckBox("JPG/JPEG")
        self.chk_png = QCheckBox("PNG")
        self.chk_webp = QCheckBox("WEBP")
        self.chk_jpg.setEnabled(False)
        self.chk_png.setEnabled(False)
        self.chk_webp.setEnabled(False)
        
        filter_layout.addWidget(self.chk_all)
        filter_layout.addWidget(self.chk_jpg)
        filter_layout.addWidget(self.chk_png)
        filter_layout.addWidget(self.chk_webp)
        filter_layout.addStretch()
        group_filter.setLayout(filter_layout)
        main_layout.addWidget(group_filter)

        # === 3. CẤU HÌNH ĐẦU RA (QUAN TRỌNG) ===
        group_config = QGroupBox(" 3. CẤU HÌNH ĐẦU RA ")
        group_config.setStyleSheet(groupbox_style)
        config_layout = QGridLayout()
        config_layout.setVerticalSpacing(15)

        # A. Định dạng đầu ra
        lbl_format = QLabel("🖼️ Định dạng đích:")
        self.combo_out_format = QComboBox()
        self.combo_out_format.addItems([
            "Giữ nguyên (Original)", 
            "JPG (Nhẹ, mất nền trong suốt)", 
            "PNG (Giữ nền, nặng)", 
            "WEBP (Khuyên dùng - Nhẹ & Nét)"
        ])
        self.combo_out_format.setCurrentIndex(3) # Mặc định chọn WEBP cho tối ưu
        
        # B. Chất lượng
        lbl_qual = QLabel("🎨 Mức chất lượng:")
        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(10, 100)
        self.spin_quality.setValue(80) 
        self.spin_quality.setSuffix(" %")
        lbl_note = QLabel("(Min: 10 - Max: 100)")
        lbl_note.setStyleSheet("color: #777; font-size: 11px;")

        # C. Nơi lưu
        lbl_out = QLabel("📂 Nơi lưu:")
        self.radio_same = QRadioButton("Lưu cùng thư mục (Thêm đuôi '_optimized')")
        self.radio_same.setChecked(True)
        self.radio_same.toggled.connect(self.toggle_output_mode)
        
        self.radio_diff = QRadioButton("Lưu sang thư mục khác (Giữ tên gốc)")
        
        self.btn_dest = QPushButton(" Chọn Nơi Lưu...")
        self.btn_dest.setEnabled(False)
        self.btn_dest.clicked.connect(self.select_dest_folder)
        self.lbl_dest_path = QLabel("Chưa chọn...")
        self.lbl_dest_path.setStyleSheet("color: #777;")
        self.lbl_dest_path.setVisible(False)

        # Layout Grid
        config_layout.addWidget(lbl_format, 0, 0)
        config_layout.addWidget(self.combo_out_format, 0, 1, 1, 2)
        
        config_layout.addWidget(lbl_qual, 1, 0)
        config_layout.addWidget(self.spin_quality, 1, 1)
        config_layout.addWidget(lbl_note, 1, 2)
        
        config_layout.addWidget(lbl_out, 2, 0)
        config_layout.addWidget(self.radio_same, 2, 1, 1, 2)
        config_layout.addWidget(self.radio_diff, 3, 1, 1, 2)
        
        dest_hbox = QHBoxLayout()
        dest_hbox.addWidget(self.btn_dest)
        dest_hbox.addWidget(self.lbl_dest_path)
        config_layout.addLayout(dest_hbox, 4, 1, 1, 2)

        group_config.setLayout(config_layout)
        main_layout.addWidget(group_config)

        # === 4. LOG & RUN ===
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

        self.btn_run = QPushButton(" BẮT ĐẦU TỐI ƯU & CHUYỂN ĐỔI")
        self.btn_run.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setMinimumHeight(45)
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 4px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_run.clicked.connect(self.start_optimization)
        
        main_layout.addWidget(self.btn_run)
        
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setStyleSheet("QProgressBar { background-color: #ddd; color: black; border: 1px solid #bbb; height: 10px; border-radius: 5px; } QProgressBar::chunk { background-color: #0078d4; border-radius: 5px; }")
        main_layout.addWidget(self.progress)

        self.setLayout(main_layout)

    # --- LOGIC ---
    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục ảnh gốc")
        if folder:
            self.source_dir = folder
            self.txt_source.setText(folder)

    def select_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu kết quả")
        if folder:
            self.dest_dir = folder
            self.lbl_dest_path.setText(folder)

    def toggle_extensions(self):
        state = not self.chk_all.isChecked()
        self.chk_jpg.setEnabled(state)
        self.chk_png.setEnabled(state)
        self.chk_webp.setEnabled(state)

    def toggle_output_mode(self):
        is_same = self.radio_same.isChecked()
        self.btn_dest.setEnabled(not is_same)
        self.lbl_dest_path.setVisible(not is_same)

    def log(self, msg, level="info"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        colors = {"info": "#d4d4d4", "success": "#a6e22e", "error": "#f92672", "process": "#66d9ef"}
        c = colors.get(level, "#d4d4d4")
        self.log_area.append(f'<span style="color: #666;">[{time_str}]</span> <span style="color: {c};">{msg}</span>')
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def start_optimization(self):
        if not self.source_dir:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn thư mục ảnh gốc!")
            return

        is_same_folder = self.radio_same.isChecked()
        dest = self.source_dir if is_same_folder else self.dest_dir

        if not is_same_folder and not dest:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn thư mục lưu kết quả!")
            return

        # Extensions Filter
        extensions = []
        if self.chk_all.isChecked():
            extensions = ['.jpg', '.jpeg', '.png', '.webp']
        else:
            if self.chk_jpg.isChecked(): extensions.extend(['.jpg', '.jpeg'])
            if self.chk_png.isChecked(): extensions.append('.png')
            if self.chk_webp.isChecked(): extensions.append('.webp')
        
        if not extensions:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn ít nhất 1 loại file đầu vào!")
            return

        # Get Target Format
        fmt_idx = self.combo_out_format.currentIndex()
        if fmt_idx == 0: target_fmt = 'original'
        elif fmt_idx == 1: target_fmt = 'jpg'
        elif fmt_idx == 2: target_fmt = 'png'
        else: target_fmt = 'webp'

        # UI Lock
        self.btn_run.setEnabled(False)
        self.log_area.clear()
        self.log(f"Bắt đầu: Input={extensions} -> Output={target_fmt.upper()}", "process")

        self.worker = OptimizerWorker(
            self.source_dir, 
            dest, 
            extensions, 
            self.spin_quality.value(), 
            is_same_folder,
            target_fmt # <--- Truyền tham số mới
        )
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, msg):
        self.btn_run.setEnabled(True)
        self.progress.setValue(100)
        self.log(msg, "success")
        QMessageBox.information(self, "Hoàn tất", msg)