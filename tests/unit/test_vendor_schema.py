"""
Unit tests for vendor schema validation.

Tests SKU pattern validation, URL template validation, and full vendor config
roundtrip through save/load cycle.
"""

import pytest
import re
from pathlib import Path
import tempfile
import yaml
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config.vendor_schema import (
    VendorConfig, SKUPattern, VendorURLs, VendorIdentity,
    VendorNiche, ScrapingConfig, Selectors
)
from src.core.config.store_profile_schema import StoreProfile, KnownVendor
from src.core.config import load_vendor_config, save_vendor_config


class TestSKUPattern:
    """Test SKU pattern validation."""

    def test_valid_regex_pattern(self):
        """Valid regex compiles successfully."""
        pattern = SKUPattern(
            name="standard",
            regex=r"^R\d{4}[A-Z]?$",
            description="ITD rice paper",
            examples=["R0530", "R0530L"]
        )
        assert pattern.regex == r"^R\d{4}[A-Z]?$"

    def test_invalid_regex_raises_error(self):
        """Invalid regex raises ValueError."""
        with pytest.raises(ValueError, match="Invalid regex"):
            SKUPattern(
                name="bad",
                regex=r"[invalid(",  # Unclosed bracket
                description="Bad pattern",
                examples=[]
            )

    def test_pattern_matches_examples(self):
        """Pattern should match its own examples."""
        pattern = SKUPattern(
            name="test",
            regex=r"^R\d{4}[A-Z]?$",
            description="Test",
            examples=["R0530", "R1234L"]
        )
        compiled = re.compile(pattern.regex)
        for example in pattern.examples:
            assert compiled.match(example), f"Pattern should match example: {example}"


class TestVendorURLs:
    """Test URL template validation."""

    def test_valid_product_template(self):
        """Product URL with {sku} placeholder is valid."""
        urls = VendorURLs(
            product={"template": "https://example.com/products/{sku_lower}"}
        )
        assert "{sku" in urls.product["template"]

    def test_product_template_requires_sku_placeholder(self):
        """Product URL without {sku} placeholder raises error."""
        with pytest.raises(ValueError):
            VendorURLs(
                product={"template": "https://example.com/products/static"}
            )


class TestVendorIdentity:
    """Test vendor identity fields."""

    def test_vendor_identity_fields(self):
        """Vendor identity has required fields."""
        vendor = VendorIdentity(
            name="ITD Collection",
            name_short="ITD",
            slug="itd_collection",
            domain="itdcollection.com"
        )
        assert vendor.name == "ITD Collection"
        assert vendor.slug == "itd_collection"
        assert vendor.domain == "itdcollection.com"


class TestStoreProfile:
    """Test store profile validation."""

    def test_minimal_store_profile(self):
        """Store profile with minimal fields."""
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts"
        )
        assert profile.vendor_scope == "focused"
        assert profile.language == "de"

    def test_known_vendors(self):
        """Store profile with known vendors."""
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            known_vendors=[
                KnownVendor(name="ITD Collection", sku_pattern=r"^R\d{4}$"),
                KnownVendor(name="Pentart")
            ]
        )
        assert len(profile.known_vendors) == 2
        assert profile.known_vendors[0].name == "ITD Collection"


