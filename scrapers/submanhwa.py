try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class SubManhwaScraper(BaseScraper):
    name = "SubManhwa.com"
    domain = "submanhwa.com"

    def get_images(self, soup, url):
        image_urls = []
        
        # Dựa trên ảnh bạn cung cấp:
        # Ảnh nằm trong <div id="all"> và thẻ <img class="img-responsive">
        images = soup.select('div#all img')
        
        # Selector dự phòng (Fallback) nếu ID thay đổi
        if not images:
            images = soup.select('.col-sm-8 img.img-responsive')

        for img in images:
            # Ưu tiên lấy link từ 'data-src' trước, nếu không có mới lấy 'src'
            img_link = img.get('data-src') or img.get('src')
            
            if img_link:
                img_link = img_link.strip()
                
                # Xử lý link tương đối (bắt đầu bằng //)
                if img_link.startswith('//'):
                    img_link = 'https:' + img_link
                
                # Lọc rác: Chỉ lấy link có chứa domain của web (để tránh icon, banner quảng cáo)
                # Link trong ảnh là: https://w1.submanhwa.com/...
                if 'submanhwa' in img_link:
                    image_urls.append(img_link)
                    
        return image_urls