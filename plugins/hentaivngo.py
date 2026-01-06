try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class HentaiVNScraper(BaseScraper):
    name = "Hentaivngo.xyz"
    domain = "hentaivngo.xyz"

    def get_images(self, soup, url):
        # Logic cào từ tool cũ của bạn
        images = []
        # Selector 1
        containers = soup.select('div.reading-detail div.page-chapter > img')
        if containers:
            return [img['src'].strip() for img in containers if img.get('src')]
        
        # Selector 2 (Fallback)
        containers = soup.find_all('div', class_='item-photo')
        for c in containers:
            img = c.find('img')
            if img and img.get('src'):
                images.append(img['src'].strip())
        return images