class TestVendorConfigIntegration:
    """Integration tests for full vendor config."""

    def test_save_and_load_roundtrip(self):
        """Save and load vendor config preserves data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create minimal valid config
            config = VendorConfig(
                vendor=VendorIdentity(
                    name="Test Vendor",
                    name_short="Test",
                    slug="test_vendor",
                    domain="test.com"
                ),
                niche=VendorNiche(primary="arts_and_crafts"),
                sku_patterns=[
                    SKUPattern(
                        name="standard",
                        regex=r"^T\d{4}$",
                        description="Test pattern",
                        examples=["T1234"]
                    )
                ],
                urls=VendorURLs(
                    product={"template": "https://test.com/p/{sku}"}
                ),
                selectors=Selectors(
                    images={"container": ".gallery", "items": "img"}
                )
            )

            # Save
            yaml_path = tmp_path / "test_vendor.yaml"
            save_vendor_config(config, yaml_path)

            # Load
            loaded = load_vendor_config(yaml_path)

            assert loaded.vendor.name == "Test Vendor"
            assert loaded.sku_patterns[0].regex == r"^T\d{4}$"

    def test_minimal_vendor_config(self):
        """Minimal vendor config with required fields only."""
        config = VendorConfig(
            vendor=VendorIdentity(
                name="Minimal Vendor",
                name_short="Min",
                slug="minimal",
                domain="minimal.com"
            ),
            niche=VendorNiche(primary="electronics"),
            sku_patterns=[
                SKUPattern(
                    name="basic",
                    regex=r"^[A-Z]{2}\d{3}$",
                    description="Basic pattern",
                    examples=["AB123"]
                )
            ],
            urls=VendorURLs(
                product={"template": "https://minimal.com/{sku}"}
            ),
            selectors=Selectors(
                images={"container": "div.images", "items": "img"}
            )
        )

        assert config.vendor.name == "Minimal Vendor"
        assert len(config.sku_patterns) == 1


class TestNicheValidation:
    """Test niche-related validation."""

    def test_valid_niches(self):
        """Valid niche values accepted."""
        valid_niches = [
            "arts_and_crafts", "automotive", "electronics",
            "fashion", "food_beverage", "health_beauty"
        ]
        for niche in valid_niches:
            n = VendorNiche(primary=niche)
            assert n.primary == niche

    def test_sub_categories(self):
        """Sub-categories stored correctly."""
        niche = VendorNiche(
            primary="arts_and_crafts",
            sub_categories=["decoupage", "scrapbooking"]
        )
        assert "decoupage" in niche.sub_categories
        assert "scrapbooking" in niche.sub_categories


class TestVendorConfigValidation:
    """Test vendor config validation rules."""

    def test_at_least_one_sku_pattern_required(self):
        """Config requires at least one SKU pattern."""
        with pytest.raises(ValueError, match="At least one SKU pattern is required"):
            VendorConfig(
                vendor=VendorIdentity(
                    name="Test",
                    name_short="T",
                    slug="test",
                    domain="test.com"
                ),
                niche=VendorNiche(primary="general"),
                sku_patterns=[],  # Empty list should fail
                urls=VendorURLs(
                    product={"template": "https://test.com/{sku}"}
                ),
                selectors=Selectors(
                    images={"container": ".img", "items": "img"}
                )
            )


class TestScrapingConfig:
    """Test scraping configuration."""

    def test_default_scraping_config(self):
        """Scraping config has sensible defaults."""
        from src.core.config.vendor_schema import StrategyConfig

        config = ScrapingConfig(
            strategy=StrategyConfig(primary="playwright")
        )

        assert config.strategy.primary == "playwright"
        assert config.strategy.discovery == "firecrawl"
        assert config.browser.headless is True
        assert config.timing.page_load_wait_ms == 3000
        assert config.rate_limits.delay_between_requests_ms == 3000
        assert config.retry.max_attempts == 4


class TestSelectors:
    """Test CSS selector configuration."""

    def test_minimal_selectors(self):
        """Minimal selector config with images only."""
        selectors = Selectors(
            images={"container": ".gallery", "items": "img"}
        )

        assert selectors.images["container"] == ".gallery"
        assert selectors.images["items"] == "img"

    def test_full_selectors(self):
        """Full selector config with all fields."""
        selectors = Selectors(
            images={"container": ".images", "items": "img"},
            title={"selector": "h1.product-title"},
            price={"selector": ".price"},
            description={"selector": ".description", "extract_as": "html"},
            sku={"selector": ".sku"}
        )

        assert selectors.title["selector"] == "h1.product-title"
        assert selectors.price["selector"] == ".price"
