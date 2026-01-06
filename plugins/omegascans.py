try:
    from .base import BaseScraper
except ImportError:
    try:
        import base
        BaseScraper = base.BaseScraper
    except ImportError:
        from src.plugins.base import BaseScraper

class OmegaScansScraper(BaseScraper):
    name = "OmegaScans.org"
    domain = "omegascans.org"

    def get_images(self, soup, url):
        image_urls = []
        # Selector chính
        images = soup.select('div.flex.flex-col.justify-center.items-center img')
        
        # Selector dự phòng
        if not images:
            images = soup.select('#content .container img')

        for img in images:
            url = img.get('src') or img.get('data-src')
            if url:
                url = url.strip()
                # Lọc rác (giữ logic cũ của bạn)
                if 'omegascans.org' in url or 'imgur' in url: 
                     if url.startswith('//'): url = 'https:' + url
                     image_urls.append(url)
        return image_urls