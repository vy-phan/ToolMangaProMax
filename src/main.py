import sys
import os
import ctypes

# Fix import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from ui.main_window import MainWindow

if __name__ == "__main__":
    # 1. Định danh App ID
    myappid = 'tool.manga.pro.max.v1' 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    
    # 2. [QUAN TRỌNG] Xác định đường dẫn gốc
    if getattr(sys, 'frozen', False):
        # Nếu đang chạy file .EXE: Thư mục gốc là nơi chứa file .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Nếu đang chạy Code Python: Thư mục gốc là thư mục dự án
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    assets_dir = os.path.join(base_dir, "assets")
    
    # Debug: In ra để biết nó đang tìm ở đâu (nếu chạy console)
    # print(f"Đang tìm icon tại: {assets_dir}")

    # 3. Nạp Icon
    app_icon = QIcon()
    
    # Danh sách các file icon (Bạn phải đảm bảo folder assets chứa đủ file này)
    icon_files = [
        "logo-16x16.ico",
        "logo-32x32.ico",
        "logo-48x48.ico",
        "logo-64x64.ico",
        "logo-128x128.ico",
        "logo-256x256.ico"
    ]
    
    found_any = False
    for filename in icon_files:
        path = os.path.join(assets_dir, filename)
        if os.path.exists(path):
            app_icon.addFile(path)
            found_any = True
        else:
            # Nếu không tìm thấy, thử fallback về file icon gốc nếu có
            pass
            
    # Nếu không tìm thấy list ảnh trên, thử load file icon.ico hoặc logo.ico chung
    if not found_any:
        fallback_path = os.path.join(assets_dir, "logo-64x64.ico") # Hoặc file nào bạn dùng build
        if os.path.exists(fallback_path):
            app_icon.addFile(fallback_path)

    # Set Icon
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.setWindowIcon(app_icon)
    
    window.show()
    sys.exit(app.exec())