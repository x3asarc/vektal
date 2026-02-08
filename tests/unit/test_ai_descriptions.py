"""Unit tests for AI description and SEO generators.

Tests cover:
- SEO meta title length and content validation
- SEO meta description length bounds (120-160 chars)
- URL handle umlaut transliteration
- URL handle stop word removal
- Image alt text generation
- AI description caching behavior
- AI similarity search functionality
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.core.enrichment.generators.descriptions import AIDescriptionGenerator
from src.core.enrichment.generators.seo import SEOGenerator


class TestSEOGenerator:
    """Test cases for SEO content generation"""

    @pytest.fixture
    def seo(self):
        """Create SEOGenerator instance for testing"""
        return SEOGenerator(store_name="Bastelschachtel")

    def test_meta_title_under_60_chars(self, seo):
        """Meta title must be under 60 characters"""
        title = seo.generate_meta_title("Pentart Acrylfarbe Jade", "20ml")
        assert len(title) <= 60
        assert title  # Not empty

    def test_meta_title_includes_store(self, seo):
        """Meta title includes store name when space allows"""
        title = seo.generate_meta_title("Test Product")
        assert "Bastelschachtel" in title

    def test_meta_title_format(self, seo):
        """Meta title follows expected format"""
        title = seo.generate_meta_title("Reispapier Vintage Rose", "A4")
        assert "Reispapier Vintage Rose" in title
        assert "A4" in title
        assert "|" in title  # Separator present

    def test_meta_description_length(self, seo):
        """Meta description between 120-160 chars"""
        desc = seo.generate_meta_description(
            "Reispapier", "ITD Collection", "Premium Qualität"
        )
        assert 120 <= len(desc) <= 160

    def test_meta_description_contains_vendor(self, seo):
        """Meta description includes vendor name"""
        desc = seo.generate_meta_description(
            "Acrylfarbe", "Pentart", "Wasserbasiert"
        )
        assert "Pentart" in desc
        assert "von" in desc  # German "by/from"

    def test_meta_description_with_size(self, seo):
        """Meta description includes size when provided"""
        desc = seo.generate_meta_description(
            "Papier", "ITD", "Hochwertig", size="A4"
        )
        assert "A4" in desc

    def test_url_handle_umlat_transliteration(self, seo):
        """URL handle transliterates umlauts correctly"""
        # Test all umlauts (note: "für" is a stop word so won't appear)
        handle = seo.generate_url_handle("Grün Größe Übung")
        assert "gruen" in handle
        assert "groesse" in handle
        assert "uebung" in handle
        # Ensure no umlauts remain
        assert "ü" not in handle
        assert "ö" not in handle
        assert "ä" not in handle

    def test_url_handle_fuer_is_stop_word(self, seo):
        """URL handle removes 'für' as stop word after transliteration"""
        handle = seo.generate_url_handle("Papier für Decoupage")
        # "für" should be transliterated to "fuer" then removed as stop word
        assert "fuer" not in handle
        assert "papier" in handle
        assert "decoupage" in handle

    def test_url_handle_eszett_conversion(self, seo):
        """URL handle converts ß to ss"""
        handle = seo.generate_url_handle("Weißgold")
        assert "weissgold" in handle
        assert "ß" not in handle

    def test_url_handle_removes_stop_words(self, seo):
        """URL handle removes German stop words"""
        handle = seo.generate_url_handle("Papier für die Decoupage mit der Schere")
        # Stop words should be removed: für, die, mit, der
        assert "fuer" not in handle
        assert "die" not in handle
        assert "mit" not in handle
        assert "der" not in handle
        # Content words should remain
        assert "papier" in handle
        assert "decoupage" in handle
        assert "schere" in handle

    def test_url_handle_lowercase(self, seo):
        """URL handle is lowercase"""
        handle = seo.generate_url_handle("PENTART Acrylfarbe")
        assert handle == handle.lower()

    def test_url_handle_with_vendor_and_size(self, seo):
        """URL handle combines vendor, product, and size"""
        handle = seo.generate_url_handle("Acrylfarbe Grün", size="20ml", vendor="Pentart")
        assert "pentart" in handle
        assert "acrylfarbe" in handle
        assert "gruen" in handle
        assert "20ml" in handle

    def test_url_handle_special_chars_removed(self, seo):
        """URL handle removes special characters"""
        handle = seo.generate_url_handle("Test & Co. (Special)")
        assert "&" not in handle
        assert "(" not in handle
        assert ")" not in handle
        assert "." not in handle

    def test_url_handle_collapses_hyphens(self, seo):
        """URL handle collapses multiple hyphens"""
        handle = seo.generate_url_handle("Test  &  Multiple   Spaces")
        assert "--" not in handle  # No double hyphens

    def test_url_handle_max_length(self, seo):
        """URL handle respects max length"""
        long_name = "Sehr langer Produktname mit vielen Wörtern die zusammen sehr lang sind"
        handle = seo.generate_url_handle(long_name, max_length=40)
        assert len(handle) <= 40

    def test_image_alt_text_basic(self, seo):
        """Image alt text contains basic product info"""
        alt = seo.generate_image_alt_text("Reispapier", "Vintage Rose", "A4")
        assert "Reispapier" in alt
        assert "Vintage Rose" in alt
        assert "A4" in alt

    def test_image_alt_text_with_vendor(self, seo):
        """Image alt text includes vendor when provided"""
        alt = seo.generate_image_alt_text("Acrylfarbe", size="20ml", vendor="Pentart")
        assert "Acrylfarbe" in alt
        assert "Pentart" in alt
        assert "von" in alt  # German "by"

    def test_image_alt_text_length(self, seo):
        """Image alt text under 125 chars"""
        alt = seo.generate_image_alt_text(
            "Reispapier", "Vintage Rose Motiv", "A4", "ITD Collection"
        )
        assert len(alt) <= 125

    def test_cta_rotation(self, seo):
        """CTA phrases rotate for variety"""
        ctas = []
        for _ in range(6):
            desc = seo.generate_meta_description("Test", "Vendor", "Feature")
            ctas.append(desc.split()[-1])  # Last word should be CTA
        # Should have at least 2 different CTAs in 6 calls
        assert len(set(ctas)) >= 2


class TestAIDescriptionGenerator:
    """Test cases for AI description generation"""

    @pytest.fixture
    def generator(self):
        """Create AIDescriptionGenerator instance with mocked API key"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            return AIDescriptionGenerator()

    def test_initialization_without_api_key(self):
        """Generator raises error without API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenRouter API key required"):
                AIDescriptionGenerator()

    def test_initialization_with_api_key(self):
        """Generator initializes with API key"""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            gen = AIDescriptionGenerator()
            assert gen.api_key == 'test-key'
            assert gen.model == "google/gemini-flash-1.5"  # Default model

    def test_cache_prevents_duplicate_calls(self, generator):
        """Same product doesn't call API twice"""
        # Mock the API call
        with patch.object(generator.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Test description'}}]
            }
            mock_post.return_value = mock_response

            product = {'title': 'Test Product', 'vendor': 'Pentart', 'category': 'Farbe'}
            examples = [
                {'title': 'Example 1', 'description': 'Example description 1'},
                {'title': 'Example 2', 'description': 'Example description 2'},
                {'title': 'Example 3', 'description': 'Example description 3'}
            ]

            # First call
            desc1 = generator.generate_description(product, examples)
            assert desc1 == 'Test description'
            assert mock_post.call_count == 1

            # Second call - should use cache
            desc2 = generator.generate_description(product, examples)
            assert desc2 == 'Test description'
            assert mock_post.call_count == 1  # Still 1, not 2

    def test_similar_products_returns_top_k(self, generator):
        """find_similar_products returns top k by cosine similarity"""
        # Create mock embeddings (768-dim)
        np.random.seed(42)  # For reproducibility
        target_embedding = np.random.rand(768)
        catalog_embeddings = np.random.rand(10, 768)
        catalog_data = [{'title': f'Product {i}', 'description': f'Description {i}'} for i in range(10)]

        # Find top 3 similar
        similar = generator.find_similar_products(
            target_embedding, catalog_embeddings, catalog_data, top_k=3
        )

        assert len(similar) == 3
        assert all('title' in p for p in similar)
        assert all('description' in p for p in similar)

    def test_similar_products_ordering(self, generator):
        """find_similar_products returns products ordered by similarity"""
        # Create specific embeddings where we know the similarity order
        # Using different angles to ensure clear similarity differences
        target = np.array([1.0, 0.0] + [0.0] * 766)  # Unit vector in first dimension

        # Create catalog with varying similarity to target
        # Cosine similarity depends on angle, not magnitude
        catalog = np.array([
            [1.0, 0.0] + [0.0] * 766,      # Very similar (angle=0°, similarity=1.0)
            [0.0, 1.0] + [0.0] * 766,      # Not similar (angle=90°, similarity=0.0)
            [0.7, 0.7] + [0.0] * 766,      # Somewhat similar (angle=45°, similarity=0.707)
        ])

        catalog_data = [
            {'title': 'Very Similar', 'description': 'desc1'},
            {'title': 'Not Similar', 'description': 'desc2'},
            {'title': 'Somewhat Similar', 'description': 'desc3'}
        ]

        similar = generator.find_similar_products(target, catalog, catalog_data, top_k=3)

        # First should be most similar (angle 0°)
        assert similar[0]['title'] == 'Very Similar'
        # Second should be somewhat similar (angle 45°)
        assert similar[1]['title'] == 'Somewhat Similar'
        # Third should be least similar (angle 90°)
        assert similar[2]['title'] == 'Not Similar'

    def test_generate_description_api_call_structure(self, generator):
        """API call includes correct structure and parameters"""
        with patch.object(generator.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Generated description'}}]
            }
            mock_post.return_value = mock_response

            product = {
                'title': 'Pentart Acrylfarbe Grün',
                'vendor': 'Pentart',
                'category': 'Farbe',
                'color': 'Grün',
                'size': '20ml'
            }
            examples = [
                {'title': 'Ex1', 'description': 'Desc1', 'category': 'Farbe'},
                {'title': 'Ex2', 'description': 'Desc2', 'category': 'Farbe'}
            ]

            generator.generate_description(product, examples)

            # Verify API call was made
            assert mock_post.called
            call_args = mock_post.call_args

            # Check payload structure
            payload = call_args.kwargs['json']
            assert payload['model'] == 'google/gemini-flash-1.5'
            assert payload['temperature'] == 0.3
            assert payload['max_tokens'] == 300
            assert len(payload['messages']) == 2  # system + user

            # Check headers
            headers = call_args.kwargs['headers']
            assert 'Authorization' in headers
            assert headers['Authorization'] == 'Bearer test-key'

    def test_batch_generation_limits_products(self, generator):
        """Batch generation respects max_products limit"""
        products = [
            {'title': f'Product {i}', 'vendor': 'Test', 'category': 'Test'}
            for i in range(10)
        ]

        with patch.object(generator, 'generate_description', return_value='Test desc') as mock_gen:
            # Limit to 3 products
            results = generator.generate_batch(products, max_products=3)

            # Should only process 3 products
            assert len(results) == 3
            assert mock_gen.call_count <= 3  # May be less if not enough examples

    def test_cost_estimates_available(self):
        """Cost estimates are documented for common models"""
        estimates = AIDescriptionGenerator.COST_ESTIMATES
        assert 'google/gemini-flash-1.5' in estimates
        assert 'openai/gpt-4o-mini' in estimates
        assert 'anthropic/claude-3.5-haiku' in estimates
