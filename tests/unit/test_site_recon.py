"""
Unit tests for Site Reconnaissance module.

Tests selector discovery, validation, URL pattern detection,
and SKU pattern inference without requiring browser.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from core.discovery.site_recon import SiteReconnaissance, SelectorScore
from core.config.generator import SiteReconData


class TestSelectorScoring:
    """Test selector scoring algorithm."""

    @pytest.mark.asyncio
    async def test_score_selector_element_exists(self):
        """Test that existing element gets base score."""
        recon = SiteReconnaissance()

        # Mock page
        page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.inner_text = AsyncMock(return_value="Test Product")
        page.query_selector_all = AsyncMock(return_value=[mock_element])

        score = await recon._score_selector(page, 'h1.title', 'title')

        assert score.score >= 1.0
        assert score.found_count == 1
        assert score.has_content is True

    @pytest.mark.asyncio
    async def test_score_selector_no_element(self):
        """Test that missing element gets zero score."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        page.query_selector_all = AsyncMock(return_value=[])

        score = await recon._score_selector(page, '.nonexistent', 'title')

        assert score.score == 0.0
        assert score.found_count == 0

    @pytest.mark.asyncio
    async def test_score_selector_multiple_elements_penalty(self):
        """Test penalty for multiple elements on unique fields."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        mock_elements = [AsyncMock() for _ in range(3)]
        for elem in mock_elements:
            elem.inner_text = AsyncMock(return_value="Test")
        page.query_selector_all = AsyncMock(return_value=mock_elements)

        score = await recon._score_selector(page, 'h1', 'title')

        # Multiple elements should reduce score
        assert score.found_count == 3
        assert score.score < 2.0  # Penalty applied

    @pytest.mark.asyncio
    async def test_score_selector_price_type_validation(self):
        """Test content type validation for prices."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        mock_element = AsyncMock()
        mock_element.inner_text = AsyncMock(return_value="€49.99")
        page.query_selector_all = AsyncMock(return_value=[mock_element])

        score = await recon._score_selector(page, '.price', 'price')

        assert score.content_type_match is True
        assert score.score >= 2.0  # Full score with type match


class TestContentTypeValidation:
    """Test content type validation."""

    def test_validate_price_content(self):
        """Test price content validation."""
        recon = SiteReconnaissance()

        assert recon._validate_content_type("€49.99", "price") is True
        assert recon._validate_content_type("$19.99", "price") is True
        assert recon._validate_content_type("123.45", "price") is True
        assert recon._validate_content_type("Random text", "price") is False

    def test_validate_title_content(self):
        """Test title content validation."""
        recon = SiteReconnaissance()

        assert recon._validate_content_type("Product Title", "title") is True
        assert recon._validate_content_type("A", "title") is False  # Too short
        assert recon._validate_content_type("A" * 300, "title") is False  # Too long

    def test_validate_sku_content(self):
        """Test SKU content validation."""
        recon = SiteReconnaissance()

        assert recon._validate_content_type("R0530", "sku") is True
        assert recon._validate_content_type("ITD123456", "sku") is True
        assert recon._validate_content_type("AB-1234", "sku") is True
        assert recon._validate_content_type("Invalid SKU!", "sku") is False


class TestURLPatternDetection:
    """Test URL pattern extraction."""

    def test_analyze_url_patterns_shopify_style(self):
        """Test Shopify-style URL pattern detection."""
        recon = SiteReconnaissance()

        product_urls = [
            "https://example.com/products/product-one",
            "https://example.com/products/product-two",
            "https://example.com/products/product-three"
        ]

        patterns = recon._analyze_url_patterns(product_urls, "example.com")

        assert 'product_template' in patterns
        assert '{sku_lower}' in patterns['product_template']
        assert 'https://example.com/products/{sku_lower}' == patterns['product_template']

    def test_analyze_url_patterns_simple_structure(self):
        """Test simple /p/ URL pattern."""
        recon = SiteReconnaissance()

        product_urls = [
            "https://shop.com/p/12345",
            "https://shop.com/p/67890",
            "https://shop.com/p/11111"
        ]

        patterns = recon._analyze_url_patterns(product_urls, "shop.com")

        assert 'product_template' in patterns
        assert '/p/{sku_lower}' in patterns['product_template']

    def test_analyze_url_patterns_empty_list(self):
        """Test with no product URLs."""
        recon = SiteReconnaissance()

        patterns = recon._analyze_url_patterns([], "example.com")

        assert patterns == {}


