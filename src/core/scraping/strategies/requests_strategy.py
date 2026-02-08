"""
Requests Strategy

For static HTML sites that don't require JavaScript.
Uses requests + BeautifulSoup.
"""

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .base import BaseStrategy, StrategyResult

logger = logging.getLogger(__name__)


class RequestsStrategy(BaseStrategy):
    """Scraping strategy using requests + BeautifulSoup."""

    name = "requests"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
        })

    async def scrape(
        self,
        url: str,
        selectors: dict,
        config: dict = None
    ) -> StrategyResult:
        """Scrape using requests + BeautifulSoup."""
        config = config or {}

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            return StrategyResult(
                success=True,
                title=self._extract_text(soup, selectors.get('title', {})),
                description=self._extract_html(soup, selectors.get('description', {})),
                price=self._extract_text(soup, selectors.get('price', {})),
                images=self._extract_images(soup, selectors.get('images', {})),
                sku_on_page=self._extract_text(soup, selectors.get('sku', {})),
                availability=self._extract_text(soup, selectors.get('availability', {})),
                source_url=url,
                strategy_name=self.name,
                raw_html=response.text[:5000] if config.get('debug') else None
            )

        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return StrategyResult(
                success=False,
                source_url=url,
                strategy_name=self.name,
                error=str(e)
            )

    def _extract_text(self, soup: BeautifulSoup, selector_config: dict) -> Optional[str]:
        """Extract text from element."""
        selector = selector_config.get('selector')
        if not selector:
            return None

        # Try primary selector
        element = soup.select_one(selector)

        # Try fallbacks
        if not element:
            for fallback in selector_config.get('fallback_selectors', []):
                element = soup.select_one(fallback)
                if element:
                    break

        if element:
            return element.get_text(strip=True)
        return None

    def _extract_html(self, soup: BeautifulSoup, selector_config: dict) -> Optional[str]:
        """Extract HTML content."""
        selector = selector_config.get('selector')
        if not selector:
            return None

        element = soup.select_one(selector)

        # Try fallbacks
        if not element:
            for fallback in selector_config.get('fallback_selectors', []):
                element = soup.select_one(fallback)
                if element:
                    break

        if element:
            extract_as = selector_config.get('extract_as', 'text')
            if extract_as == 'html':
                return str(element)
            return element.get_text(strip=True)
        return None

    def _extract_images(self, soup: BeautifulSoup, selector_config: dict) -> list[str]:
        """Extract image URLs."""
        container_selector = selector_config.get('container')
        item_selector = selector_config.get('items', 'img')
        src_attr = selector_config.get('src_attribute', 'src')
        data_attrs = selector_config.get('data_attributes', [])

        images = []

        # Find container
        container = soup
        if container_selector:
            container = soup.select_one(container_selector)
            if not container:
                # Try fallbacks
                for fallback in selector_config.get('fallback_selectors', []):
                    container = soup.select_one(fallback)
                    if container:
                        break

        if not container:
            return []

        # Find image elements
        elements = container.select(item_selector)

        for elem in elements:
            # Try standard src
            src = elem.get(src_attr)

            # Try data attributes
            if not src:
                for data_attr in data_attrs:
                    src = elem.get(data_attr)
                    if src:
                        break

            # Try srcset (get first image)
            if not src:
                srcset = elem.get('srcset') or elem.get(selector_config.get('srcset_attribute', 'srcset'))
                if srcset:
                    # Parse srcset: "image1.jpg 1x, image2.jpg 2x"
                    first_src = srcset.split(',')[0].split()[0]
                    src = first_src

            if src:
                # Clean URL
                src = src.strip()
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    # Need base URL - skip for now
                    pass
                if src.startswith('http'):
                    images.append(src)

        return images

    async def close(self):
        """Close session."""
        self.session.close()
