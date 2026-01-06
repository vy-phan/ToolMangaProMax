try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class HentaivngoScraper(BaseScraper):
    name = "Hentaivngo.xyz"
    domain = "hentaivngo.xyz"

    def get_images(self, soup, url):
        # Ưu tiên selector 1
        imgs = [img['src'].strip() for img in soup.select('div.reading-detail div.page-chapter > img') if img.get('src')]
        if imgs: return imgs
        
        # Fallback selector
        for container in soup.find_all('div', class_='item-photo'):
            img = container.find('img')
            if img and img.get('src'): imgs.append(img['src'].strip())
        return imgs