class TestSKUPatternInference:
    """Test SKU pattern inference from samples."""

    def test_infer_sku_patterns_itd_format(self):
        """Test detection of ITD Collection format (R0530)."""
        recon = SiteReconnaissance()

        sample_products = [
            {'title': 'Product R0530', 'sku': 'R0530'},
            {'title': 'Product R1234L', 'sku': 'R1234L'},
            {'title': 'Product R5678', 'sku': 'R5678'}
        ]

        patterns = recon._infer_sku_patterns(sample_products)

        assert len(patterns) > 0
        # Should detect ITD Collection format
        itd_pattern = next((p for p in patterns if 'ITD Collection' in p['description']), None)
        assert itd_pattern is not None
        assert len(itd_pattern['examples']) >= 2

    def test_infer_sku_patterns_brand_prefix(self):
        """Test detection of brand prefix pattern."""
        recon = SiteReconnaissance()

        sample_products = [
            {'title': 'Product ABC123456', 'sku': 'ABC123456'},
            {'title': 'Product ABC789012', 'sku': 'ABC789012'}
        ]

        patterns = recon._infer_sku_patterns(sample_products)

        assert len(patterns) > 0
        # Should detect brand prefix pattern
        brand_pattern = next((p for p in patterns if 'prefix' in p['description'].lower()), None)
        assert brand_pattern is not None

    def test_infer_sku_patterns_no_matches(self):
        """Test with no matching patterns."""
        recon = SiteReconnaissance()

        sample_products = [
            {'title': 'Product One'},  # No SKU
            {'title': 'Product Two'}
        ]

        patterns = recon._infer_sku_patterns(sample_products)

        assert patterns == []

    def test_infer_sku_patterns_from_title(self):
        """Test SKU extraction from product titles."""
        recon = SiteReconnaissance()

        sample_products = [
            {'title': 'Amazing Product R0530 by Brand'},  # SKU in title
            {'title': 'Another Item R1234L Premium'}
        ]

        patterns = recon._infer_sku_patterns(sample_products)

        assert len(patterns) > 0
        # Should extract and detect pattern
        assert any('R0530' in p.get('examples', []) or 'R1234L' in p.get('examples', []) for p in patterns)


class TestVendorNameExtraction:
    """Test vendor name extraction from domain."""

    def test_extract_vendor_name_simple(self):
        """Test simple domain extraction."""
        recon = SiteReconnaissance()

        assert recon._extract_vendor_name("example.com") == "Example"
        assert recon._extract_vendor_name("www.example.com") == "Example"
        assert recon._extract_vendor_name("shop-name.de") == "Shop Name"

    def test_extract_vendor_name_with_hyphens(self):
        """Test domain with hyphens."""
        recon = SiteReconnaissance()

        assert recon._extract_vendor_name("my-awesome-shop.com") == "My Awesome Shop"

    def test_extract_vendor_name_various_tlds(self):
        """Test various TLDs."""
        recon = SiteReconnaissance()

        assert recon._extract_vendor_name("vendor.de") == "Vendor"
        assert recon._extract_vendor_name("vendor.at") == "Vendor"
        assert recon._extract_vendor_name("vendor.ch") == "Vendor"


class TestJavaScriptDetection:
    """Test JavaScript requirement detection."""

    @pytest.mark.asyncio
    async def test_detect_javascript_required_size_difference(self):
        """Test JS detection based on content size change."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        # Initial HTML is small, rendered is much larger
        page.content = AsyncMock(side_effect=[
            "<html><body>Loading...</body></html>",  # Initial
            "<html><body>" + "X" * 10000 + "</body></html>"  # After JS
        ])

        requires_js = await recon._detect_javascript_requirement(page)

        assert requires_js is True

    @pytest.mark.asyncio
    async def test_detect_javascript_required_framework_indicators(self):
        """Test JS detection based on framework indicators."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        page.content = AsyncMock(return_value='<div data-react-root>Content</div>')

        requires_js = await recon._detect_javascript_requirement(page)

        assert requires_js is True

    @pytest.mark.asyncio
    async def test_detect_javascript_not_required(self):
        """Test static site detection."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        static_html = "<html><body><h1>Static Content</h1></body></html>"
        page.content = AsyncMock(return_value=static_html)

        requires_js = await recon._detect_javascript_requirement(page)

        # Should not require JS for static content
        assert requires_js is False


class TestLazyLoadingDetection:
    """Test lazy loading detection."""

    @pytest.mark.asyncio
    async def test_detect_lazy_loading_present(self):
        """Test detection when lazy loading is used."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        page.content = AsyncMock(return_value='<img data-src="image.jpg" loading="lazy">')

        has_lazy = await recon._detect_lazy_loading(page)

        assert has_lazy is True

    @pytest.mark.asyncio
    async def test_detect_lazy_loading_not_present(self):
        """Test detection when no lazy loading."""
        recon = SiteReconnaissance()

        page = AsyncMock()
        page.content = AsyncMock(return_value='<img src="image.jpg">')

        has_lazy = await recon._detect_lazy_loading(page)

        assert has_lazy is False


