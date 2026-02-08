"""
Unit tests for AttributeExtractor

Tests German and English attribute extraction from product titles and descriptions.
"""
import pytest
from src.core.enrichment.extractors.attributes import AttributeExtractor


@pytest.fixture
def extractor():
    """Create AttributeExtractor instance for tests"""
    return AttributeExtractor()


class TestColorExtraction:
    """Test color extraction from titles"""

    def test_german_color_rot(self, extractor):
        """Extract German color 'rot'"""
        result = extractor.extract_from_title("Acrylfarbe Rot 50ml")
        assert result['extracted_color'] == 'Rot'

    def test_german_color_gruen_with_umlaut(self, extractor):
        """Extract German color with umlaut"""
        result = extractor.extract_from_title("Textilfarbe Grün 100ml")
        assert result['extracted_color'] == 'Grün'

    def test_english_color_red(self, extractor):
        """Extract English color"""
        result = extractor.extract_from_title("Acrylic Paint Red 20ml")
        assert result['extracted_color'] == 'Rot'

    def test_special_color_jade(self, extractor):
        """Extract special colors like jade, ruby"""
        result = extractor.extract_from_title("Pentart Acrylfarbe Jade 20ml")
        assert result['extracted_color'] == 'Jade Grün'

    def test_special_color_ruby(self, extractor):
        """Extract ruby color"""
        result = extractor.extract_from_title("Ruby Paint 100ml")
        assert result['extracted_color'] == 'Ruby Rot'

    def test_no_color_in_title(self, extractor):
        """Return None when no color present"""
        result = extractor.extract_from_title("Pinsel Set 10 Stück")
        assert result['extracted_color'] is None


class TestSizeExtraction:
    """Test size and unit extraction from titles"""

    def test_ml_size(self, extractor):
        """Extract milliliter sizes (20ml, 100ml)"""
        result = extractor.extract_from_title("Acrylfarbe Rot 20ml")
        assert result['extracted_size'] == '20'
        assert result['extracted_unit'] == 'ml'

    def test_gram_size(self, extractor):
        """Extract gram sizes (50g, 100g)"""
        result = extractor.extract_from_title("Glitter Gold 50g")
        assert result['extracted_size'] == '50'
        assert result['extracted_unit'] == 'g'

    def test_dimension_size(self, extractor):
        """Extract dimensions (14x14cm, 10x15cm)"""
        result = extractor.extract_from_title("Serviette 14x14cm Blumen")
        assert result['extracted_size'] == '14x14'
        assert result['extracted_unit'] == 'cm'

    def test_paper_format(self, extractor):
        """Extract paper formats (A4, A3)"""
        result = extractor.extract_from_title("Cardstock A4 Weiß 50 Blatt")
        assert result['extracted_size'] == 'A4'
        assert result['extracted_unit'] == 'format'

    def test_decimal_size(self, extractor):
        """Extract decimal sizes with comma"""
        result = extractor.extract_from_title("Epoxidharz 0,5l Transparent")
        assert result['extracted_size'] == '0.5'
        assert result['extracted_unit'] == 'l'

    def test_piece_count(self, extractor):
        """Extract piece counts"""
        result = extractor.extract_from_title("Pinsel Set 10 Stück")
        assert result['extracted_size'] == '10'
        assert result['extracted_unit'] == 'stück'


class TestMaterialExtraction:
    """Test material detection from titles"""

    def test_acryl_material(self, extractor):
        """Extract Acryl/Acrylfarbe"""
        result = extractor.extract_from_title("Acrylfarbe Rot 20ml")
        assert result['extracted_material'] == 'Acryl'

    def test_textil_material(self, extractor):
        """Extract Textil/Textilfarbe"""
        result = extractor.extract_from_title("Textilfarbe Blau 50ml")
        assert result['extracted_material'] == 'Textil'

    def test_harz_material(self, extractor):
        """Extract Harz/Epoxid"""
        result = extractor.extract_from_title("Epoxidharz Transparent 500ml")
        assert result['extracted_material'] == 'Harz'

    def test_oel_material(self, extractor):
        """Extract Öl/Ölfarbe"""
        result = extractor.extract_from_title("Ölfarbe Schwarz 100ml")
        assert result['extracted_material'] == 'Öl'

    def test_papier_material(self, extractor):
        """Extract Papier"""
        result = extractor.extract_from_title("Papier A4 Weiß")
        assert result['extracted_material'] == 'Papier'


