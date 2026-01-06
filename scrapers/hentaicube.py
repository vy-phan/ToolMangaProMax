try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class HentaiCubeScraper(BaseScraper):
    name = "Hentaicube.xyz"
    domain = "hentaicube.xyz"

    def get_images(self, soup, url):
        return [img['src'].strip() for img in soup.select('p.doc-truyen img') if img.get('src')]