class TestSiteReconDataPopulation:
    """Test complete SiteReconData population."""

    @pytest.mark.asyncio
    async def test_discover_populates_site_recon_data(self):
        """Test that discover() returns properly populated SiteReconData."""
        recon = SiteReconnaissance()

        # Mock the entire playwright import chain
        mock_playwright_module = MagicMock()

        # Setup mock browser and page
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        mock_p = AsyncMock()

        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Mock page navigation
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html><body>Test</body></html>")
        mock_page.evaluate = AsyncMock(return_value=[])
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.close = AsyncMock()
        mock_context.close = AsyncMock()
        mock_browser.close = AsyncMock()

        # Mock async context manager
        async def mock_async_playwright_ctx():
            class AsyncPlaywrightContextManager:
                async def __aenter__(self):
                    return mock_p
                async def __aexit__(self, *args):
                    return None
            return AsyncPlaywrightContextManager()

        mock_async_playwright = MagicMock(side_effect=mock_async_playwright_ctx)
        mock_playwright_module.async_playwright = mock_async_playwright

        # Mock the imports
        with patch('core.discovery.site_recon._check_playwright', return_value=True):
            with patch.dict('sys.modules', {'playwright.async_api': mock_playwright_module}):
                # Execute discovery
                result = await recon.discover("https://example.com", "Test Vendor")

                # Verify SiteReconData fields
                assert result is not None
                assert hasattr(result, 'domain')
                assert result.domain == "example.com"
                assert result.vendor_name == "Test Vendor"
                assert hasattr(result, 'requires_javascript')
                assert hasattr(result, 'has_lazy_loading')
                assert hasattr(result, 'has_collection_pages')
                assert hasattr(result, 'sample_products')

    @pytest.mark.asyncio
    async def test_discover_handles_errors_gracefully(self):
        """Test error handling during discovery."""
        recon = SiteReconnaissance()

        # Mock playwright with browser failure
        mock_playwright_module = MagicMock()
        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(side_effect=Exception("Browser launch failed"))

        async def mock_async_playwright_ctx():
            class AsyncPlaywrightContextManager:
                async def __aenter__(self):
                    return mock_p
                async def __aexit__(self, *args):
                    return None
            return AsyncPlaywrightContextManager()

        mock_async_playwright = MagicMock(side_effect=mock_async_playwright_ctx)
        mock_playwright_module.async_playwright = mock_async_playwright

        with patch('core.discovery.site_recon._check_playwright', return_value=True):
            with patch.dict('sys.modules', {'playwright.async_api': mock_playwright_module}):
                # Should not raise, should return partial data
                result = await recon.discover("https://example.com", "Test Vendor")

                assert result is not None
                assert hasattr(result, 'domain')
                assert result.domain == "example.com"
                # Sample products should be empty due to error
                assert hasattr(result, 'sample_products')
                assert len(result.sample_products) == 0


class TestPlaywrightAvailability:
    """Test Playwright availability checking."""

    def test_check_playwright_not_available(self):
        """Test behavior when Playwright is not installed."""
        import core.discovery.site_recon as recon_module

        # Reset global
        recon_module._playwright_available = None

        with patch.dict('sys.modules', {'playwright.async_api': None}):
            with patch('importlib.import_module', side_effect=ImportError):
                available = recon_module._check_playwright()
                assert available is False

    @pytest.mark.asyncio
    async def test_discover_fails_without_playwright(self):
        """Test that discover raises error when Playwright unavailable."""
        recon = SiteReconnaissance()

        with patch('core.discovery.site_recon._check_playwright', return_value=False):
            with pytest.raises(RuntimeError, match="Playwright not available"):
                await recon.discover("https://example.com")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
