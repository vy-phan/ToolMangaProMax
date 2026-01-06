try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class DamCoNuongScraper(BaseScraper):
    name = "Damconuong.onl"
    domain = "damconuong.onl"

    def get_images(self, soup, url):
        image_urls = []
        for img in soup.select('#chapter-content img'):
            url = img.get('data-original-src') or img.get('data-src') or img.get('src')
            if url:
                url = url.strip()
                if url.startswith('//'): url = 'https:' + url
                image_urls.append(url)
        return image_urls