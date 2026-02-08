"""
Tests for dynamic color learning system
"""
import pytest
import tempfile
import json
from pathlib import Path
from src.core.enrichment.color_learning import (
    ColorLearner,
    load_store_colors,
    save_store_colors
)
from src.core.enrichment.extractors.attributes import AttributeExtractor


class TestColorLearner:
    @pytest.fixture
    def sample_products(self):
        """Sample products with various colors"""
        return [
            {
                'title': 'Pentart Acrylfarbe Mintgrün 20ml',
                'variants': [],
                'tags': ''
            },
            {
                'title': 'Reispapier Lavendel A4',
                'variants': [
                    {'title': 'Lavendel', 'option1': 'Lavendel'}
                ],
                'tags': 'purple,lavender'
            },
            {
                'title': 'Serviette Apricot 33x33cm',
                'variants': [],
                'tags': 'apricot,orange'
            },
            {
                'title': 'Farbe Himmelblau 50ml',
                'variants': [],
                'tags': ''
            },
            {
                'title': 'Kleber Transparent 100ml',
                'variants': [],
                'tags': 'clear'
            },
            # Duplicate color (should still be counted once)
            {
                'title': 'Acryl Mintgrün 100ml',
                'variants': [],
                'tags': ''
            }
        ]

    @pytest.fixture
    def learner(self):
        return ColorLearner()

    def test_extract_colors_from_catalog(self, learner, sample_products):
        """Extract colors from catalog"""
        learned = learner.extract_colors_from_catalog(sample_products)

        # Should find new colors (not in base COLOR_MAP)
        assert 'mintgrün' in learned or 'mintgrun' in learned
        assert 'lavendel' in learned
        # Note: 'apricot' is in the color_keywords list, so it's detected
        # 'himmelblau' contains 'blau' so it should be detected
        assert len(learned) >= 2  # At least mintgrün and lavendel

    def test_color_normalization(self, learner):
        """Test color string normalization"""
        assert learner._normalize_color('mintgrün') == 'Mintgrün'
        assert learner._normalize_color('sky-blue') == 'Sky Blue'
        assert learner._normalize_color('PETROL') == 'Petrol'  # Capitalizes

    def test_extract_color_words(self, learner):
        """Extract potential color words from text"""
        colors = learner._extract_color_words('Pentart Acrylfarbe Mintgrün 20ml')
        assert 'mintgrün' in [c.lower() for c in colors] or 'mintgrun' in [c.lower() for c in colors]

    def test_merge_with_base_map(self, learner):
        """Merge learned colors with base COLOR_MAP"""
        learned = {'mintgrün': 'Mint Grün', 'apricot': 'Apricot'}
        combined = learner.merge_with_base_map(learned)

        # Should include base colors
        assert 'rot' in combined
        assert 'blue' in combined

        # Should include learned colors
        assert 'mintgrün' in combined
        assert 'apricot' in combined

    def test_analyze_catalog_colors(self, learner, sample_products):
        """Analyze catalog and return statistics"""
        analysis = learner.analyze_catalog_colors(sample_products)

        assert 'learned_colors' in analysis
        assert 'total_learned' in analysis
        assert 'coverage_increase_percent' in analysis
        assert 'sample_products' in analysis

        assert analysis['total_learned'] > 0
        assert len(analysis['sample_products']) > 0

    def test_minimum_occurrence_threshold(self, learner):
        """Colors appearing only once should be filtered"""
        products = [
            {'title': 'Product with Typocolor', 'variants': [], 'tags': ''}
        ]

        learned = learner.extract_colors_from_catalog(products)

        # Single occurrence should be filtered (min threshold = 2)
        assert 'typocolor' not in learned

    def test_false_positive_filtering(self, learner):
        """Common false positives should be filtered"""
        colors = learner._extract_color_words('Decoupage Papier Vintage Format A4')

        # These should NOT be detected as colors
        assert 'decoupage' not in [c.lower() for c in colors]
        assert 'papier' not in [c.lower() for c in colors]
        assert 'format' not in [c.lower() for c in colors]


class TestStoreColorsPersistence:
    def test_save_and_load_store_colors(self, tmp_path):
        """Save and load colors from store profile"""
        profile_path = tmp_path / 'store_profile.json'

        colors = {
            'mintgrün': 'Mint Grün',
            'apricot': 'Apricot',
            'lavendel': 'Lavendel'
        }

        # Save
        save_store_colors(colors, store_profile_path=str(profile_path))

        # Verify file exists
        assert profile_path.exists()

        # Load
        loaded = load_store_colors(store_profile_path=str(profile_path))

        assert loaded == colors

    def test_load_nonexistent_profile(self):
        """Loading nonexistent profile returns empty dict"""
        colors = load_store_colors(store_profile_path='/nonexistent/path.json')
        assert colors == {}

    def test_merge_with_existing_profile(self, tmp_path):
        """New colors merge with existing profile data"""
        profile_path = tmp_path / 'store_profile.json'

        # Create initial profile
        initial_profile = {
            'store_name': 'Test Store',
            'keywords': ['decoupage', 'craft']
        }

        with open(profile_path, 'w') as f:
            json.dump(initial_profile, f)

        # Save colors (should merge, not overwrite)
        colors = {'mintgrun': 'Mint Grün'}  # Use ASCII version to avoid encoding issues
        save_store_colors(colors, store_profile_path=str(profile_path))

        # Load and verify both old and new data
        with open(profile_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        assert profile['store_name'] == 'Test Store'  # Old data preserved
        assert profile['keywords'] == ['decoupage', 'craft']
        assert profile['colors']['learned'] == colors  # New data added


class TestAttributeExtractorWithDynamicColors:
    def test_extraction_with_learned_colors(self):
        """Extractor uses learned colors"""
        # Create custom color map with learned colors
        from src.core.enrichment.config import COLOR_MAP

        learned = {
            'mintgrün': 'Mint Grün',
            'apricot': 'Apricot'
        }
        combined = {**COLOR_MAP, **learned}

        # Create extractor with combined map
        extractor = AttributeExtractor(custom_color_map=combined)

        # Test extraction
        result = extractor.extract_from_title('Pentart Acrylfarbe Mintgrün 20ml')

        # Should recognize learned color
        assert result['extracted_color'] == 'Mint Grün'

    def test_extraction_without_learned_colors(self):
        """Extractor falls back to capitalization for unknown colors in base map"""
        # Create extractor with only base colors
        extractor = AttributeExtractor()

        # Color keyword that exists in special patterns but not in base COLOR_MAP
        # 'magenta' is in the special color patterns but not in base COLOR_MAP
        result = extractor.extract_from_title('Product Magenta 20ml')

        # Should capitalize unknown color (since magenta matches color pattern but not in base map)
        assert result['extracted_color'] == 'Magenta'

    def test_base_colors_still_work(self):
        """Base colors continue working with custom map"""
        from src.core.enrichment.config import COLOR_MAP

        learned = {'mintgrün': 'Mint Grün'}
        combined = {**COLOR_MAP, **learned}

        extractor = AttributeExtractor(custom_color_map=combined)

        # Test base color
        result = extractor.extract_from_title('Pentart Rot 20ml')
        assert result['extracted_color'] == 'Rot'

        # Test learned color
        result = extractor.extract_from_title('Pentart Mintgrün 20ml')
        assert result['extracted_color'] == 'Mint Grün'
