"""
Unit tests for Firecrawl integration.

Tests FirecrawlClient and GSDPopulator functionality with mocked API responses.
"""

import os
from unittest.mock import Mock, patch, MagicMock
import pytest
import httpx

from src.core.discovery.firecrawl_client import (
    FirecrawlClient,
    FirecrawlAPIError,
    FirecrawlRateLimitError,
    CrawlResult,
    ScrapeResult
)
from src.core.discovery.gsd_populator import GSDPopulator
from src.core.config.vendor_schema import (
    VendorConfig,
    VendorMeta,
    VendorIdentity,
    VendorNiche,
    SKUPattern,
    VendorURLs,
    Selectors,
    GSDMappings
)


# ============================================================================
# FIRECRAWL CLIENT TESTS
# ============================================================================

class TestFirecrawlClientInit:
    """Test FirecrawlClient initialization."""

    def test_init_with_api_key(self):
        """Should initialize with provided API key."""
        client = FirecrawlClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"
        assert "Bearer test-key-123" in client.headers["Authorization"]

    def test_init_from_environment(self):
        """Should read API key from FIRECRAWL_API_KEY environment variable."""
        with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "env-key-456"}):
            client = FirecrawlClient()
            assert client.api_key == "env-key-456"

    def test_init_no_api_key_raises_error(self):
        """Should raise ValueError if no API key provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key required"):
                FirecrawlClient()


class TestFirecrawlCrawl:
    """Test crawl() method with mocked API."""

    @patch('src.core.discovery.firecrawl_client.httpx.Client')
    def test_crawl_success(self, mock_client_class):
        """Should successfully crawl and return results."""
        # Mock API responses
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Start crawl response
        start_response = MagicMock()
        start_response.json.return_value = {"id": "job-123"}
        start_response.raise_for_status = MagicMock()

        # Poll response (completed)
        poll_response = MagicMock()
        poll_response.json.return_value = {
            "status": "completed",
            "data": [
                {
                    "url": "https://example.com/product/R0530",
                    "markdown": "# Product R0530",
                    "html": "<h1>Product R0530</h1>",
                    "metadata": {"title": "Product R0530"}
                }
            ]
        }
        poll_response.raise_for_status = MagicMock()

        mock_client.post.return_value = start_response
        mock_client.get.return_value = poll_response

        # Test
        client = FirecrawlClient(api_key="test-key")
        results = client.crawl("https://example.com/collections/all", max_pages=10)

        assert len(results) == 1
        assert results[0].url == "https://example.com/product/R0530"
        assert results[0].markdown == "# Product R0530"

    @patch('src.core.discovery.firecrawl_client.httpx.Client')
    def test_crawl_rate_limit_error(self, mock_client_class):
        """Should raise FirecrawlRateLimitError on 429 status."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock 429 response
        error_response = MagicMock()
        error_response.status_code = 429
        mock_client.post.side_effect = httpx.HTTPStatusError(
            "Rate limit",
            request=MagicMock(),
            response=error_response
        )

        client = FirecrawlClient(api_key="test-key")
        with pytest.raises(FirecrawlRateLimitError):
            client.crawl("https://example.com/collections/all")

    @patch('src.core.discovery.firecrawl_client.httpx.Client')
    @patch('src.core.discovery.firecrawl_client.time.sleep')
    def test_crawl_timeout(self, mock_sleep, mock_client_class):
        """Should raise TimeoutError if crawl doesn't complete."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Start crawl response
        start_response = MagicMock()
        start_response.json.return_value = {"id": "job-123"}
        start_response.raise_for_status = MagicMock()

        # Poll response (still running)
        poll_response = MagicMock()
        poll_response.json.return_value = {"status": "running"}
        poll_response.raise_for_status = MagicMock()

        mock_client.post.return_value = start_response
        mock_client.get.return_value = poll_response

        client = FirecrawlClient(api_key="test-key")
        with pytest.raises(TimeoutError):
            client.crawl("https://example.com/collections/all", timeout_seconds=1)


class TestFirecrawlScrape:
    """Test scrape() method."""

    @patch('src.core.discovery.firecrawl_client.httpx.Client')
    def test_scrape_success(self, mock_client_class):
        """Should successfully scrape single page."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock scrape response
        scrape_response = MagicMock()
        scrape_response.json.return_value = {
            "url": "https://example.com/product/R0530",
            "markdown": "# Product",
            "html": "<h1>Product</h1>",
            "metadata": {}
        }
        scrape_response.raise_for_status = MagicMock()
        mock_client.post.return_value = scrape_response

        client = FirecrawlClient(api_key="test-key")
        result = client.scrape("https://example.com/product/R0530")

        assert result.url == "https://example.com/product/R0530"
        assert result.markdown == "# Product"


