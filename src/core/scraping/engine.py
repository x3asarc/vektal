"""
Universal Scraping Engine

One engine that works with ANY vendor YAML config.
Selects strategy based on config, handles retries, validates results.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.core.config import load_vendor_config, VendorConfig
from src.core.discovery.sku_validator import normalize_sku, extract_sku_info, infer_size_from_sku
from .strategies.base import BaseStrategy, StrategyResult
from .strategies.playwright_strategy import PlaywrightStrategy
from .strategies.requests_strategy import RequestsStrategy

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when rate limit detected."""
    pass


class ScrapeError(Exception):
    """General scrape error."""
    pass


@dataclass
class ScrapeResult:
    """Complete scrape result."""
    success: bool
    sku: str
    vendor_name: str

    # Extracted data
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[str] = None
    images: list[str] = field(default_factory=list)
    sku_on_page: Optional[str] = None
    availability: Optional[str] = None
    inferred_size: Optional[str] = None

    # Metadata
    source_url: str = ""
    strategy_used: str = ""
    attempts: int = 1
    scrape_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Validation
    sku_validated: bool = False
    validation_errors: list[str] = field(default_factory=list)
    error: Optional[str] = None


class UniversalScraper:
    """
    Universal scraping engine that works with any vendor config.

    Usage:
        scraper = UniversalScraper()
        result = await scraper.scrape("R0530", vendor_config)
    """

    def __init__(
        self,
        vendor_config_dir: str = "config/vendors",
        max_retries: int = 4
    ):
        """
        Initialize scraper.

        Args:
            vendor_config_dir: Directory with vendor YAML configs
            max_retries: Maximum retry attempts
        """
        self.vendor_config_dir = Path(vendor_config_dir)
        self.max_retries = max_retries

        # Strategy instances
        self._strategies: dict[str, BaseStrategy] = {}

    def _get_strategy(self, strategy_name: str) -> BaseStrategy:
        """Get or create strategy instance."""
        if strategy_name not in self._strategies:
            if strategy_name == 'playwright':
                self._strategies[strategy_name] = PlaywrightStrategy()
            elif strategy_name == 'requests':
                self._strategies[strategy_name] = RequestsStrategy()
            else:
                # Default to requests
                self._strategies[strategy_name] = RequestsStrategy()

        return self._strategies[strategy_name]

    def _build_product_url(self, sku: str, config: VendorConfig) -> str:
        """Build product URL from template."""
        sku_info = extract_sku_info(sku)

        # Check GSD mappings first (direct URLs)
        if config.gsd_mappings and config.gsd_mappings.get('mappings'):
            direct_url = config.gsd_mappings['mappings'].get(sku)
            if direct_url:
                return direct_url

        # Build from template
        template = config.urls.get('product', {}).get('template', '')

        if not template:
            raise ValueError(f"No product URL template in config for {config.vendor.name}")

        url = template.replace('{domain}', config.vendor.domain)
        url = url.replace('{sku}', sku)
        url = url.replace('{sku_lower}', sku_info.normalized.lower())
        url = url.replace('{sku_upper}', sku_info.normalized.upper())
        url = url.replace('{sku_base}', sku_info.base_sku)

        return url

    async def scrape(
        self,
        sku: str,
        vendor_config: VendorConfig,
        direct_url: Optional[str] = None
    ) -> ScrapeResult:
        """
        Scrape product data.

        Args:
            sku: Product SKU
            vendor_config: Vendor configuration
            direct_url: Optional direct URL (bypasses template)

        Returns:
            ScrapeResult with extracted data
        """
        import time
        start_time = time.time()

        sku_info = extract_sku_info(sku)
        inferred_size = infer_size_from_sku(
            sku,
            vendor_config.variants.get('size_encoding', {}).get('mappings')
            if vendor_config.variants else None
        )

        # Get URL
        url = direct_url or self._build_product_url(sku, vendor_config)

        # Get strategy
        strategy_name = vendor_config.scraping.get('strategy', {}).get('primary', 'playwright')
        fallback_strategies = vendor_config.scraping.get('strategy', {}).get('fallback', ['requests'])

        strategies_to_try = [strategy_name] + fallback_strategies

        last_error = None
        attempts = 0

        for strategy_name in strategies_to_try[:self.max_retries]:
            attempts += 1
            strategy = self._get_strategy(strategy_name)

            try:
                result = await self._scrape_with_retry(
                    strategy=strategy,
                    url=url,
                    selectors=vendor_config.selectors,
                    config={
                        'timing': vendor_config.scraping.get('timing', {}),
                        'quirks': vendor_config.quirks if hasattr(vendor_config, 'quirks') else {},
                        'browser': vendor_config.scraping.get('browser', {})
                    }
                )

                if result.success:
                    # Validate result
                    validated, errors = self._validate_result(result, sku, vendor_config)

                    elapsed = int((time.time() - start_time) * 1000)

                    return ScrapeResult(
                        success=True,
                        sku=sku,
                        vendor_name=vendor_config.vendor.name,
                        title=result.title,
                        description=result.description,
                        price=result.price,
                        images=result.images,
                        sku_on_page=result.sku_on_page,
                        availability=result.availability,
                        inferred_size=inferred_size,
                        source_url=url,
                        strategy_used=strategy_name,
                        attempts=attempts,
                        scrape_time_ms=elapsed,
                        sku_validated=validated,
                        validation_errors=errors
                    )

                last_error = result.error

            except RateLimitError as e:
                logger.warning(f"Rate limited on {strategy_name}: {e}")
                last_error = str(e)
                # Don't try more strategies, wait and retry same
                continue

            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}")
                last_error = str(e)
                continue

        # All strategies failed
        elapsed = int((time.time() - start_time) * 1000)

        return ScrapeResult(
            success=False,
            sku=sku,
            vendor_name=vendor_config.vendor.name,
            source_url=url,
            attempts=attempts,
            scrape_time_ms=elapsed,
            error=last_error or "All strategies failed"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True
    )
    async def _scrape_with_retry(
        self,
        strategy: BaseStrategy,
        url: str,
        selectors: dict,
        config: dict
    ) -> StrategyResult:
        """Scrape with retry logic."""
        result = await strategy.scrape(url, selectors, config)

        # Check for rate limit patterns
        if result.error:
            error_lower = result.error.lower()
            if any(pattern in error_lower for pattern in ['429', 'rate limit', 'too many']):
                raise RateLimitError(result.error)

        return result

    def _validate_result(
        self,
        result: StrategyResult,
        expected_sku: str,
        config: VendorConfig
    ) -> tuple[bool, list[str]]:
        """Validate scraped data."""
        errors = []

        validation_rules = config.validation if hasattr(config, 'validation') else {}

        # Check SKU match
        sku_rules = validation_rules.get('sku', {})
        if sku_rules.get('must_match_input', True) and result.sku_on_page:
            expected_norm = normalize_sku(expected_sku)
            actual_norm = normalize_sku(result.sku_on_page)

            if sku_rules.get('normalize_before_compare', True):
                # Apply allowed variations
                variations = sku_rules.get('allowed_variations', [])
                if 'case_insensitive' in variations:
                    expected_norm = expected_norm.lower()
                    actual_norm = actual_norm.lower()
                if 'ignore_hyphens' in variations:
                    expected_norm = expected_norm.replace('-', '')
                    actual_norm = actual_norm.replace('-', '')

            if expected_norm != actual_norm:
                errors.append(f"SKU mismatch: expected {expected_sku}, found {result.sku_on_page}")

        # Check images
        image_rules = validation_rules.get('images', {})
        min_images = image_rules.get('min_count', 1)
        if len(result.images) < min_images:
            errors.append(f"Too few images: {len(result.images)} < {min_images}")

        # Check for placeholder images
        if image_rules.get('reject_placeholders', True):
            placeholder_patterns = image_rules.get('placeholder_patterns', [
                'no-image', 'placeholder', 'coming-soon'
            ])
            for img in result.images:
                for pattern in placeholder_patterns:
                    if pattern in img.lower():
                        errors.append(f"Placeholder image detected: {img}")
                        break

        # Check content
        content_rules = validation_rules.get('content', {})
        required_fields = content_rules.get('required_fields', ['title', 'images'])

        if 'title' in required_fields and not result.title:
            errors.append("Missing required field: title")

        if 'images' in required_fields and not result.images:
            errors.append("Missing required field: images")

        return len(errors) == 0, errors

    async def scrape_batch(
        self,
        skus: list[str],
        vendor_config: VendorConfig,
        batch_size: int = 10,
        delay_between_batches_ms: int = 5000
    ) -> list[ScrapeResult]:
        """
        Scrape multiple SKUs in batches.

        Args:
            skus: List of SKUs to scrape
            vendor_config: Vendor configuration
            batch_size: SKUs per batch
            delay_between_batches_ms: Delay between batches

        Returns:
            List of ScrapeResult for each SKU
        """
        results = []

        for i in range(0, len(skus), batch_size):
            batch = skus[i:i + batch_size]

            # Scrape batch concurrently (limited)
            batch_tasks = [
                self.scrape(sku, vendor_config)
                for sku in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks)
            results.extend(batch_results)

            # Delay between batches
            if i + batch_size < len(skus):
                await asyncio.sleep(delay_between_batches_ms / 1000)

        return results

    async def close(self):
        """Clean up all strategy resources."""
        for strategy in self._strategies.values():
            await strategy.close()
