import pytest
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import asdict

from src.core.scraping import (
    UniversalScraper,
    ScrapeResult,
    PlaywrightStrategy,
    RequestsStrategy,
    StrategyResult
)
from src.core.config.vendor_schema import VendorConfig, VendorIdentity, VendorURLs, SKUPattern


class TestScrapeResult:
    """Test ScrapeResult dataclass"""

    def test_successful_result(self):
        result = ScrapeResult(
            success=True,
            sku="R0530",
            vendor_name="ITD Collection",
            title="Rice Paper A4",
            images=["https://example.com/img.jpg"],
            source_url="https://itd.com/r0530"
        )
        assert result.success
        assert result.sku == "R0530"
        assert len(result.images) == 1

    def test_failed_result(self):
        result = ScrapeResult(
            success=False,
            sku="R0530",
            vendor_name="ITD Collection",
            error="Connection timeout"
        )
        assert not result.success
        assert result.error == "Connection timeout"


class TestStrategyResult:
    """Test StrategyResult dataclass"""

    def test_strategy_result(self):
        result = StrategyResult(
            success=True,
            title="Product Title",
            images=["img1.jpg", "img2.jpg"],
            source_url="https://example.com",
            strategy_name="playwright"
        )
        assert result.success
        assert len(result.images) == 2
        assert result.strategy_name == "playwright"


class TestUniversalScraper:
    """Test UniversalScraper engine"""

    def test_build_product_url(self):
        """Test URL building from template"""
        scraper = UniversalScraper()

        # Mock config
        config = Mock()
        config.vendor = Mock()
        config.vendor.domain = "itdcollection.com"
        config.urls = {
            'product': {'template': 'https://{domain}/products/{sku_lower}'}
        }
        config.gsd_mappings = None

        url = scraper._build_product_url("R0530", config)
        assert url == "https://itdcollection.com/products/r0530"

    def test_build_product_url_with_gsd(self):
        """Test URL from GSD mappings (direct URL)"""
        scraper = UniversalScraper()

        config = Mock()
        config.gsd_mappings = {
            'mappings': {'R0530': 'https://direct.url/product'}
        }

        url = scraper._build_product_url("R0530", config)
        assert url == "https://direct.url/product"

    def test_get_strategy_playwright(self):
        """Get playwright strategy"""
        scraper = UniversalScraper()
        strategy = scraper._get_strategy('playwright')
        assert isinstance(strategy, PlaywrightStrategy)

    def test_get_strategy_requests(self):
        """Get requests strategy"""
        scraper = UniversalScraper()
        strategy = scraper._get_strategy('requests')
        assert isinstance(strategy, RequestsStrategy)

    def test_validate_result_sku_match(self):
        """Validate SKU matching"""
        scraper = UniversalScraper()

        config = Mock()
        config.validation = {
            'sku': {
                'must_match_input': True,
                'normalize_before_compare': True,
                'allowed_variations': ['case_insensitive']
            },
            'images': {'min_count': 1, 'reject_placeholders': True},
            'content': {'required_fields': ['title', 'images']}
        }

        # Matching SKU
        result = StrategyResult(
            success=True,
            title="Product",
            images=["img.jpg"],
            sku_on_page="r0530",  # Lowercase
            source_url="",
            strategy_name=""
        )
        validated, errors = scraper._validate_result(result, "R0530", config)
        assert validated

    def test_validate_result_sku_mismatch(self):
        """Detect SKU mismatch"""
        scraper = UniversalScraper()

        config = Mock()
        config.validation = {
            'sku': {
                'must_match_input': True,
                'normalize_before_compare': True,
                'allowed_variations': []  # Strict comparison
            },
            'images': {'min_count': 1},
            'content': {'required_fields': []}
        }

        result = StrategyResult(
            success=True,
            title="Product",
            images=["img.jpg"],
            sku_on_page="R0531",  # Wrong SKU
            source_url="",
            strategy_name=""
        )
        validated, errors = scraper._validate_result(result, "R0530", config)
        assert not validated
        assert any("mismatch" in e.lower() for e in errors)

    def test_validate_result_placeholder_image(self):
        """Detect placeholder images"""
        scraper = UniversalScraper()

        config = Mock()
        config.validation = {
            'sku': {'must_match_input': False},
            'images': {
                'min_count': 1,
                'reject_placeholders': True,
                'placeholder_patterns': ['no-image']
            },
            'content': {'required_fields': []}
        }

        result = StrategyResult(
            success=True,
            title="Product",
            images=["https://example.com/no-image.jpg"],
            source_url="",
            strategy_name=""
        )
        validated, errors = scraper._validate_result(result, "R0530", config)
        assert not validated
        assert any("placeholder" in e.lower() for e in errors)


class TestRequestsStrategy:
    """Test RequestsStrategy"""

    def test_strategy_name(self):
        strategy = RequestsStrategy()
        assert strategy.name == "requests"


class TestPlaywrightStrategy:
    """Test PlaywrightStrategy"""

    def test_strategy_name(self):
        strategy = PlaywrightStrategy()
        assert strategy.name == "playwright"

    def test_headless_default(self):
        strategy = PlaywrightStrategy()
        assert strategy.headless is True
