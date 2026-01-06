import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QThread, Signal

class ScanWorker(QThread):
    """
    Luồng xử lý việc quét ảnh từ URL để không làm đơ giao diện.
    """
    finished = Signal(list)
    error = Signal(str)
    
    def __init__(self, scraper, url):
        super().__init__()
        self.scraper = scraper
        self.url = url
        
    def run(self):
        try:
            # Fake User-Agent để tránh bị chặn
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            # Request
            resp = requests.get(self.url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Gọi hàm get_images từ Plugin
            imgs = self.scraper.get_images(soup, self.url)
            self.finished.emit(imgs)
            
        except Exception as e:
            self.error.emit(str(e))