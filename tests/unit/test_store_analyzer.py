import pytest
from datetime import datetime

from src.core.discovery import StoreProfileAnalyzer
from src.core.discovery.catalog_extractor import (
    extract_keywords, detect_niche, learn_sku_patterns, extract_vendors
)


class TestExtractKeywords:
    """Test keyword extraction"""

    def test_extracts_from_titles(self):
        """Keywords extracted from product titles"""
        products = [
            {'title': 'Reispapier Vintage', 'body_html': ''},
            {'title': 'Reispapier Floral', 'body_html': ''},
            {'title': 'Reispapier Classic', 'body_html': ''},
        ]
        keywords = extract_keywords(products)
        assert 'reispapier' in [k.lower() for k in keywords]

    def test_empty_products_returns_empty(self):
        """Empty product list returns empty keywords"""
        keywords = extract_keywords([])
        assert keywords == []

    def test_respects_top_n(self):
        """Returns at most top_n keywords"""
        products = [
            {'title': 'word1 word2 word3 word4 word5', 'body_html': 'more words'},
        ] * 10
        keywords = extract_keywords(products, top_n=3)
        assert len(keywords) <= 3


class TestDetectNiche:
    """Test niche detection"""

    def test_detects_arts_and_crafts(self):
        """Detects arts_and_crafts niche from craft keywords"""
        products = [
            {'title': 'Decoupage Rice Paper', 'product_type': 'Craft', 'tags': ['decoupage']},
            {'title': 'Acrylic Paint', 'product_type': 'Paint', 'tags': ['craft']},
            {'title': 'Scrapbooking Paper', 'product_type': 'Paper', 'tags': ['scrapbooking']},
        ]
        niche, confidence, _ = detect_niche(products)
        assert niche == 'arts_and_crafts'
        assert confidence > 0.5

    def test_returns_other_for_unknown(self):
        """Returns 'other' for unrecognized products"""
        products = [
            {'title': 'Random Product XYZ', 'product_type': '', 'tags': []},
        ]
        niche, confidence, _ = detect_niche(products)
        assert niche in ['other', 'unknown']
        assert confidence < 0.5

    def test_empty_products(self):
        """Handles empty product list"""
        niche, confidence, _ = detect_niche([])
        assert niche == 'unknown'
        assert confidence == 0.0


class TestLearnSKUPatterns:
    """Test SKU pattern learning"""

    def test_learns_letter_digit_pattern(self):
        """Learns R#### pattern from SKUs"""
        products = [
            {'vendor': 'ITD', 'variants': [{'sku': 'R0530'}]},
            {'vendor': 'ITD', 'variants': [{'sku': 'R0531'}]},
            {'vendor': 'ITD', 'variants': [{'sku': 'R0532'}]},
            {'vendor': 'ITD', 'variants': [{'sku': 'R0533'}]},
            {'vendor': 'ITD', 'variants': [{'sku': 'R0534'}]},
            {'vendor': 'ITD', 'variants': [{'sku': 'R0535'}]},
        ]
        patterns = learn_sku_patterns(products, min_occurrences=5)
        assert len(patterns) > 0
        # Should find a pattern matching R####
        found_pattern = any('R' in p.get('examples', [''])[0] for p in patterns.values())
        assert found_pattern

    def test_empty_products(self):
        """Handles empty product list"""
        patterns = learn_sku_patterns([])
        assert patterns == {}


class TestExtractVendors:
    """Test vendor extraction"""

    def test_extracts_vendors(self):
        """Extracts vendors with product counts"""
        products = [
            {'vendor': 'ITD Collection', 'variants': [{'sku': 'R0530'}]},
            {'vendor': 'ITD Collection', 'variants': [{'sku': 'R0531'}]},
            {'vendor': 'Pentart', 'variants': [{'sku': 'P123'}]},
        ]
        vendors = extract_vendors(products)
        assert len(vendors) == 2
        assert vendors[0]['name'] == 'ITD Collection'  # Sorted by count
        assert vendors[0]['product_count'] == 2

    def test_collects_sample_skus(self):
        """Collects sample SKUs for each vendor"""
        products = [
            {'vendor': 'Test', 'variants': [{'sku': 'T001'}]},
            {'vendor': 'Test', 'variants': [{'sku': 'T002'}]},
        ]
        vendors = extract_vendors(products)
        assert 'T001' in vendors[0]['sample_skus']


class TestStoreProfileAnalyzer:
    """Test StoreProfileAnalyzer class"""

    def test_high_confidence_catalog(self):
        """50+ products gives high confidence"""
        products = [
            {
                'title': f'Reispapier {i}',
                'body_html': 'Decoupage paper',
                'vendor': 'ITD Collection',
                'product_type': 'Reispapier',
                'tags': ['decoupage'],
                'variants': [{'sku': f'R{1000+i}'}]
            }
            for i in range(60)
        ]

        analyzer = StoreProfileAnalyzer(store_id='test.myshopify.com')
        profile = analyzer.analyze(products)

        assert profile.vendor_scope == 'focused'
        assert profile.niche_confidence > 0.5
        assert profile.content_framework is not None
        assert len(profile.known_vendors) > 0

    def test_low_confidence_catalog(self):
        """<10 products gives low confidence"""
        products = [
            {
                'title': 'Product 1',
                'body_html': '',
                'vendor': 'Test',
                'variants': [{'sku': 'T001'}]
            }
        ]

        analyzer = StoreProfileAnalyzer(store_id='test.myshopify.com')
        profile = analyzer.analyze(products)

        assert profile.vendor_scope == 'flexible'
        assert profile.content_framework is None

    def test_needs_questionnaire(self):
        """Check questionnaire requirement"""
        analyzer = StoreProfileAnalyzer(store_id='test.myshopify.com')

        assert analyzer.needs_questionnaire(5) is True
        assert analyzer.needs_questionnaire(30) is True
        assert analyzer.needs_questionnaire(60) is False

    def test_confidence_levels(self):
        """Check confidence level thresholds"""
        analyzer = StoreProfileAnalyzer(store_id='test.myshopify.com')

        assert analyzer.get_confidence_level(5) == 'low'
        assert analyzer.get_confidence_level(10) == 'medium'
        assert analyzer.get_confidence_level(50) == 'high'
        assert analyzer.get_confidence_level(100) == 'high'