class TestCategoryInference:
    """Test category inference from keywords"""

    def test_infer_farbe_category(self, extractor):
        """Infer Farbe category from paint keywords"""
        result = extractor.extract_from_title("Acrylfarbe Rot 20ml")
        assert result['inferred_category'] == 'Farbe'

    def test_infer_papier_category(self, extractor):
        """Infer Papier category from paper keywords"""
        result = extractor.extract_from_title("Cardstock A4 Weiß")
        assert result['inferred_category'] == 'Papier'

    def test_infer_harz_category(self, extractor):
        """Infer Harz category from resin keywords"""
        result = extractor.extract_from_title("Epoxidharz Transparent")
        assert result['inferred_category'] == 'Harz'

    def test_infer_werkzeug_category(self, extractor):
        """Infer Werkzeug category from tool keywords"""
        result = extractor.extract_from_title("Pinsel Set 10 Stück")
        assert result['inferred_category'] == 'Werkzeug'

    def test_no_category_inference(self, extractor):
        """Return None when no category matches"""
        result = extractor.extract_from_title("Some Random Product")
        assert result['inferred_category'] is None


class TestDescriptionExtraction:
    """Test extraction from product descriptions"""

    def test_use_case_decoupage(self, extractor):
        """Extract Decoupage use case"""
        desc = "Perfekt für Serviettentechnik und Decoupage-Projekte"
        result = extractor.extract_from_description(desc)
        assert 'Decoupage' in result['extracted_use_cases']

    def test_use_case_resin_art(self, extractor):
        """Extract Resin-Art use case"""
        desc = "Ideal zum Giessen von Harz und Resin-Art"
        result = extractor.extract_from_description(desc)
        assert 'Resin-Art' in result['extracted_use_cases']

    def test_waterproof_feature(self, extractor):
        """Detect waterproof feature"""
        desc = "Wasserfest nach dem Trocknen"
        result = extractor.extract_from_description(desc)
        assert result['is_waterproof'] is True

    def test_washable_feature(self, extractor):
        """Detect washable feature"""
        desc = "Waschbar bei 30°C"
        result = extractor.extract_from_description(desc)
        assert result['is_washable'] is True

    def test_non_toxic_feature(self, extractor):
        """Detect non-toxic feature"""
        desc = "Ungiftig und kindersicher"
        result = extractor.extract_from_description(desc)
        assert result['is_non_toxic'] is True

    def test_empty_description(self, extractor):
        """Handle empty description gracefully"""
        result = extractor.extract_from_description("")
        assert result['extracted_use_cases'] == []
        assert result['is_waterproof'] is False


class TestQualityScore:
    """Test quality score calculation"""

    def test_high_quality_product(self, extractor):
        """Product with all fields scores 85+"""
        product = {
            'description': 'A' * 150,  # >100 chars = 40 points
            'extracted_color': 'Rot',  # +10
            'extracted_size': '20',    # +10
            'extracted_material': 'Acryl',  # +10
            'inferred_category': 'Farbe',   # +10
            'product_type': 'Acrylfarbe',   # +10
            'tags': 'farbe, rot, basteln'   # +10
        }
        score = extractor.calculate_quality_score(product)
        assert score >= 85

    def test_low_quality_product(self, extractor):
        """Product with missing fields scores <50"""
        product = {
            'description': 'Short',  # <20 chars = 0 points
            'product_type': '',
            'tags': ''
        }
        score = extractor.calculate_quality_score(product)
        assert score < 50

    def test_score_bounds(self, extractor):
        """Score always 0-100"""
        # Minimal product
        product_min = {}
        score_min = extractor.calculate_quality_score(product_min)
        assert 0 <= score_min <= 100

        # Maximal product
        product_max = {
            'description': 'A' * 200,
            'extracted_color': 'Rot',
            'extracted_size': '20',
            'extracted_material': 'Acryl',
            'inferred_category': 'Farbe',
            'product_type': 'Acrylfarbe',
            'tags': 'farbe, rot, basteln'
        }
        score_max = extractor.calculate_quality_score(product_max)
        assert 0 <= score_max <= 100

    def test_medium_quality_product(self, extractor):
        """Product with some fields scores in middle range"""
        product = {
            'description': 'A' * 60,  # >50 chars = 30 points
            'extracted_color': 'Rot',  # +10
            'inferred_category': 'Farbe'  # +10
        }
        score = extractor.calculate_quality_score(product)
        assert 40 <= score <= 60


class TestExtractAll:
    """Test combined extraction from title and description"""

    def test_extract_all_combines_sources(self, extractor):
        """extract_all combines title and description extraction"""
        title = "Pentart Acrylfarbe Jade 20ml"
        desc = "Wasserfest und perfekt für Decoupage"
        result = extractor.extract_all(title, desc)

        # From title
        assert result['extracted_color'] == 'Jade Grün'
        assert result['extracted_size'] == '20'
        assert result['extracted_material'] == 'Acryl'

        # From description
        assert result['is_waterproof'] is True
        assert 'Decoupage' in result['extracted_use_cases']

    def test_extract_all_with_empty_description(self, extractor):
        """extract_all works with empty description"""
        title = "Acrylfarbe Rot 50ml"
        result = extractor.extract_all(title, "")

        assert result['extracted_color'] == 'Rot'
        assert result['extracted_use_cases'] == []
