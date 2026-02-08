"""
Firecrawl API Client

Integrates with Firecrawl API for collection page crawling and product URL extraction.
Enables GSD mapping auto-population by discovering product URLs from collection pages.
"""

import os
import time
from typing import Optional
from urllib.parse import urlparse
import re

import httpx
from pydantic import BaseModel, Field


class FirecrawlAPIError(Exception):
    """Raised when Firecrawl API returns an error."""
    pass


class FirecrawlRateLimitError(FirecrawlAPIError):
    """Raised when rate limit is exceeded."""
    pass


class CrawlResult(BaseModel):
    """Result from a Firecrawl crawl operation."""
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ScrapeResult(BaseModel):
    """Result from a Firecrawl scrape operation."""
    url: str
    markdown: Optional[str] = None
    html: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class FirecrawlClient:
    """
    Firecrawl API client for collection page crawling and product URL extraction.

    Supports:
    - Collection crawling with async polling
    - Single page scraping
    - Product URL extraction from crawled pages
    - Rate limit handling with exponential backoff

    Usage:
        client = FirecrawlClient()
        results = client.crawl("https://vendor.com/collections/all")
        product_urls = client.extract_product_urls(results)
    """

    BASE_URL = "https://api.firecrawl.dev/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl client.

        Args:
            api_key: Firecrawl API key. If None, reads from FIRECRAWL_API_KEY env var.

        Raises:
            ValueError: If API key is not provided and not in environment.
        """
        self.api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Firecrawl API key required. "
                "Provide via constructor or set FIRECRAWL_API_KEY environment variable."
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "UniversalVendorScraper/1.0"
        }

        self.client = httpx.Client(headers=self.headers, timeout=30.0)

    def crawl(
        self,
        url: str,
        max_pages: int = 100,
        timeout_seconds: int = 300
    ) -> list[CrawlResult]:
        """
        Crawl a collection page and discover product URLs.

        Starts async crawl job and polls for completion.

        Args:
            url: Collection page URL to crawl
            max_pages: Maximum number of pages to crawl (default 100)
            timeout_seconds: Max time to wait for crawl completion (default 300)

        Returns:
            List of CrawlResult objects with page content

        Raises:
            FirecrawlAPIError: If API returns error
            FirecrawlRateLimitError: If rate limit exceeded
            TimeoutError: If crawl doesn't complete within timeout
        """
        # Start crawl job
        crawl_url = f"{self.BASE_URL}/crawl"
        payload = {
            "url": url,
            "maxPages": max_pages,
            "includeMarkdown": True,
            "includeHtml": True
        }

        try:
            response = self.client.post(crawl_url, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise FirecrawlRateLimitError("Rate limit exceeded") from e
            raise FirecrawlAPIError(f"Failed to start crawl: {e}") from e
        except httpx.RequestError as e:
            raise FirecrawlAPIError(f"Request failed: {e}") from e

        data = response.json()
        job_id = data.get("id")
        if not job_id:
            raise FirecrawlAPIError("No job ID returned from crawl start")

        # Poll for completion with exponential backoff
        poll_url = f"{self.BASE_URL}/crawl/{job_id}"
        start_time = time.time()
        wait_time = 2  # Start with 2 seconds
        max_wait = 30  # Cap at 30 seconds

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(f"Crawl did not complete within {timeout_seconds}s")

            time.sleep(wait_time)

            try:
                poll_response = self.client.get(poll_url)
                poll_response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited during polling - wait longer
                    time.sleep(60)
                    continue
                raise FirecrawlAPIError(f"Polling failed: {e}") from e
            except httpx.RequestError as e:
                raise FirecrawlAPIError(f"Polling request failed: {e}") from e

            poll_data = poll_response.json()
            status = poll_data.get("status")

            if status == "completed":
                # Extract results
                results = []
                for page in poll_data.get("data", []):
                    results.append(CrawlResult(
                        url=page.get("url", ""),
                        markdown=page.get("markdown"),
                        html=page.get("html"),
                        metadata=page.get("metadata", {})
                    ))
                return results
            elif status == "failed":
                error_msg = poll_data.get("error", "Unknown error")
                raise FirecrawlAPIError(f"Crawl failed: {error_msg}")

            # Still running - increase wait time with exponential backoff
            wait_time = min(wait_time * 1.5, max_wait)

    def scrape(self, url: str) -> ScrapeResult:
        """
        Scrape a single page immediately (synchronous).

        Useful for individual product pages or quick metadata extraction.

        Args:
            url: URL to scrape

        Returns:
            ScrapeResult with page content

        Raises:
            FirecrawlAPIError: If API returns error
            FirecrawlRateLimitError: If rate limit exceeded
        """
        scrape_url = f"{self.BASE_URL}/scrape"
        payload = {
            "url": url,
            "formats": ["markdown", "html"]
        }

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.post(scrape_url, json=payload)
                response.raise_for_status()

                data = response.json()
                return ScrapeResult(
                    url=data.get("url", url),
                    markdown=data.get("markdown"),
                    html=data.get("html"),
                    metadata=data.get("metadata", {})
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    if attempt < max_retries - 1:
                        # Exponential backoff for rate limits
                        time.sleep(retry_delay * (2 ** attempt))
                        continue
                    raise FirecrawlRateLimitError("Rate limit exceeded") from e
                raise FirecrawlAPIError(f"Scrape failed: {e}") from e
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                raise FirecrawlAPIError(f"Request failed: {e}") from e

        raise FirecrawlAPIError("Scrape failed after retries")

    def extract_product_urls(
        self,
        crawl_results: list[CrawlResult]
    ) -> list[tuple[str, Optional[str]]]:
        """
        Extract product URLs from crawl results.

        Filters to only product pages (not category, about, etc.).
        Attempts to extract SKU from URL.

        Args:
            crawl_results: Results from crawl() method

        Returns:
            List of (url, extracted_sku) tuples. SKU may be None if not found in URL.
        """
        product_urls = []

        for result in crawl_results:
            url = result.url

            # Filter to only product pages
            if not self._is_product_url(url):
                continue

            # Try to extract SKU from URL
            sku = self._extract_sku_from_url(url)

            product_urls.append((url, sku))

        return product_urls

    def _is_product_url(self, url: str) -> bool:
        """
        Check if URL is likely a product page.

        Filters out:
        - Collection/category pages
        - About/contact pages
        - Checkout/cart pages
        - Account pages

        Args:
            url: URL to check

        Returns:
            True if likely a product page
        """
        url_lower = url.lower()

        # Common non-product patterns
        exclude_patterns = [
            r'/collections?/',
            r'/categories?/',
            r'/about',
            r'/contact',
            r'/cart',
            r'/checkout',
            r'/account',
            r'/login',
            r'/register',
            r'/pages?/',
            r'/blog',
            r'/search',
            r'/tags?/',
            r'/filter',
        ]

        for pattern in exclude_patterns:
            if re.search(pattern, url_lower):
                return False

        # Common product page patterns
        product_patterns = [
            r'/products?/',
            r'/p/',
            r'/item/',
            r'/product-',
            r'-p\d+\.html',
            r'/[a-z0-9-]+/[a-z0-9-]+\.html'  # Generic product path
        ]

        for pattern in product_patterns:
            if re.search(pattern, url_lower):
                return True

        # If URL has SKU-like patterns, likely a product
        if re.search(r'[A-Z]{1,3}\d{3,6}', url):
            return True

        return False

    def _extract_sku_from_url(self, url: str) -> Optional[str]:
        """
        Extract SKU from product URL.

        Tries common patterns:
        - /products/R0530
        - /item/r-0530
        - ?sku=R0530
        - /p/R0530-description

        Args:
            url: Product URL

        Returns:
            Extracted SKU or None if not found
        """
        # Try query parameter first
        if '?' in url:
            query = url.split('?')[1]
            sku_match = re.search(r'sku=([A-Za-z0-9-]+)', query, re.IGNORECASE)
            if sku_match:
                return sku_match.group(1).upper()

        # Parse URL path
        path = urlparse(url).path

        # Common SKU patterns in path
        sku_patterns = [
            r'/([A-Z]{1,3}\d{3,6})',  # /R0530
            r'/([A-Z]{1,3}-?\d{3,6})',  # /R-0530
            r'/p/([A-Za-z0-9-]+)',  # /p/R0530-description
            r'/products?/([A-Za-z0-9-]+)',  # /product/R0530
            r'/item/([A-Za-z0-9-]+)',  # /item/r-0530
        ]

        for pattern in sku_patterns:
            match = re.search(pattern, path, re.IGNORECASE)
            if match:
                sku = match.group(1)
                # Clean up: remove hyphens, uppercase
                sku = sku.replace('-', '').upper()
                # Validate it looks SKU-like (has both letters and numbers)
                if re.search(r'[A-Z]', sku) and re.search(r'\d', sku):
                    return sku

        return None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close HTTP client."""
        self.client.close()

    def close(self):
        """Close HTTP client."""
        self.client.close()
