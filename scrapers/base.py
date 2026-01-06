from abc import ABC, abstractmethod
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    name = "Base Scraper"
    domain = "example.com"

    @abstractmethod
    def get_images(self, soup: BeautifulSoup, url: str) -> list[str]:
        pass