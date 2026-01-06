import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QTextEdit, QGroupBox, 
                               QGridLayout, QSpinBox, QMessageBox, QApplication, 
                               QStyle, QComboBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class UrlGeneratorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.formatted_result = ""
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # Style đồng bộ (Sạch sẽ, không nền đen)
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
        # 1. CẤU HÌNH INPUT
        # ======================================================================
        group_input = QGroupBox(" 1. CẤU HÌNH LINK MẪU ")
        group_input.setStyleSheet(groupbox_style)
        input_layout = QGridLayout()
        input_layout.setVerticalSpacing(15)

        # URL Input
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("Ví dụ: https://api.site.com/images/uuid/index (Chữ 'index' sẽ được thay thế)")
        self.input_url.setClearButtonEnabled(True)
        self.input_url.setMinimumHeight(35)
        
        # Cấu hình số bắt đầu / kết thúc
        self.spin_start = QSpinBox()
        self.spin_start.setRange(0, 99999)
        self.spin_start.setValue(0)
        self.spin_start.setPrefix("Từ số: ")
        self.spin_start.setMinimumHeight(30)

        self.spin_end = QSpinBox()
        self.spin_end.setRange(0, 99999)
        self.spin_end.setValue(20)
        self.spin_end.setPrefix("Đến số: ")
        self.spin_end.setMinimumHeight(30)

        # --- THAY ĐỔI Ở ĐÂY: DÙNG COMBOBOX THAY VÌ SPINBOX ---
        self.combo_padding = QComboBox()
        self.combo_padding.addItems([
            "Loại 1 (1, 2, ... 10)",      # Index 0 - Mặc định
            "Loại 01 (01, 02, ... 10)",   # Index 1
            "Loại 001 (001, 002, ... 010)"# Index 2
        ])
        self.combo_padding.setMinimumHeight(30)
        self.combo_padding.setToolTip("Chọn định dạng số chèn vào link")

        # Layout
        input_layout.addWidget(QLabel("🔗 Link mẫu:"), 0, 0)
        input_layout.addWidget(self.input_url, 0, 1, 1, 3) # Chiếm hết dòng ngang
        
        input_layout.addWidget(QLabel("🔢 Quy luật:"), 1, 0)
        input_layout.addWidget(self.spin_start, 1, 1)
        input_layout.addWidget(self.spin_end, 1, 2)
        
        input_layout.addWidget(QLabel("🎨 Định dạng:"), 2, 0)
        input_layout.addWidget(self.combo_padding, 2, 1, 1, 2) # Chiếm 2 ô

        group_input.setLayout(input_layout)
        main_layout.addWidget(group_input)

        # ======================================================================
        # 2. OUTPUT & ACTION
        # ======================================================================
        group_output = QGroupBox(" 2. KẾT QUẢ TẠO RA ")
        group_output.setStyleSheet(groupbox_style)
        output_layout = QVBoxLayout()

        self.txt_result = QTextEdit()
        self.txt_result.setReadOnly(True)
        self.txt_result.setPlaceholderText("Danh sách link sẽ hiện ở đây...")
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9; color: #333;")

        # Button Layout
        btn_layout = QHBoxLayout()
        
        self.btn_gen = QPushButton(" TẠO DANH SÁCH")
        self.btn_gen.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_gen.setCursor(Qt.PointingHandCursor)
        self.btn_gen.setMinimumHeight(40)
        self.btn_gen.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; font-weight: bold; border-radius: 4px; } 
            QPushButton:hover { background-color: #0063b1; }
        """)
        self.btn_gen.clicked.connect(self.generate_links)

        self.btn_copy = QPushButton(" COPY CLIPBOARD")
        self.btn_copy.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.setMinimumHeight(40)
        self.btn_copy.setEnabled(False)
        self.btn_copy.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #219150; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.btn_copy.clicked.connect(self.copy_to_clipboard)

        btn_layout.addWidget(self.btn_gen)
        btn_layout.addWidget(self.btn_copy)

        output_layout.addWidget(self.txt_result)
        output_layout.addLayout(btn_layout)
        
        group_output.setLayout(output_layout)
        main_layout.addWidget(group_output)
        
        self.setLayout(main_layout)

    # --- LOGIC ---
    def generate_links(self):
        template = self.input_url.text().strip()
        start = self.spin_start.value()
        end = self.spin_end.value()
        
        # Lấy lựa chọn từ ComboBox
        padding_choice = self.combo_padding.currentIndex() # 0: None, 1: 01, 2: 001

        if not template:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập Link mẫu!")
            return

        if "index" not in template:
            QMessageBox.warning(self, "Lỗi cú pháp", "Link mẫu PHẢI chứa chữ 'index' để tool biết vị trí cần thay số.\n\nVí dụ: https://site.com/image/index.jpg")
            return

        if start > end:
            QMessageBox.warning(self, "Lỗi logic", "Số bắt đầu không được lớn hơn số kết thúc!")
            return

        lines = []
        count = 0
        
        # Loop tạo link
        for i in range(start, end + 1):
            # Xử lý format số dựa trên lựa chọn
            if padding_choice == 0:   # Loại 1 (1, 2...)
                num_str = f"{i}"
            elif padding_choice == 1: # Loại 01 (01, 02...)
                num_str = f"{i:02d}"
            else:                     # Loại 001 (001, 002...)
                num_str = f"{i:03d}"
            
            # Thay thế chữ index bằng số
            new_url = template.replace("index", num_str)
            
            # Format chuẩn output: 0:https://...
            line = f"{count}:{new_url}"
            lines.append(line)
            count += 1

        self.formatted_result = "\n".join(lines)
        self.txt_result.setPlainText(self.formatted_result)
        
        self.btn_copy.setEnabled(True)
        self.btn_copy.setText(f" COPY {len(lines)} DÒNG")
        
        # Scroll xuống cuối
        self.txt_result.verticalScrollBar().setValue(self.txt_result.verticalScrollBar().maximum())

    def copy_to_clipboard(self):
        if not self.formatted_result: return
        clipboard = QApplication.clipboard()
        clipboard.setText(self.formatted_result)
        QMessageBox.information(self, "Thành công", "Đã copy toàn bộ vào Clipboard!")