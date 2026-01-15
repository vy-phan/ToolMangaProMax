from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from core.loader import load_scrapers

# Import các Tab con
from ui.tabs.downloader_tab import DownloaderTab
from ui.tabs.tools_tab import ToolsTab
from ui.tabs.get_links_tab import GetLinksTab  
from ui.tabs.optimizer_tab import OptimizerTab
from ui.tabs.url_generator_tab import UrlGeneratorTab
from ui.tabs.gif_maker_tab import GifMakerTab
from ui.tabs.merger_tab import MergerTab
from ui.tabs.translator_tab import TranslatorTab
from ui.tabs.settings_tab import SettingsTab 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Manga Tool Pro Max v2.0 - Vy Phan Rekid")
        self.resize(1150, 850)
        
        # 1. Load dữ liệu lõi (Plugins)
        try:
            self.scrapers = load_scrapers()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Khởi Động", f"Không thể tải Plugins: {e}")
            self.scrapers = {}

        # 2. Setup Giao diện chính
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.setup_tabs()
        
        self.statusBar().showMessage(f"Hệ thống đã tải {len(self.scrapers)} nguồn truyện.")

    def setup_tabs(self):
        # Khởi tạo các Tab
        self.downloader_tab = DownloaderTab(self.scrapers)
        self.get_links_tab = GetLinksTab(self.scrapers) 
        self.optimizer_tab = OptimizerTab()
        self.translator_tab = TranslatorTab()  
        self.url_gen_tab = UrlGeneratorTab()
        self.tools_tab = ToolsTab()
        self.gif_maker_tab = GifMakerTab()
        self.merger_tab = MergerTab()
        self.settings_tab = SettingsTab()
        
        # Thêm vào Widget
        self.tabs.addTab(self.downloader_tab, "TẢI TRUYỆN")
        self.tabs.addTab(self.get_links_tab, "LẤY LINK TRUYỆN") 
        self.tabs.addTab(self.url_gen_tab, "TẠO LINK HÀNG LOẠT")
        self.tabs.addTab(self.translator_tab, "DỊCH TRUYỆN ")
        self.tabs.addTab(self.optimizer_tab, "TỐI ƯU ẢNH ")
        self.tabs.addTab(self.gif_maker_tab, "TẠO GIF")
        self.tabs.addTab(self.merger_tab, "GHÉP ẢNH DÀI")
        self.tabs.addTab(self.tools_tab, "TIỆN ÍCH KHÁC")
        self.tabs.addTab(self.settings_tab, "CÀI ĐẶT")