import pytest
from pathlib import Path

from src.core.config import (
    VendorConfigGenerator,
    SiteReconData,
    GeneratedConfig,
    ConfigVerifier,
    CheckResult,
    VerificationResult
)


class TestSiteReconData:
    """Test SiteReconData dataclass"""

    def test_minimal_recon(self):
        recon = SiteReconData(
            domain="test.com",
            vendor_name="Test Vendor",
            detected_niche="other"
        )
        assert recon.domain == "test.com"
        assert recon.requires_javascript is True  # Default

    def test_full_recon(self):
        recon = SiteReconData(
            domain="itdcollection.com",
            vendor_name="ITD Collection",
            detected_niche="arts_and_crafts",
            sku_patterns=[{"name": "primary", "regex": r"^R\d+$", "examples": ["R0530"]}],
            url_patterns={"product_template": "https://itd.com/p/{sku}"},
            requires_javascript=True,
            has_lazy_loading=True,
            has_collection_pages=["https://itd.com/collections/a4"]
        )
        assert len(recon.sku_patterns) == 1
        assert recon.has_lazy_loading


class TestVendorConfigGenerator:
    """Test VendorConfigGenerator"""

    def test_generates_config(self):
        generator = VendorConfigGenerator(output_dir="/tmp/test_vendors")

        recon = SiteReconData(
            domain="example.com",
            vendor_name="Example Vendor",
            detected_niche="arts_and_crafts"
        )

        result = generator.generate(recon)

        assert isinstance(result, GeneratedConfig)
        assert result.config.vendor.name == "Example Vendor"
        assert result.config.vendor.slug == "example_vendor"

    def test_generates_slug(self):
        generator = VendorConfigGenerator()

        assert generator._to_slug("ITD Collection") == "itd_collection"
        assert generator._to_slug("Test-Vendor") == "test_vendor"
        assert generator._to_slug("UPPERCASE") == "uppercase"

    def test_generates_short_name(self):
        generator = VendorConfigGenerator()

        assert generator._to_short_name("ITD Collection") == "IC"
        assert generator._to_short_name("Pentart") == "PEN"
        assert generator._to_short_name("A B C") == "ABC"

    def test_sku_patterns_included(self):
        generator = VendorConfigGenerator()

        recon = SiteReconData(
            domain="test.com",
            vendor_name="Test",
            detected_niche="other",
            sku_patterns=[
                {"name": "main", "regex": r"^T\d{4}$", "examples": ["T1234"]}
            ]
        )

        result = generator.generate(recon)

        assert len(result.config.sku_patterns) == 1
        assert result.config.sku_patterns[0].regex == r"^T\d{4}$"

    def test_default_sku_pattern_when_none(self):
        generator = VendorConfigGenerator()

        recon = SiteReconData(
            domain="test.com",
            vendor_name="Test",
            detected_niche="other",
            sku_patterns=[]  # No patterns
        )

        result = generator.generate(recon)

        assert len(result.config.sku_patterns) == 1
        assert "generic" in result.warnings[0].lower()

    def test_confidence_scoring(self):
        generator = VendorConfigGenerator()

        # Full recon data should have higher confidence
        full_recon = SiteReconData(
            domain="test.com",
            vendor_name="Test",
            detected_niche="arts_and_crafts",
            sku_patterns=[{"name": "main", "regex": r"^T\d+$", "examples": ["T1"]}],
            url_patterns={"product_template": "https://test.com/p/{sku}"},
            has_collection_pages=["https://test.com/all"],
            sample_products=[{"sku": "T1"}]
        )

        # Minimal recon data should have lower confidence
        minimal_recon = SiteReconData(
            domain="test.com",
            vendor_name="Test",
            detected_niche="other"
        )

        full_result = generator.generate(full_recon)
        minimal_result = generator.generate(minimal_recon)

        assert full_result.confidence > minimal_result.confidence

    def test_needs_verification_flag(self):
        generator = VendorConfigGenerator()

        # Low confidence config needs verification
        recon = SiteReconData(
            domain="test.com",
            vendor_name="Test",
            detected_niche="other"
        )

        result = generator.generate(recon)
        assert result.needs_verification


