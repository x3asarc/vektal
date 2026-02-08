"""
GSD Mappings Populator

Auto-populate GSD (Get Shit Done) mappings with discovered SKU→URL pairs.
Enables 10x faster scraping by using direct URLs instead of search/discovery.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import re

import httpx

from .firecrawl_client import FirecrawlClient, CrawlResult
from ..config.loader import load_vendor_config, save_vendor_config
from ..config.vendor_schema import VendorConfig


class GSDPopulator:
    """
    Auto-populate GSD mappings for a vendor.

    Uses Firecrawl to crawl collection pages, extract product URLs,
    match URLs to SKUs, and update vendor YAML config.

    Usage:
        populator = GSDPopulator(
            vendor_name="ralph_wiggum",
            firecrawl_client=FirecrawlClient()
        )
        mappings = populator.populate_from_collection(
            "https://ralph-wiggum.com/collections/all"
        )
        count = populator.update_vendor_config(mappings)
    """

    def __init__(
        self,
        vendor_name: str,
        firecrawl_client: Optional[FirecrawlClient] = None,
        config_dir: str = "config/vendors"
    ):
        """
        Initialize GSD populator.

        Args:
            vendor_name: Vendor name (matches YAML filename without .yaml)
            firecrawl_client: FirecrawlClient instance. Creates new one if None.
            config_dir: Directory containing vendor YAML configs
        """
        self.vendor_name = vendor_name
        self.config_dir = Path(config_dir)
        self.config_path = self.config_dir / f"{vendor_name}.yaml"

        # Load vendor config
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Vendor config not found: {self.config_path}"
            )
        self.config = load_vendor_config(self.config_path)

        # Firecrawl client (create if not provided)
        self.firecrawl = firecrawl_client or FirecrawlClient()
        self._owns_firecrawl = firecrawl_client is None

    def populate_from_collection(
        self,
        collection_url: str,
        max_pages: int = 100
    ) -> dict[str, str]:
        """
        Crawl a collection page and extract SKU→URL mappings.

        Args:
            collection_url: Collection page URL to crawl
            max_pages: Maximum pages to crawl (default 100)

        Returns:
            Dict of {SKU: direct_url} mappings
        """
        # Crawl collection with Firecrawl
        crawl_results = self.firecrawl.crawl(collection_url, max_pages=max_pages)

        # Extract product URLs
        product_urls = self.firecrawl.extract_product_urls(crawl_results)

        # Match URLs to SKUs
        mappings = {}
        for url, extracted_sku in product_urls:
            # Try to extract SKU from URL first
            if extracted_sku:
                sku = self._normalize_sku(extracted_sku)
                if self._validate_sku(sku):
                    mappings[sku] = url
                    continue

            # Fall back to matching URL against vendor patterns
            sku = self._extract_sku_from_url(url, self.config.sku_patterns)
            if sku:
                sku = self._normalize_sku(sku)
                if self._validate_sku(sku):
                    mappings[sku] = url

        return mappings

    def populate_from_content(
        self,
        url: str
    ) -> dict[str, str]:
        """
        Scrape a single page and extract SKU→URL mapping.

        Useful for individual product pages or when URL already known.

        Args:
            url: Product page URL

        Returns:
            Dict with single {SKU: url} mapping or empty dict if SKU not found
        """
        # Extract SKU from URL
        sku = self._extract_sku_from_url(url, self.config.sku_patterns)

        if not sku:
            # Try scraping content for SKU
            scrape_result = self.firecrawl.scrape(url)
            sku = self._extract_sku_from_content(
                scrape_result.markdown or "",
                scrape_result.html or ""
            )

        if sku:
            sku = self._normalize_sku(sku)
            if self._validate_sku(sku):
                return {sku: url}

        return {}

    def _extract_sku_from_url(
        self,
        url: str,
        sku_patterns: list
    ) -> Optional[str]:
        """
        Extract SKU from URL using vendor's SKU patterns.

        Args:
            url: Product URL
            sku_patterns: List of SKUPattern objects from vendor config

        Returns:
            Extracted SKU or None
        """
        for pattern in sku_patterns:
            # Try pattern against full URL
            match = re.search(pattern.regex, url, re.IGNORECASE)
            if match:
                # Use first capture group or full match
                sku = match.group(1) if match.groups() else match.group(0)
                return sku

        return None

    def _extract_sku_from_content(
        self,
        markdown: str,
        html: str
    ) -> Optional[str]:
        """
        Extract SKU from page content.

        Looks for SKU in common locations:
        - Title/heading
        - Product code field
        - SKU field
        - Article number

        Args:
            markdown: Markdown content from Firecrawl
            html: HTML content from Firecrawl

        Returns:
            Extracted SKU or None
        """
        content = markdown + "\n" + html

        # Common SKU field patterns
        sku_field_patterns = [
            r'(?:SKU|Article|Product Code|Item)[:\s]+([A-Z0-9-]+)',
            r'Art\.\s*Nr\.\s*[:\s]+([A-Z0-9-]+)',  # German
            r'Artikelnummer[:\s]+([A-Z0-9-]+)',  # German
        ]

        for pattern in sku_field_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

        # Try vendor patterns against content
        for pattern in self.config.sku_patterns:
            match = re.search(pattern.regex, content, re.IGNORECASE)
            if match:
                sku = match.group(1) if match.groups() else match.group(0)
                return sku

        return None

    def _normalize_sku(self, sku: str) -> str:
        """
        Normalize SKU to vendor's standard format.

        Uses vendor's URL normalization rules if available.

        Args:
            sku: Raw SKU string

        Returns:
            Normalized SKU
        """
        # Apply vendor normalization rules
        if self.config.urls.normalization:
            norm = self.config.urls.normalization

            if norm.lowercase_sku:
                sku = sku.lower()
            else:
                sku = sku.upper()

            # Replace characters
            if norm.replace_chars:
                for old_char, new_char in norm.replace_chars.items():
                    sku = sku.replace(old_char, new_char)

            # Strip size suffix if configured
            if norm.strip_size_suffix:
                # Remove common size suffixes like -A4, -A3
                sku = re.sub(r'-[A-Z]\d+$', '', sku, flags=re.IGNORECASE)

        else:
            # Default: uppercase, no hyphens
            sku = sku.upper().replace('-', '')

        return sku

    def _validate_sku(self, sku: str) -> bool:
        """
        Validate SKU matches vendor's patterns.

        Args:
            sku: SKU to validate

        Returns:
            True if SKU is valid for this vendor
        """
        for pattern in self.config.sku_patterns:
            if re.match(pattern.regex, sku, re.IGNORECASE):
                return True
        return False

    def update_vendor_config(
        self,
        mappings: dict[str, str]
    ) -> int:
        """
        Update vendor config with new GSD mappings.

        Merges new mappings into existing ones (doesn't overwrite).

        Args:
            mappings: Dict of {SKU: URL} to add

        Returns:
            Count of new mappings added (excludes duplicates)
        """
        # Initialize gsd_mappings if not present
        if not self.config.gsd_mappings:
            from ..config.vendor_schema import GSDMappings
            self.config.gsd_mappings = GSDMappings()

        # Merge new mappings (don't overwrite existing)
        existing = self.config.gsd_mappings.mappings
        new_count = 0

        for sku, url in mappings.items():
            if sku not in existing:
                existing[sku] = url
                new_count += 1

        # Update metadata
        self.config.gsd_mappings.last_discovery_run = datetime.now()
        self.config.gsd_mappings.discovery_source = "firecrawl"
        self.config.gsd_mappings.total_mapped_skus = len(existing)

        # Update vendor meta
        self.config.meta.last_modified = datetime.now()

        # Save config
        save_vendor_config(self.config, self.config_path)

        return new_count

    def verify_mappings(
        self,
        sample_size: int = 10,
        timeout: float = 5.0
    ) -> dict[str, any]:
        """
        Verify a sample of mappings still resolve.

        Args:
            sample_size: Number of random mappings to verify
            timeout: HTTP request timeout in seconds

        Returns:
            Dict with verification stats:
            {
                "total_checked": int,
                "successful": int,
                "failed": int,
                "success_rate": float,
                "failed_skus": list[str]
            }
        """
        if not self.config.gsd_mappings or not self.config.gsd_mappings.mappings:
            return {
                "total_checked": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "failed_skus": []
            }

        # Sample mappings
        import random
        mappings = list(self.config.gsd_mappings.mappings.items())
        sample = random.sample(mappings, min(sample_size, len(mappings)))

        successful = 0
        failed = 0
        failed_skus = []

        with httpx.Client(timeout=timeout) as client:
            for sku, url in sample:
                try:
                    # HEAD request to verify URL resolves
                    response = client.head(url, follow_redirects=True)
                    if response.status_code < 400:
                        successful += 1
                    else:
                        failed += 1
                        failed_skus.append(sku)
                except Exception:
                    failed += 1
                    failed_skus.append(sku)

        total_checked = successful + failed
        success_rate = (successful / total_checked) if total_checked > 0 else 0.0

        return {
            "total_checked": total_checked,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
            "failed_skus": failed_skus
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - clean up Firecrawl client if we own it."""
        if self._owns_firecrawl:
            self.firecrawl.close()

    def close(self):
        """Close resources."""
        if self._owns_firecrawl:
            self.firecrawl.close()
