"""
Shared pytest fixtures for all tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Ensure both project root and src/ are importable
# This supports both "from src.core..." and "from core..." imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))


@pytest.fixture
def mock_shopify_client():
    """Mock Shopify client for testing."""
    client = MagicMock()
    client.resolve_product.return_value = {
        "id": "gid://shopify/Product/123",
        "title": "Test Product",
        "handle": "test-product",
        "vendor": "Test Vendor"
    }
    return client


@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary directory for test data."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_resolver():
    """Mock ShopifyResolver for testing."""
    resolver = MagicMock()
    resolver.shop_domain = "test-shop.myshopify.com"
    resolver.api_version = "2024-01"
    resolver.resolve_identifier.return_value = {
        "matches": [{
            "id": "gid://shopify/Product/123",
            "title": "Test Product",
            "handle": "test-product",
            "vendor": "Test Vendor",
            "primary_variant": {
                "sku": "TEST-SKU",
                "barcode": "123456789"
            }
        }]
    }
    return resolver


@pytest.fixture
def sample_product():
    """Sample product data for testing."""
    return {
        "id": "gid://shopify/Product/123",
        "title": "Galaxy Flakes 15g",
        "handle": "galaxy-flakes-15g",
        "vendor": "Pentart",
        "primary_variant": {
            "id": "gid://shopify/ProductVariant/456",
            "sku": "PENT-GF-15",
            "barcode": "5998858704901",
            "price": "4.99",
            "weight": 15,
            "weight_unit": "g"
        },
        "images": [{
            "id": "gid://shopify/ProductImage/789",
            "src": "https://example.com/image.jpg",
            "alt": "Galaxy Flakes product photo"
        }]
    }