class TestConfigVerifier:
    """Test ConfigVerifier"""

    def test_verify_sku_patterns_valid(self):
        verifier = ConfigVerifier()

        # Create a mock config with valid patterns
        from src.core.config.vendor_schema import VendorConfig, SKUPattern, VendorIdentity, VendorNiche

        config = VendorConfig(
            vendor=VendorIdentity(
                name="Test",
                name_short="T",
                slug="test",
                domain="test.com"
            ),
            niche=VendorNiche(primary="other"),
            sku_patterns=[
                SKUPattern(
                    name="main",
                    regex=r"^T\d{4}$",
                    description="Test",
                    examples=["T1234", "T5678"]
                )
            ],
            urls={"product": {"template": "https://test.com/p/{sku}"}},
            selectors={"images": {"container": ".gallery", "items": "img"}}
        )

        result = verifier._verify_sku_patterns(config)

        assert result.status == 'passed'
        assert result.passed > 0

    def test_verify_sku_patterns_invalid_regex(self):
        """Test that invalid regex is caught by Pydantic validator"""
        from src.core.config.vendor_schema import SKUPattern
        import pytest

        # Pydantic should catch invalid regex at initialization
        with pytest.raises(Exception):
            SKUPattern(
                name="main",
                regex=r"^[invalid(",  # Invalid regex
                description="Test",
                examples=[]
            )

    def test_verify_urls_with_placeholder(self):
        verifier = ConfigVerifier()

        from src.core.config.vendor_schema import VendorConfig, VendorIdentity, VendorNiche, SKUPattern

        config = VendorConfig(
            vendor=VendorIdentity(
                name="Test",
                name_short="T",
                slug="test",
                domain="test.com"
            ),
            niche=VendorNiche(primary="other"),
            sku_patterns=[SKUPattern(name="test", regex=r"^T\d+$", description="Test")],
            urls={
                "product": {"template": "https://test.com/p/{sku_lower}"}
            },
            selectors={"images": {"container": ".gallery", "items": "img"}}
        )

        result = verifier._verify_urls(config)

        assert result.status == 'passed'

    def test_verify_urls_missing_placeholder(self):
        """Test that URLs without placeholder are caught by Pydantic validator"""
        from src.core.config.vendor_schema import VendorConfig, VendorIdentity, VendorNiche, SKUPattern
        import pytest

        # Pydantic should catch missing placeholder at initialization
        with pytest.raises(Exception):
            config = VendorConfig(
                vendor=VendorIdentity(
                    name="Test",
                    name_short="T",
                    slug="test",
                    domain="test.com"
                ),
                niche=VendorNiche(primary="other"),
                sku_patterns=[SKUPattern(name="test", regex=r"^T\d+$", description="Test")],
                urls={
                    "product": {"template": "https://test.com/static-url"}
                },
                selectors={"images": {"container": ".gallery", "items": "img"}}
            )

    def test_css_selector_validation(self):
        verifier = ConfigVerifier()

        # Valid selectors
        assert verifier._is_valid_css_selector('.product-title')
        assert verifier._is_valid_css_selector('#main')
        assert verifier._is_valid_css_selector('[data-sku]')
        assert verifier._is_valid_css_selector('h1.title')

        # Invalid selectors
        assert not verifier._is_valid_css_selector('')
        assert not verifier._is_valid_css_selector('<script>')
        assert not verifier._is_valid_css_selector('{{variable}}')

    def test_integration_generator_and_verifier(self):
        """Test full verification flow using generator output"""
        generator = VendorConfigGenerator()
        verifier = ConfigVerifier()

        recon = SiteReconData(
            domain="itdcollection.com",
            vendor_name="ITD Collection",
            detected_niche="arts_and_crafts",
            sku_patterns=[
                {"name": "rice", "regex": r"^R\d{4}[A-Z]?$", "examples": ["R0530"]}
            ],
            url_patterns={"product_template": "https://itd.com/p/{sku_lower}"}
        )

        # Generate config
        generated = generator.generate(recon)
        assert isinstance(generated, GeneratedConfig)
        assert generated.config.vendor.name == "ITD Collection"

        # Verify using synchronous methods (async verify tested separately)
        sku_check = verifier._verify_sku_patterns(generated.config)
        assert sku_check.status == 'passed'

        url_check = verifier._verify_urls(generated.config)
        assert url_check.status == 'passed'
