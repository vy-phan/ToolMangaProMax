try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class HentaiWorldScraper(BaseScraper):
    name = "Hentaivn.world"
    domain = "hentaivn.world"

    def get_images(self, soup, url):
        return [img['src'].strip() for img in soup.select('div.reading-content div.item-list div.item img') if img.get('src')]