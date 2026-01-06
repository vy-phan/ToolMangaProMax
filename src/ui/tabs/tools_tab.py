from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ToolsTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        
        label = QLabel("Đang phát triển các công cụ bổ sung...\n(Ví dụ: Convert hàng loạt, Đổi tên file, Ghép PDF thủ công)")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px;")
        
        layout.addWidget(label)
        self.setLayout(layout)