class TestExtractProductUrls:
    """Test extract_product_urls() method."""

    def test_extract_product_urls_filters_non_products(self):
        """Should filter out non-product pages."""
        client = FirecrawlClient(api_key="test-key")

        crawl_results = [
            CrawlResult(url="https://example.com/products/R0530", markdown=""),
            CrawlResult(url="https://example.com/collections/all", markdown=""),
            CrawlResult(url="https://example.com/about", markdown=""),
            CrawlResult(url="https://example.com/p/R0531", markdown=""),
        ]

        product_urls = client.extract_product_urls(crawl_results)

        assert len(product_urls) == 2
        assert product_urls[0][0] == "https://example.com/products/R0530"
        assert product_urls[1][0] == "https://example.com/p/R0531"

    def test_extract_sku_from_url_patterns(self):
        """Should extract SKU from various URL patterns."""
        client = FirecrawlClient(api_key="test-key")

        test_cases = [
            ("https://example.com/products/R0530", "R0530"),
            ("https://example.com/item/r-0531", "R0531"),
            ("https://example.com/p/R0532-description", "R0532"),
            ("https://example.com/product?sku=R0533", "R0533"),
        ]

        for url, expected_sku in test_cases:
            sku = client._extract_sku_from_url(url)
            assert sku == expected_sku, f"Failed for URL: {url}"


# ============================================================================
# GSD POPULATOR TESTS
# ============================================================================

@pytest.fixture
def mock_vendor_config():
    """Create a mock vendor config."""
    return VendorConfig(
        meta=VendorMeta(),
        vendor=VendorIdentity(
            name="Test Vendor",
            name_short="TV",
            slug="test_vendor",
            domain="test-vendor.com"
        ),
        niche=VendorNiche(primary="arts_and_crafts"),
        sku_patterns=[
            SKUPattern(
                name="standard",
                regex=r'[A-Z]{1,3}\d{3,6}',
                description="Standard SKU format",
                examples=["R0530", "AB1234"]
            )
        ],
        urls=VendorURLs(
            product={
                "template": "https://test-vendor.com/products/{sku_lower}"
            }
        ),
        selectors={"images": {"container": ".images", "items": "img"}},
        gsd_mappings=GSDMappings()
    )


class TestGSDPopulatorInit:
    """Test GSDPopulator initialization."""

    def test_init_loads_vendor_config(self, tmp_path, mock_vendor_config):
        """Should load vendor config on initialization."""
        # Save mock config
        from src.core.config.loader import save_vendor_config
        config_path = tmp_path / "test_vendor.yaml"
        save_vendor_config(mock_vendor_config, config_path)

        # Initialize populator
        with patch('src.core.discovery.gsd_populator.FirecrawlClient'):
            populator = GSDPopulator(
                vendor_name="test_vendor",
                config_dir=str(tmp_path)
            )
            assert populator.config.vendor.name == "Test Vendor"

    def test_init_missing_config_raises_error(self, tmp_path):
        """Should raise FileNotFoundError if vendor config doesn't exist."""
        with pytest.raises(FileNotFoundError):
            GSDPopulator(
                vendor_name="nonexistent",
                config_dir=str(tmp_path)
            )


class TestGSDPopulatorPopulate:
    """Test populate_from_collection()."""

    def test_populate_from_collection_extracts_mappings(
        self,
        tmp_path,
        mock_vendor_config
    ):
        """Should extract SKU→URL mappings from crawl results."""
        # Save mock config
        from src.core.config.loader import save_vendor_config
        config_path = tmp_path / "test_vendor.yaml"
        save_vendor_config(mock_vendor_config, config_path)

        # Mock Firecrawl client
        mock_firecrawl = Mock()
        mock_firecrawl.crawl.return_value = [
            CrawlResult(
                url="https://test-vendor.com/products/R0530",
                markdown="# Product R0530"
            ),
            CrawlResult(
                url="https://test-vendor.com/products/AB1234",
                markdown="# Product AB1234"
            ),
        ]
        mock_firecrawl.extract_product_urls.return_value = [
            ("https://test-vendor.com/products/R0530", "R0530"),
            ("https://test-vendor.com/products/AB1234", "AB1234"),
        ]

        # Test
        populator = GSDPopulator(
            vendor_name="test_vendor",
            firecrawl_client=mock_firecrawl,
            config_dir=str(tmp_path)
        )
        mappings = populator.populate_from_collection(
            "https://test-vendor.com/collections/all"
        )

        assert len(mappings) == 2
        assert mappings["R0530"] == "https://test-vendor.com/products/R0530"
        assert mappings["AB1234"] == "https://test-vendor.com/products/AB1234"


