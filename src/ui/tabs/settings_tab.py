import sys
import os
import platform
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QGroupBox, QPushButton, QLineEdit, QFormLayout, 
                               QFrame, QMessageBox)
from PySide6.QtCore import Qt, QUrl, QSize
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QColor, QPalette
from datetime import datetime

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # --- PHẦN 1: HEADER ---
        header_layout = QVBoxLayout()
        lbl_title = QLabel("Manga Tool Pro Max")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")
        lbl_title.setAlignment(Qt.AlignCenter)
        
        lbl_subtitle = QLabel("Bộ công cụ hỗ trợ dịch và tải truyện tranh All-in-One")
        lbl_subtitle.setStyleSheet("font-size: 14px; color: #666;")
        lbl_subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        layout.addLayout(header_layout)

        # --- PHẦN 2: THÔNG TIN ỨNG DỤNG ---
        group_info = QGroupBox("THÔNG TIN PHẦN MỀM")
        group_info.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Version
        lbl_version = QLabel("v2.1 (Portable Edition)")
        lbl_version.setStyleSheet("font-weight: bold; color: #2e7d32;")
        form_layout.addRow("Phiên bản:", lbl_version)

        # Author
        lbl_author = QLabel("Vy Phan Rekid")
        lbl_author.setStyleSheet("font-weight: bold;")
        form_layout.addRow("Tác giả:", lbl_author)

        # Github Link (Nút bấm)
        btn_github = QPushButton(" github.com/vy-phan/ToolMangaProMax")
        btn_github.setCursor(Qt.PointingHandCursor)
        btn_github.setStyleSheet("""
            QPushButton { text-align: left; color: #0078d4; border: none; background: transparent; font-weight: bold; }
            QPushButton:hover { text-decoration: underline; color: #005a9e; }
        """)
        btn_github.clicked.connect(self.open_github)
        form_layout.addRow("Mã nguồn:", btn_github)
        
        # System Info
        sys_info = f"{platform.system()} {platform.release()} - Python {sys.version.split()[0]}"
        form_layout.addRow("Hệ thống:", QLabel(sys_info))

        group_info.setLayout(form_layout)
        layout.addWidget(group_info)

        # --- PHẦN 3: MÔI TRƯỜNG CHẠY (PORTABLE PATH) ---
        group_path = QGroupBox("MÔI TRƯỜNG CHẠY (PORTABLE)")
        group_path.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #ccc; border-radius: 5px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        vbox_path = QVBoxLayout()

        lbl_desc_path = QLabel("Vì đây là bản Portable, toàn bộ dữ liệu (plugins, assets , temp , ... ) nằm tại thư mục này:")
        lbl_desc_path.setWordWrap(True)
        lbl_desc_path.setStyleSheet("color: #555; font-style: italic;")
        vbox_path.addWidget(lbl_desc_path)

        hbox_path = QHBoxLayout()
        
        # Lấy đường dẫn thực thi
        # Nếu chạy bằng file .exe (frozen) thì lấy đường dẫn file exe
        # Nếu chạy bằng code python thì lấy đường dẫn hiện tại
        if getattr(sys, 'frozen', False):
            app_path = os.path.dirname(sys.executable)
        else:
            app_path = os.getcwd()

        self.txt_path = QLineEdit(app_path)
        self.txt_path.setReadOnly(True)
        self.txt_path.setStyleSheet("padding: 5px; color: #333; background-color: #f0f0f0; border: 1px solid #ccc; border-radius: 3px;")
        
        btn_open_folder = QPushButton("📂 Mở Thư Mục")
        btn_open_folder.setCursor(Qt.PointingHandCursor)
        btn_open_folder.setFixedHeight(30)
        btn_open_folder.setStyleSheet("""
            QPushButton { background-color: #0078d4; color: white; border-radius: 4px; padding: 0 15px; font-weight: bold; }
            QPushButton:hover { background-color: #106ebe; }
        """)
        btn_open_folder.clicked.connect(lambda: self.open_local_folder(app_path))

        hbox_path.addWidget(self.txt_path)
        hbox_path.addWidget(btn_open_folder)
        vbox_path.addLayout(hbox_path)
        
        group_path.setLayout(vbox_path)
        layout.addWidget(group_path)

        # --- PHẦN 4: HÀNH ĐỘNG KHÁC ---
        layout.addStretch()
        
        # Footer
        current_year = datetime.now().year
        lbl_footer = QLabel(f"© 2025 - {current_year} Vy Phan Rekid. All rights reserved.")
        lbl_footer.setAlignment(Qt.AlignCenter)
        lbl_footer.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(lbl_footer)

        self.setLayout(layout)

    def open_github(self):
        """Mở link GitHub trên trình duyệt"""
        url = QUrl("https://github.com/vy-phan/ToolMangaProMax")
        QDesktopServices.openUrl(url)

    def open_local_folder(self, path):
        """Mở thư mục trên máy tính"""
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục:\n{e}")