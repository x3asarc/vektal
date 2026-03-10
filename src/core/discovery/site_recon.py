"""
Site Reconnaissance Module

Visits vendor websites and automatically discovers selectors, URL patterns,
and SKU formats from actual page structure.

Purpose: Closes Gap 1 from VERIFICATION.md - provides mechanism to LEARN
site structure from actual pages instead of relying on templates.
"""

import logging
import re
import asyncio
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from src.core.config.generator import SiteReconData

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


@dataclass
class SelectorScore:
    """Score for a candidate selector."""
    selector: str
    score: float
    found_count: int
    has_content: bool
    content_type_match: bool


class SiteReconnaissance:
    """
    Visits vendor sites and discovers selectors, patterns, and structure.

    Usage:
        recon = SiteReconnaissance()
        data = await recon.discover("https://example.com", "Example Vendor")
    """

    # Common selectors to try (from VendorConfigGenerator)
    DEFAULT_SELECTOR_ATTEMPTS = {
        'title': [
            'h1.product-title',
            'h1.product__title',
            '[data-product-title]',
            '.product-single__title',
            'h1[itemprop="name"]',
            '.product-title',
            'h1'
        ],
        'price': [
            '.price__current',
            '.product-price',
            '[data-price]',
            '.price',
            '.product__price',
            '[itemprop="price"]',
            'span.money'
        ],
        'images': [
            '.product-gallery img',
            '.product__media-gallery img',
            '.product-images img',
            '[data-product-image]',
            '.product-single__photo img',
            '[itemprop="image"]',
            '.product-photo img'
        ],
        'description': [
            '.product-description',
            '.product__description',
            '[data-description]',
            '.description',
            '.rte',
            '[itemprop="description"]',
            '.product-details'
        ],
        'sku': [
            '[data-sku]',
            '.product-sku',
            '.sku',
            '[itemprop="sku"]',
            '.variant-sku',
            'span.sku'
        ]
    }

    # Patterns for collection/category pages
    COLLECTION_PATTERNS = [
        r'/collections?/',
        r'/categories?/',
        r'/products?/',
        r'/catalog',
        r'/shop',
        r'/alle-produkte'  # German
    ]

    # Common SKU patterns to try
    SKU_REGEX_PATTERNS = [
        (r'^[A-Z]\d{4}[A-Z]?$', 'ITD Collection format (R0530, R1234L)'),
        (r'^[A-Z]{2,3}\d{3,6}$', 'Brand prefix + numbers (ITD123456)'),
        (r'^[A-Z0-9]{6,12}$', 'Alphanumeric 6-12 chars'),
        (r'^\d{5,10}$', 'Pure numeric'),
        (r'^[A-Z]+-\d+$', 'Letter-dash-number (R-12345)'),
    ]

    def __init__(self, timeout_ms: int = 30000, headless: bool = True):
        """
        Initialize site reconnaissance.

        Args:
            timeout_ms: Page load timeout in milliseconds
            headless: Run browser in headless mode
        """
        self.timeout_ms = timeout_ms
        self.headless = headless

    async def discover(
        self,
        domain_url: str,
        vendor_name: Optional[str] = None,
        max_sample_products: int = 5
    ) -> SiteReconData:
        """
        Discover vendor site structure from actual pages.

        Args:
            domain_url: Vendor domain URL (e.g., "https://example.com")
            vendor_name: Optional vendor name (extracted from domain if None)
            max_sample_products: Number of sample products to analyze

        Returns:
            SiteReconData populated with discovered patterns
        """
        if not _check_playwright():
            raise RuntimeError("Playwright not available")

        # Normalize domain URL
        if not domain_url.startswith('http'):
            domain_url = f"https://{domain_url}"

        parsed = urlparse(domain_url)
        domain = parsed.netloc or parsed.path

        # Extract vendor name from domain if not provided
        if not vendor_name:
            vendor_name = self._extract_vendor_name(domain)

        logger.info(f"Starting site reconnaissance for {vendor_name} ({domain_url})")

        warnings = []
        discovered_selectors = {}
        collection_pages = []
        sample_products = []
        url_patterns = {}
        sku_patterns = []
        requires_javascript = False
        has_lazy_loading = False

        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )

                try:
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        locale='de-AT',
                        timezone_id='Europe/Vienna'
                    )

                    page = await context.new_page()

                    # Visit homepage
                    logger.info(f"Visiting homepage: {domain_url}")
                    await page.goto(domain_url, wait_until='domcontentloaded', timeout=self.timeout_ms)
                    await asyncio.sleep(2)  # Wait for JS to execute

                    # Detect if JavaScript is required
                    requires_javascript = await self._detect_javascript_requirement(page)

                    # Find collection pages
                    collection_pages = await self._find_collection_pages(page, domain_url)
                    logger.info(f"Found {len(collection_pages)} collection pages")

                    # Find product links
                    product_links = await self._find_product_links(
                        page, domain_url, collection_pages[:3], max_sample_products
                    )
                    logger.info(f"Found {len(product_links)} product links")

                    if not product_links:
                        warnings.append("No product links found - may need manual configuration")
                    else:
                        # Analyze URL patterns
                        url_patterns = self._analyze_url_patterns(product_links, domain)

                        # Visit sample products and discover selectors
                        for idx, product_url in enumerate(product_links[:max_sample_products]):
                            logger.info(f"Analyzing product {idx + 1}/{len(product_links[:max_sample_products])}: {product_url}")

                            try:
                                await page.goto(product_url, wait_until='domcontentloaded', timeout=self.timeout_ms)
                                await asyncio.sleep(1.5)

                                # Detect lazy loading on first product
                                if idx == 0:
                                    has_lazy_loading = await self._detect_lazy_loading(page)

                                # Discover selectors for this product
                                product_selectors = await self._discover_selectors(page)

                                # Extract sample data
                                sample_data = {
                                    'url': product_url,
                                    'title': product_selectors.get('title_content'),
                                    'price': product_selectors.get('price_content'),
                                    'sku': product_selectors.get('sku_content')
                                }
                                sample_products.append(sample_data)

                                # Merge selectors (take best across products)
                                for field, selector in product_selectors.items():
                                    if field.endswith('_content'):
                                        continue
                                    if field not in discovered_selectors:
                                        discovered_selectors[field] = selector

                            except Exception as e:
                                logger.warning(f"Failed to analyze product {product_url}: {e}")
                                warnings.append(f"Product analysis failed: {str(e)[:100]}")

                        # Validate selectors across all samples
                        if len(sample_products) > 1:
                            validated_selectors = await self._validate_selectors_on_samples(
                                page, product_links[:max_sample_products], discovered_selectors
                            )
                            discovered_selectors.update(validated_selectors)

                        # Infer SKU patterns from samples
                        sku_patterns = self._infer_sku_patterns(sample_products)

                    await context.close()

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"Site reconnaissance failed: {e}")
            warnings.append(f"Discovery error: {str(e)}")

        # Build SiteReconData
        return SiteReconData(
            domain=domain,
            vendor_name=vendor_name,
            detected_niche="other",  # Niche detection done elsewhere
            sku_patterns=sku_patterns,
            url_patterns=url_patterns,
            selectors=discovered_selectors,
            requires_javascript=requires_javascript,
            has_lazy_loading=has_lazy_loading,
            has_collection_pages=collection_pages,
            sample_products=sample_products
        )

    async def _discover_selectors(self, page) -> Dict[str, str]:
        """
        Discover selectors for a product page.

        Returns dict with selector keys and their best candidates.
        """
        discovered = {}

        for field, candidates in self.DEFAULT_SELECTOR_ATTEMPTS.items():
            best_selector = None
            best_score = 0.0

            for selector in candidates:
                score = await self._score_selector(page, selector, field)

                if score.score > best_score:
                    best_score = score.score
                    best_selector = selector

            if best_selector and best_score > 0.5:
                discovered[field] = best_selector
                # Also store content for pattern analysis
                discovered[f"{field}_content"] = await self._extract_content(page, best_selector, field)

        return discovered

    async def _score_selector(
        self,
        page,
        selector: str,
        expected_type: str
    ) -> SelectorScore:
        """
        Score a selector based on element existence and content quality.

        Score criteria:
        - Element exists: +1.0
        - Single element (for unique fields): +0.5 / Multiple: -0.5
        - Has non-empty content: +0.5
        - Content matches expected type: +0.5
        """
        try:
            elements = await page.query_selector_all(selector)
            element_count = len(elements)

            if element_count == 0:
                return SelectorScore(selector, 0.0, 0, False, False)

            score = 1.0  # Element exists
            has_content = False
            type_match = False

            # Get content from first element
            element = elements[0]
            content = None

            if expected_type == 'images':
                content = await element.get_attribute('src')
            else:
                content = await element.inner_text()
                content = content.strip() if content else ""

            has_content = bool(content)

            # Check if content matches expected type
            if content:
                type_match = self._validate_content_type(content, expected_type)

            # Scoring adjustments
            if expected_type != 'images':
                # For unique fields, prefer single element
                if element_count == 1:
                    score += 0.5
                else:
                    score -= 0.5

            if has_content:
                score += 0.5

            if type_match:
                score += 0.5

            return SelectorScore(selector, score, element_count, has_content, type_match)

        except Exception as e:
            logger.debug(f"Selector scoring failed for {selector}: {e}")
            return SelectorScore(selector, 0.0, 0, False, False)

    def _validate_content_type(self, content: str, expected_type: str) -> bool:
        """Check if content matches expected type."""
        if expected_type == 'price':
            # Look for currency symbols or numbers
            return bool(re.search(r'[\d.,]+|€|\$|EUR|USD', content))
        elif expected_type == 'images':
            # Check if it's a URL
            return content.startswith('http') or content.startswith('//')
        elif expected_type == 'title':
            # Title should have reasonable length
            return 5 <= len(content) <= 200
        elif expected_type == 'description':
            # Description should be longer
            return len(content) >= 10
        elif expected_type == 'sku':
            # SKU should be short alphanumeric
            return bool(re.match(r'^[A-Z0-9\-]{3,20}$', content, re.IGNORECASE))

        return True

    async def _extract_content(self, page, selector: str, field_type: str) -> Optional[str]:
        """Extract content from selector for pattern analysis."""
        try:
            if field_type == 'images':
                element = await page.query_selector(selector)
                if element:
                    return await element.get_attribute('src')
            else:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    return text.strip() if text else None
        except Exception:
            pass
        return None

    async def _validate_selectors_on_samples(
        self,
        page,
        product_urls: List[str],
        selectors: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Validate discovered selectors across multiple product pages.

        Returns updated selectors with only reliable ones (>80% success rate).
        """
        validated = {}
        success_counts = {field: 0 for field in selectors.keys() if not field.endswith('_content')}

        for url in product_urls:
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=self.timeout_ms)
                await asyncio.sleep(0.5)

                for field, selector in selectors.items():
                    if field.endswith('_content'):
                        continue

                    try:
                        element = await page.query_selector(selector)
                        if element:
                            success_counts[field] += 1
                    except Exception:
                        pass

            except Exception as e:
                logger.debug(f"Validation failed for {url}: {e}")

        # Keep selectors with >80% success rate
        total_samples = len(product_urls)
        threshold = 0.8

        for field, count in success_counts.items():
            success_rate = count / total_samples if total_samples > 0 else 0
            if success_rate >= threshold:
                validated[field] = selectors[field]
            else:
                logger.warning(
                    f"Selector for {field} has low success rate: "
                    f"{success_rate:.1%} ({count}/{total_samples})"
                )

        return validated

    async def _detect_javascript_requirement(self, page) -> bool:
        """
        Detect if site requires JavaScript for content rendering.

        Compare initial HTML with rendered HTML after JS execution.
        """
        try:
            # Get initial HTML
            initial_html = await page.content()

            # Wait for potential JS execution
            await asyncio.sleep(2)

            # Get rendered HTML
            rendered_html = await page.content()

            # Check for significant differences (simple heuristic)
            initial_length = len(initial_html)
            rendered_length = len(rendered_html)

            # If rendered content is >20% larger, JS is likely required
            if rendered_length > initial_length * 1.2:
                return True

            # Check for common JS framework indicators
            js_indicators = [
                'data-react',
                'ng-app',
                'v-app',
                '__NEXT_DATA__',
                'nuxt'
            ]

            for indicator in js_indicators:
                if indicator in rendered_html:
                    return True

            return False

        except Exception as e:
            logger.debug(f"JS detection failed: {e}")
            return True  # Assume JS required on error

    async def _detect_lazy_loading(self, page) -> bool:
        """Detect if site uses lazy loading for images."""
        try:
            content = await page.content()

            # Check for lazy loading indicators
            lazy_indicators = [
                'data-src',
                'data-lazy-src',
                'loading="lazy"',
                'IntersectionObserver',
                'lazyload'
            ]

            for indicator in lazy_indicators:
                if indicator in content:
                    return True

            return False

        except Exception:
            return False

    async def _find_collection_pages(self, page, domain_url: str) -> List[str]:
        """
        Find collection/category pages on the site.

        Returns list of collection page URLs.
        """
        collection_pages = []

        try:
            # Get all links from page
            links = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href);
                }
            """)

            # Filter for collection patterns
            for link in links:
                for pattern in self.COLLECTION_PATTERNS:
                    if re.search(pattern, link, re.IGNORECASE):
                        # Normalize URL
                        full_url = urljoin(domain_url, link)
                        if full_url not in collection_pages:
                            collection_pages.append(full_url)
                        break

        except Exception as e:
            logger.warning(f"Collection page discovery failed: {e}")

        return collection_pages[:10]  # Limit to 10

    async def _find_product_links(
        self,
        page,
        domain_url: str,
        collection_pages: List[str],
        max_products: int
    ) -> List[str]:
        """
        Find product page links from collection pages.

        Returns list of product URLs.
        """
        product_links = []

        # Common product URL patterns
        product_patterns = [
            r'/products?/[^/\s]+',
            r'/p/[^/\s]+',
            r'/item/[^/\s]+',
            r'/produkt/[^/\s]+'  # German
        ]

        # Try homepage first
        try:
            await page.goto(domain_url, wait_until='domcontentloaded', timeout=self.timeout_ms)
            await asyncio.sleep(1)

            links = await page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href);
                }
            """)

            for link in links:
                for pattern in product_patterns:
                    if re.search(pattern, link, re.IGNORECASE):
                        if link not in product_links:
                            product_links.append(link)
                        if len(product_links) >= max_products:
                            return product_links

        except Exception as e:
            logger.warning(f"Product link discovery on homepage failed: {e}")

        # Try collection pages
        for collection_url in collection_pages:
            if len(product_links) >= max_products:
                break

            try:
                await page.goto(collection_url, wait_until='domcontentloaded', timeout=self.timeout_ms)
                await asyncio.sleep(1)

                links = await page.evaluate("""
                    () => {
                        return Array.from(document.querySelectorAll('a'))
                            .map(a => a.href)
                            .filter(href => href);
                    }
                """)

                for link in links:
                    for pattern in product_patterns:
                        if re.search(pattern, link, re.IGNORECASE):
                            if link not in product_links:
                                product_links.append(link)
                            if len(product_links) >= max_products:
                                return product_links

            except Exception as e:
                logger.warning(f"Product link discovery on {collection_url} failed: {e}")

        return product_links

    def _analyze_url_patterns(self, product_urls: List[str], domain: str) -> Dict[str, str]:
        """
        Analyze product URLs to extract URL template pattern.

        Returns dict with product_template key.
        """
        if not product_urls:
            return {}

        # Parse URLs to find common pattern
        parsed_urls = [urlparse(url) for url in product_urls]
        paths = [p.path for p in parsed_urls]

        # Find common pattern
        # e.g., /products/some-slug -> /products/{sku_lower}
        #       /p/12345 -> /p/{sku}

        # Try to identify pattern structure
        pattern_parts = []
        for path in paths[:5]:  # Sample first 5
            parts = [p for p in path.split('/') if p]
            if len(parts) >= 2:
                # Last part is likely the SKU/slug
                base_parts = parts[:-1]
                pattern_parts.append('/'.join(base_parts))

        if pattern_parts:
            # Find most common base
            from collections import Counter
            most_common_base = Counter(pattern_parts).most_common(1)[0][0]

            # Build template
            template = f"https://{domain}/{most_common_base}/{{sku_lower}}"

            return {
                'product_template': template
            }

        return {}

    def _infer_sku_patterns(self, sample_products: List[Dict]) -> List[Dict]:
        """
        Infer SKU regex patterns from sample products.

        Returns list of pattern dicts with name, regex, description, examples.
        """
        patterns = []
        skus = []

        # Collect SKUs from samples
        for product in sample_products:
            sku = product.get('sku')
            title = product.get('title', '')

            if sku:
                skus.append(sku)
            elif title:
                # Try to extract SKU from title
                # Look for patterns like "R0530" or "ITD123456"
                matches = re.findall(r'\b[A-Z]{1,3}\d{3,6}[A-Z]?\b', title)
                skus.extend(matches)

        if not skus:
            return []

        # Test each pattern against collected SKUs
        for regex, description in self.SKU_REGEX_PATTERNS:
            matching_skus = [sku for sku in skus if re.match(regex, sku, re.IGNORECASE)]

            if len(matching_skus) >= 2:  # Need at least 2 matches
                patterns.append({
                    'name': description.split('(')[0].strip().lower().replace(' ', '_'),
                    'regex': regex,
                    'description': description,
                    'examples': matching_skus[:3]
                })

        return patterns

    def _extract_vendor_name(self, domain: str) -> str:
        """Extract vendor name from domain."""
        # Remove www. and TLD
        name = re.sub(r'^www\.', '', domain)
        name = re.sub(r'\.(com|de|at|ch|net|org)$', '', name)

        # Convert to title case
        return name.replace('-', ' ').replace('_', ' ').title()