class TestGSDPopulatorUpdateConfig:
    """Test update_vendor_config()."""

    def test_update_vendor_config_adds_new_mappings(
        self,
        tmp_path,
        mock_vendor_config
    ):
        """Should add new mappings to vendor config."""
        # Save mock config
        from src.core.config.loader import save_vendor_config, load_vendor_config
        config_path = tmp_path / "test_vendor.yaml"
        save_vendor_config(mock_vendor_config, config_path)

        # Create populator
        mock_firecrawl = Mock()
        populator = GSDPopulator(
            vendor_name="test_vendor",
            firecrawl_client=mock_firecrawl,
            config_dir=str(tmp_path)
        )

        # Update config
        new_mappings = {
            "R0530": "https://test-vendor.com/products/R0530",
            "AB1234": "https://test-vendor.com/products/AB1234"
        }
        count = populator.update_vendor_config(new_mappings)

        assert count == 2

        # Verify saved config
        reloaded = load_vendor_config(config_path)
        assert reloaded.gsd_mappings.total_mapped_skus == 2
        assert reloaded.gsd_mappings.mappings["R0530"] == "https://test-vendor.com/products/R0530"
        assert reloaded.gsd_mappings.discovery_source == "firecrawl"
        assert reloaded.gsd_mappings.last_discovery_run is not None

    def test_update_vendor_config_skips_duplicates(
        self,
        tmp_path,
        mock_vendor_config
    ):
        """Should not overwrite existing mappings."""
        # Add existing mapping
        mock_vendor_config.gsd_mappings.mappings = {
            "R0530": "https://test-vendor.com/old-url"
        }

        # Save mock config
        from src.core.config.loader import save_vendor_config, load_vendor_config
        config_path = tmp_path / "test_vendor.yaml"
        save_vendor_config(mock_vendor_config, config_path)

        # Create populator
        mock_firecrawl = Mock()
        populator = GSDPopulator(
            vendor_name="test_vendor",
            firecrawl_client=mock_firecrawl,
            config_dir=str(tmp_path)
        )

        # Try to add duplicate
        new_mappings = {
            "R0530": "https://test-vendor.com/new-url",
            "AB1234": "https://test-vendor.com/products/AB1234"
        }
        count = populator.update_vendor_config(new_mappings)

        # Should only add the new one
        assert count == 1

        # Old URL should remain
        reloaded = load_vendor_config(config_path)
        assert reloaded.gsd_mappings.mappings["R0530"] == "https://test-vendor.com/old-url"
        assert reloaded.gsd_mappings.mappings["AB1234"] == "https://test-vendor.com/products/AB1234"


class TestSKUExtraction:
    """Test SKU extraction edge cases."""

    def test_sku_extraction_url_variations(self):
        """Should extract SKU from various URL formats."""
        client = FirecrawlClient(api_key="test-key")

        test_cases = [
            # URL with SKU in path
            ("https://vendor.com/products/r0530", "R0530"),
            # URL with hyphenated SKU
            ("https://vendor.com/p/r-0530", "R0530"),
            # URL with SKU in query
            ("https://vendor.com/product?sku=R0530", "R0530"),
            # Case insensitive
            ("https://vendor.com/products/R0530", "R0530"),
            ("https://vendor.com/products/r0530", "R0530"),
        ]

        for url, expected_sku in test_cases:
            sku = client._extract_sku_from_url(url)
            assert sku == expected_sku, f"Failed for: {url}"


class TestVerifyMappings:
    """Test verify_mappings()."""

    @patch('src.core.discovery.gsd_populator.httpx.Client')
    def test_verify_mappings_success(
        self,
        mock_client_class,
        tmp_path,
        mock_vendor_config
    ):
        """Should verify mappings and return stats."""
        # Add mappings
        mock_vendor_config.gsd_mappings.mappings = {
            "R0530": "https://test-vendor.com/products/R0530",
            "AB1234": "https://test-vendor.com/products/AB1234"
        }

        # Save config
        from src.core.config.loader import save_vendor_config
        config_path = tmp_path / "test_vendor.yaml"
        save_vendor_config(mock_vendor_config, config_path)

        # Mock HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.head.return_value = mock_response

        # Test
        mock_firecrawl = Mock()
        populator = GSDPopulator(
            vendor_name="test_vendor",
            firecrawl_client=mock_firecrawl,
            config_dir=str(tmp_path)
        )
        stats = populator.verify_mappings(sample_size=2)

        assert stats["total_checked"] == 2
        assert stats["successful"] == 2
        assert stats["failed"] == 0
        assert stats["success_rate"] == 1.0
