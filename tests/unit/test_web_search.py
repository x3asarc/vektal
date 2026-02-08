import pytest
from unittest.mock import Mock, patch

from src.core.discovery import (
    WebSearchClient,
    SearchResult,
    WebSearchResponse,
    validate_niche_match,
    detect_niche_from_text,
    NicheValidationResult
)
from src.core.config.store_profile_schema import StoreProfile, KnownVendor


class TestNicheDetection:
    """Test niche detection from text"""

    def test_detects_arts_and_crafts(self):
        text = "Beautiful decoupage rice paper for craft projects"
        niche, conf, keywords = detect_niche_from_text(text)
        assert niche == "arts_and_crafts"
        assert conf > 0.5
        assert any(k in keywords for k in ["decoupage", "craft"])

    def test_detects_automotive(self):
        text = "Oil filter for Honda Civic engine replacement"
        niche, conf, keywords = detect_niche_from_text(text)
        assert niche == "automotive"
        assert any(k in keywords for k in ["oil", "filter", "engine"])

    def test_returns_none_for_unknown(self):
        text = "Random product XYZ 12345"
        niche, conf, keywords = detect_niche_from_text(text)
        assert niche is None or conf < 0.3


class TestNicheValidation:
    """Test niche compatibility validation"""

    def test_same_niche_compatible(self):
        result = validate_niche_match("arts_and_crafts", "arts_and_crafts")
        assert result.is_compatible
        assert result.confidence_modifier == 1.0

    def test_incompatible_niche_strict_mode(self):
        result = validate_niche_match(
            "arts_and_crafts",
            "automotive",
            strict_mode=True
        )
        assert not result.is_compatible
        assert result.confidence_modifier == 0.0
        assert "MISMATCH" in result.message

    def test_incompatible_niche_flexible_mode(self):
        result = validate_niche_match(
            "arts_and_crafts",
            "automotive",
            strict_mode=False
        )
        assert not result.is_compatible
        assert result.confidence_modifier == 0.2
        assert "confirmation" in result.message.lower()

    def test_related_niche(self):
        result = validate_niche_match(
            "arts_and_crafts",
            "home_garden"
        )
        assert result.is_compatible
        assert result.confidence_modifier == 0.9

    def test_unknown_vendor_niche(self):
        result = validate_niche_match(
            "arts_and_crafts",
            vendor_niche=None,
            vendor_text=""
        )
        assert result.is_compatible  # Allowed but penalized
        assert result.confidence_modifier == 0.7


class TestQueryBuilding:
    """Test context-aware query building"""

    def test_query_with_store_profile(self):
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            keywords=["decoupage", "rice paper", "craft"],
            known_vendors=[KnownVendor(name="ITD Collection")]
        )

        client = WebSearchClient(store_profile=profile)
        query = client.build_context_query("R0530")

        assert "R0530" in query
        assert "decoupage" in query
        assert "ITD Collection" in query

    def test_query_without_profile(self):
        client = WebSearchClient()
        query = client.build_context_query("R0530")

        assert query == "R0530"

    def test_query_limits_keywords(self):
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            keywords=["a", "b", "c", "d", "e", "f"],  # 6 keywords
            known_vendors=[]
        )

        client = WebSearchClient(store_profile=profile)
        query = client.build_context_query("SKU123")

        # Should only include top 3 keywords
        words = query.split()
        assert len(words) <= 4  # SKU + 3 keywords


class TestSearchResultParsing:
    """Test search result parsing and analysis"""

    def test_search_result_dataclass(self):
        result = SearchResult(
            title="ITD Collection Rice Paper",
            url="https://itdcollection.com/products/r0530",
            snippet="Beautiful rice paper for decoupage",
            position=1,
            detected_vendor="ITD Collection",
            detected_niche="arts_and_crafts"
        )

        assert result.title == "ITD Collection Rice Paper"
        assert result.detected_vendor == "ITD Collection"

    def test_web_search_response(self):
        results = [
            SearchResult(
                title="Result 1",
                url="https://vendor1.com",
                snippet="",
                position=1,
                detected_vendor="Vendor A"
            ),
            SearchResult(
                title="Result 2",
                url="https://vendor1.com",
                snippet="",
                position=2,
                detected_vendor="Vendor A"
            ),
            SearchResult(
                title="Result 3",
                url="https://vendor2.com",
                snippet="",
                position=3,
                detected_vendor="Vendor B"
            ),
        ]

        response = WebSearchResponse(
            query="test",
            results=results,
            vendor_counts={"Vendor A": 2, "Vendor B": 1},
            top_vendor="Vendor A",
            top_vendor_confidence=0.67
        )

        assert response.top_vendor == "Vendor A"
        assert response.vendor_counts["Vendor A"] == 2


class TestVendorExtraction:
    """Test vendor name extraction from results"""

    def test_extract_known_vendor(self):
        client = WebSearchClient()
        vendor = client._extract_vendor_name(
            "ITD Collection Rice Paper R0530",
            "https://itdcollection.com/products/r0530"
        )
        assert vendor == "ITD Collection"

    def test_extract_from_domain(self):
        client = WebSearchClient()
        vendor = client._extract_vendor_name(
            "Some Product Title",
            "https://example-vendor.com/product"
        )
        assert vendor == "Example Vendor"


class TestNicheAppliedToConfidence:
    """Test that niche validation affects confidence"""

    def test_incompatible_niche_zeros_confidence(self):
        # Create a focused arts store profile
        profile = StoreProfile(
            store_id="test.myshopify.com",
            niche_primary="arts_and_crafts",
            vendor_scope="focused",
            keywords=["decoupage"],
            known_vendors=[]
        )

        response = WebSearchResponse(
            query="test",
            results=[],
            top_vendor="Some Auto Parts",
            top_vendor_confidence=0.90
        )

        # Simulate niche validation being applied
        niche_result = validate_niche_match(
            profile.niche_primary,
            "automotive",
            strict_mode=True
        )

        # Apply modifier
        final_confidence = response.top_vendor_confidence * niche_result.confidence_modifier
        assert final_confidence == 0.0  # Should be zeroed out
