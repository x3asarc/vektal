"""
Playwright Strategy

For JavaScript-heavy sites that require browser rendering.
Handles dynamic content, lazy loading, and interactive elements.
"""

import logging
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from .base import BaseStrategy, StrategyResult

logger = logging.getLogger(__name__)

# Lazy import to avoid requiring playwright if not used
_playwright_available = None


def _check_playwright():
    """Check if playwright is available."""
    global _playwright_available
    if _playwright_available is None:
        try:
            from playwright.async_api import async_playwright
            _playwright_available = True
        except ImportError:
            logger.warning(
                "playwright not installed. "
                "Install with: pip install playwright && playwright install chromium"
            )
            _playwright_available = False
    return _playwright_available


class PlaywrightStrategy(BaseStrategy):
    """Scraping strategy using Playwright for JavaScript sites."""

    name = "playwright"

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30000
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._browser = None
        self._playwright = None

    @asynccontextmanager
    async def _get_browser(self):
        """Get or create browser instance with cleanup."""
        if not _check_playwright():
            raise RuntimeError("Playwright not available")

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            try:
                yield browser
            finally:
                await browser.close()

    async def scrape(
        self,
        url: str,
        selectors: dict,
        config: dict = None
    ) -> StrategyResult:
        """Scrape using Playwright browser automation."""
        if not _check_playwright():
            return StrategyResult(
                success=False,
                source_url=url,
                strategy_name=self.name,
                error="Playwright not installed"
            )

        config = config or {}
        timing = config.get('timing', {})
        page_load_wait = timing.get('page_load_wait_ms', 3000)
        dynamic_wait = timing.get('dynamic_content_wait_ms', 1500)
        selector_timeout = timing.get('selector_timeout_ms', 5000)

        try:
            async with self._get_browser() as browser:
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    locale=config.get('browser', {}).get('locale', 'de-AT'),
                    timezone_id=config.get('browser', {}).get('timezone', 'Europe/Vienna')
                )

                page = await context.new_page()

                try:
                    # Navigate to page
                    await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout_ms)

                    # Wait for page to load
                    await asyncio.sleep(page_load_wait / 1000)

                    # Execute pre-scrape actions if defined
                    quirks = config.get('quirks', {})
                    for action in quirks.get('pre_scrape_actions', []):
                        await self._execute_action(page, action)

                    # Handle lazy loading - scroll page
                    if quirks.get('lazy_loads_images', False):
                        await self._scroll_page(page)
                        await asyncio.sleep(dynamic_wait / 1000)

                    # Extract data
                    title = await self._extract_text(page, selectors.get('title', {}), selector_timeout)
                    description = await self._extract_html(page, selectors.get('description', {}))
                    price = await self._extract_text(page, selectors.get('price', {}), selector_timeout)
                    images = await self._extract_images(page, selectors.get('images', {}))
                    sku = await self._extract_text(page, selectors.get('sku', {}), selector_timeout)
                    availability = await self._extract_text(page, selectors.get('availability', {}), selector_timeout)

                    return StrategyResult(
                        success=True,
                        title=title,
                        description=description,
                        price=price,
                        images=images,
                        sku_on_page=sku,
                        availability=availability,
                        source_url=url,
                        strategy_name=self.name
                    )

                finally:
                    await page.close()
                    await context.close()

        except Exception as e:
            logger.error(f"Playwright scrape failed for {url}: {e}")
            return StrategyResult(
                success=False,
                source_url=url,
                strategy_name=self.name,
                error=str(e)
            )

    async def _extract_text(self, page, selector_config: dict, timeout: int) -> Optional[str]:
        """Extract text from element."""
        selector = selector_config.get('selector')
        if not selector:
            return None

        selectors_to_try = [selector] + selector_config.get('fallback_selectors', [])

        for sel in selectors_to_try:
            try:
                element = await page.wait_for_selector(sel, timeout=timeout, state='visible')
                if element:
                    text = await element.inner_text()
                    return text.strip()
            except Exception:
                continue

        return None

    async def _extract_html(self, page, selector_config: dict) -> Optional[str]:
        """Extract HTML content."""
        selector = selector_config.get('selector')
        if not selector:
            return None

        selectors_to_try = [selector] + selector_config.get('fallback_selectors', [])

        for sel in selectors_to_try:
            try:
                element = await page.query_selector(sel)
                if element:
                    if selector_config.get('extract_as', 'text') == 'html':
                        return await element.inner_html()
                    return await element.inner_text()
            except Exception:
                continue

        return None

    async def _extract_images(self, page, selector_config: dict) -> list[str]:
        """Extract image URLs using JavaScript evaluation."""
        container = selector_config.get('container', 'body')
        items = selector_config.get('items', 'img')
        src_attr = selector_config.get('src_attribute', 'src')
        data_attrs = selector_config.get('data_attributes', ['data-src', 'data-lazy-src'])

        try:
            images = await page.evaluate(f"""
                () => {{
                    const container = document.querySelector('{container}') || document;
                    const imgs = container.querySelectorAll('{items}');
                    const urls = [];

                    imgs.forEach(img => {{
                        let src = img.getAttribute('{src_attr}');

                        if (!src) {{
                            const dataAttrs = {data_attrs};
                            for (const attr of dataAttrs) {{
                                src = img.getAttribute(attr);
                                if (src) break;
                            }}
                        }}

                        if (!src && img.srcset) {{
                            src = img.srcset.split(',')[0].split(' ')[0];
                        }}

                        if (src) {{
                            if (src.startsWith('//')) src = 'https:' + src;
                            if (src.startsWith('http')) urls.push(src);
                        }}
                    }});

                    return urls;
                }}
            """)
            return images

        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")
            return []

    async def _scroll_page(self, page):
        """Scroll page to trigger lazy loading."""
        try:
            await page.evaluate("""
                async () => {
                    const delay = ms => new Promise(r => setTimeout(r, ms));
                    const height = document.body.scrollHeight;
                    for (let i = 0; i < height; i += 500) {
                        window.scrollTo(0, i);
                        await delay(100);
                    }
                    window.scrollTo(0, 0);
                }
            """)
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")

    async def _execute_action(self, page, action: dict):
        """Execute pre-scrape action."""
        action_type = action.get('action')
        selector = action.get('selector')
        wait_after = action.get('wait_after_ms', 1000)

        try:
            if action_type == 'click' and selector:
                element = await page.query_selector(selector)
                if element:
                    await element.click()

            elif action_type == 'scroll':
                amount = action.get('amount_px', 500)
                await page.evaluate(f'window.scrollBy(0, {amount})')

            elif action_type == 'wait':
                wait_duration = action.get('duration_ms', 1000)
                await asyncio.sleep(wait_duration / 1000)

            await asyncio.sleep(wait_after / 1000)

        except Exception as e:
            logger.warning(f"Action {action_type} failed: {e}")

    async def close(self):
        """Clean up resources."""
        pass  # Resources cleaned up in context manager
