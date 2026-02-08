"""
Unit Tests for Embedding Generator

Tests the EmbeddingGenerator for product semantic search:
- Embedding dimension and type
- Field weighting (title 2x, description 1x, tags 1.5x)
- Batch processing
- Content hashing
- Semantic similarity
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.core.enrichment.embeddings.generator import EmbeddingGenerator


class TestEmbeddingGenerator:
    @pytest.fixture
    def generator(self):
        """Create generator (model will be lazy loaded)"""
        return EmbeddingGenerator()

    def test_embedding_dimension(self, generator):
        """Embedding is 768-dimensional"""
        product = {'title': 'Test Product', 'description': 'Test description'}
        embedding = generator.generate_embedding(product)
        assert embedding.shape == (768,)

    def test_embedding_is_numpy_array(self, generator):
        """Embedding is numpy array"""
        product = {'title': 'Test'}
        embedding = generator.generate_embedding(product)
        assert isinstance(embedding, np.ndarray)

    def test_search_text_includes_title_twice(self, generator):
        """Title is weighted 2x in search text"""
        product = {'title': 'Pentart Acryl'}
        search_text = generator.build_search_text(product)
        assert search_text.count('Pentart Acryl') >= 2

    def test_search_text_includes_description(self, generator):
        """Description included in search text"""
        product = {'title': 'Test', 'description': 'Unique Description XYZ'}
        search_text = generator.build_search_text(product)
        assert 'Unique Description XYZ' in search_text

    def test_search_text_includes_tags(self, generator):
        """Tags included in search text"""
        product = {'title': 'Test', 'tags': 'decoupage,craft'}
        search_text = generator.build_search_text(product)
        assert 'decoupage' in search_text

    def test_batch_generation(self, generator):
        """Batch generation returns list of embeddings"""
        products = [
            {'title': 'Product 1'},
            {'title': 'Product 2'},
            {'title': 'Product 3'},
        ]
        embeddings = generator.generate_batch(products, show_progress=False)
        assert len(embeddings) == 3
        assert all(e.shape == (768,) for e in embeddings)

    def test_content_hash_changes_with_title(self, generator):
        """Content hash changes when title changes"""
        hash1 = generator.compute_content_hash({'title': 'Original'})
        hash2 = generator.compute_content_hash({'title': 'Changed'})
        assert hash1 != hash2

    def test_content_hash_stable_for_price_change(self, generator):
        """Content hash unchanged when only price changes"""
        hash1 = generator.compute_content_hash({'title': 'Test', 'price': 10})
        hash2 = generator.compute_content_hash({'title': 'Test', 'price': 20})
        assert hash1 == hash2

    def test_needs_reembedding_true_when_changed(self, generator):
        """needs_reembedding returns True when content changed"""
        original_hash = generator.compute_content_hash({'title': 'Original'})
        changed_product = {'title': 'Changed'}
        assert generator.needs_reembedding(changed_product, original_hash)

    def test_needs_reembedding_false_when_same(self, generator):
        """needs_reembedding returns False when content unchanged"""
        product = {'title': 'Same'}
        hash1 = generator.compute_content_hash(product)
        assert not generator.needs_reembedding(product, hash1)

    def test_lazy_model_loading(self):
        """Model not loaded until first embedding generated"""
        generator = EmbeddingGenerator()
        assert generator._model is None
        # Access model property triggers load
        _ = generator.model
        assert generator._model is not None

    def test_similar_products_have_similar_embeddings(self, generator):
        """Similar products should have high cosine similarity"""
        from sklearn.metrics.pairwise import cosine_similarity

        p1 = {'title': 'Pentart Acrylfarbe Rot 20ml', 'description': 'Hochwertige Acrylfarbe'}
        p2 = {'title': 'Pentart Acrylfarbe Blau 20ml', 'description': 'Hochwertige Acrylfarbe'}
        p3 = {'title': 'Reispapier Vintage Rose A4', 'description': 'Für Decoupage'}

        e1 = generator.generate_embedding(p1)
        e2 = generator.generate_embedding(p2)
        e3 = generator.generate_embedding(p3)

        # Similar paints should be more similar than paint vs paper
        sim_paints = cosine_similarity([e1], [e2])[0][0]
        sim_different = cosine_similarity([e1], [e3])[0][0]
        assert sim_paints > sim_different

    def test_embedding_dimension_property(self, generator):
        """embedding_dimension property returns 768"""
        assert generator.embedding_dimension == 768

    def test_model_name_default(self):
        """Default model is paraphrase-multilingual-mpnet-base-v2"""
        generator = EmbeddingGenerator()
        assert 'paraphrase-multilingual-mpnet-base-v2' in generator.model_name

    def test_custom_model_name(self):
        """Can specify custom model name"""
        custom_model = 'custom-model'
        generator = EmbeddingGenerator(model_name=custom_model)
        assert generator.model_name == custom_model
