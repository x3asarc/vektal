import pytest

from src.core.discovery import (
    LocalPatternMatcher,
    PatternMatchResult,
    validate_sku,
    normalize_sku,
    extract_sku_info,
    infer_size_from_sku
)
from src.core.config.store_profile_schema import StoreProfile, KnownVendor


class TestNormalizeSKU:
    """Test SKU normalization"""

    def test_strips_whitespace(self):
        assert normalize_sku("  R0530  ") == "R0530"

    def test_uppercases(self):
        assert normalize_sku("r0530") == "R0530"

    def test_removes_underscores(self):
        assert normalize_sku("R_0530") == "R0530"

    def test_preserves_hyphens(self):
        # Hyphens may be part of format (P-12345)
        assert normalize_sku("P-12345") == "P-12345"

    def test_empty_string(self):
        assert normalize_sku("") == ""

    def test_none_returns_empty(self):
        assert normalize_sku(None) == ""


class TestValidateSKU:
    """Test SKU validation"""

    def test_valid_sku(self):
        is_valid, errors = validate_sku("R0530")
        assert is_valid
        assert len(errors) == 0

    def test_too_short(self):
        is_valid, errors = validate_sku("R1")
        assert not is_valid
        assert any("too short" in e.lower() for e in errors)

    def test_empty_sku(self):
        is_valid, errors = validate_sku("")
        assert not is_valid
        assert any("empty" in e.lower() for e in errors)

    def test_placeholder_sku(self):
        is_valid, errors = validate_sku("TEST")
        assert not is_valid
        assert any("placeholder" in e.lower() for e in errors)


class TestExtractSKUInfo:
    """Test SKU info extraction"""

    def test_extracts_size_suffix_l(self):
        info = extract_sku_info("R0530L")
        assert info.base_sku == "R0530"
        assert info.size_suffix == "L"
        assert info.product_line == "R"

    def test_no_suffix(self):
        info = extract_sku_info("R0530")
        assert info.base_sku == "R0530"
        assert info.size_suffix is None

    def test_extracts_product_line_rp(self):
        info = extract_sku_info("RP1234")
        assert info.product_line == "RP"

    def test_extracts_product_line_ac(self):
        info = extract_sku_info("AC5678")
        assert info.product_line == "AC"

    def test_normalized_stored(self):
        info = extract_sku_info("  r0530  ")
        assert info.normalized == "R0530"


class TestInferSizeFromSKU:
    """Test size inference"""

    def test_no_suffix_is_a4(self):
        assert infer_size_from_sku("R0530") == "A4"

    def test_l_suffix_is_a3(self):
        assert infer_size_from_sku("R0530L") == "A3"

    def test_xl_suffix_is_a2(self):
        assert infer_size_from_sku("R0530XL") == "A2"

    def test_s_suffix_is_a5(self):
        assert infer_size_from_sku("R0530S") == "A5"

    def test_custom_mappings(self):
        custom = {"": "B5", "L": "B4"}
        assert infer_size_from_sku("R0530", custom) == "B5"
        assert infer_size_from_sku("R0530L", custom) == "B4"


class TestLocalPatternMatcher:
    """Test local pattern matching"""

    def test_matches_itd_pattern(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("R0530")

        assert result.matched is True
        assert result.vendor_name == "ITD Collection"
        assert result.confidence >= 0.90

    def test_matches_itd_with_suffix(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("R0530L")

        assert result.matched is True
        assert result.vendor_name == "ITD Collection"
        assert result.sku_info is not None
        assert result.sku_info.get('size_suffix') == 'L'

    def test_matches_pentart_pattern(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("P-12345")

        assert result.matched is True
        assert result.vendor_name == "Pentart"
        assert result.confidence >= 0.85

    def test_no_match_for_unknown(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("RANDOM123456")

        assert result.matched is False
        assert result.vendor_name is None
        assert result.confidence == 0.0

    def test_invalid_sku_returns_error(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("test")

        assert result.matched is False
        assert "placeholder" in result.message.lower()

    def test_method_is_local_pattern(self):
        matcher = LocalPatternMatcher()
        result = matcher.match("R0530")

        assert result.method == "local_pattern"

    def test_with_store_profile_boosts_confidence(self):
        """Store profile with known vendor boosts confidence"""
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            known_vendors=[
                KnownVendor(
                    name="ITD Collection",
                    sku_pattern=r"^R\d{4}[A-Z]?$",
                    product_count=100
                )
            ]
        )

        matcher = LocalPatternMatcher(store_profile=profile)
        result = matcher.match("R0530")

        assert result.matched is True
        assert result.confidence >= 0.95  # Boosted by store profile

    def test_requires_confirmation_for_medium_confidence(self):
        """Medium confidence requires confirmation"""
        matcher = LocalPatternMatcher()
        # FN Deco has lower base confidence
        result = matcher.match("FN1234")

        if result.matched and result.confidence < 0.90:
            assert result.requires_confirmation is True


class TestPatternMatcherMethods:
    """Test pattern matcher utility methods"""

    def test_list_vendors(self):
        matcher = LocalPatternMatcher()
        vendors = matcher.list_vendors()

        assert 'itd_collection' in vendors
        assert 'pentart' in vendors

    def test_get_vendor_patterns(self):
        matcher = LocalPatternMatcher()
        patterns = matcher.get_vendor_patterns('itd_collection')

        assert len(patterns) > 0
        # Each pattern is (regex, confidence, description)
        assert len(patterns[0]) == 3
