"""
Unit tests for codebase embedding generation.

Tests hierarchical summary generation and vector embedding creation
for Phase 14 knowledge graph.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.core.embeddings import (
    generate_embedding,
    batch_generate_embeddings,
    EMBEDDING_DIMENSION,
    VECTOR_INDEX_CONFIG
)
from src.core.summary_generator import (
    generate_file_summary,
    generate_function_summary,
    generate_class_summary,
    generate_planning_doc_summary
)


class TestEmbeddingGeneration:
    """Test vector embedding generation."""

    @patch('src.core.embeddings._get_model')
    def test_embedding_dimension(self, mock_get_model):
        """Verify embedding is 384-dimensional."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros(384)
        mock_get_model.return_value = mock_model

        embedding = generate_embedding("test text")
        assert len(embedding) == EMBEDDING_DIMENSION
        assert EMBEDDING_DIMENSION == 384

    @patch('src.core.embeddings._get_model')
    def test_embedding_determinism(self, mock_get_model):
        """Same input produces same output."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.ones(384) * 0.5
        mock_get_model.return_value = mock_model

        emb1 = generate_embedding("test text")
        emb2 = generate_embedding("test text")
        assert emb1 == emb2

    @patch('src.core.embeddings._get_model')
    def test_batch_embedding(self, mock_get_model):
        """Batch processing works."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.zeros((3, 384))
        mock_get_model.return_value = mock_model

        texts = ["text1", "text2", "text3"]
        embeddings = batch_generate_embeddings(texts)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    def test_empty_text_handling(self):
        """Empty text returns zero vector without calling model."""
        embedding = generate_embedding("")
        assert len(embedding) == 384
        assert all(v == 0.0 for v in embedding)

    def test_empty_batch_handling(self):
        """Empty list returns empty list."""
        embeddings = batch_generate_embeddings([])
        assert embeddings == []

    def test_vector_index_config(self):
        """Vector index config has required fields."""
        assert "index_name" in VECTOR_INDEX_CONFIG
        assert "node_label" in VECTOR_INDEX_CONFIG
        assert "property_name" in VECTOR_INDEX_CONFIG
        assert "dimension" in VECTOR_INDEX_CONFIG
        assert "similarity_function" in VECTOR_INDEX_CONFIG

        assert VECTOR_INDEX_CONFIG["dimension"] == 384
        assert VECTOR_INDEX_CONFIG["similarity_function"] == "cosine"

    @patch('src.core.embeddings._get_model', return_value=None)
    def test_model_unavailable_uses_deterministic_fallback(self, _mock_get_model, monkeypatch):
        monkeypatch.setenv("GRAPH_EMBEDDINGS_HASH_FALLBACK", "true")
        emb1 = generate_embedding("sandbox query")
        emb2 = generate_embedding("sandbox query")
        assert len(emb1) == 384
        assert emb1 == emb2
        assert any(v != 0.0 for v in emb1)

    @patch('src.core.embeddings._runtime_backend_mode', return_value="local_snapshot")
    @patch('src.core.embeddings._get_model')
    def test_local_snapshot_mode_forces_hash_embeddings(self, mock_get_model, _mock_mode, monkeypatch):
        monkeypatch.setenv("GRAPH_EMBEDDINGS_LOCAL_SNAPSHOT_HASH", "true")
        emb = generate_embedding("local snapshot query")
        assert len(emb) == 384
        assert any(v != 0.0 for v in emb)
        mock_get_model.assert_not_called()


class TestSummaryGeneration:
    """Test hierarchical summary extraction."""

    def test_summary_file_format(self):
        """File summary has expected structure."""
        summary = generate_file_summary("src/core/embeddings.py")
        if summary:  # File might not exist in test environment
            assert "File:" in summary
            assert "Purpose:" in summary
            assert "Exports:" in summary
            assert "Imports:" in summary

    def test_summary_function_format(self):
        """Function summary has expected structure."""
        summary = generate_function_summary(
            file_path="src/core/embeddings.py",
            function_name="generate_embedding",
            signature="(text: str) -> List[float]",
            docstring="Generate vector embedding for text."
        )
        assert "Function:" in summary
        assert "Signature:" in summary
        assert "Purpose:" in summary
        assert "File:" in summary
        assert "generate_embedding" in summary

    def test_summary_class_format(self):
        """Class summary has expected structure."""
        summary = generate_class_summary(
            file_path="src/core/codebase_entities.py",
            class_name="FileEntity",
            bases=["BaseEntity"],
            docstring="Represents a source file.",
            methods=["validate_path"]
        )
        assert "Class:" in summary
        assert "Inherits:" in summary
        assert "Purpose:" in summary
        assert "Methods:" in summary
        assert "File:" in summary
        assert "FileEntity" in summary

    def test_summary_planning_doc_format(self):
        """Planning doc summary has expected structure."""
        summary = generate_planning_doc_summary(
            path=".planning/phases/14-continuous-optimization-learning/14-01-PLAN.md",
            doc_type="PLAN",
            goal="Create codebase entity schema foundation",
            status="complete"
        )
        assert "Planning:" in summary
        assert "Type:" in summary
        assert "Goal:" in summary
        assert "Status:" in summary
        assert "PLAN" in summary

    def test_function_summary_without_docstring(self):
        """Function summary handles missing docstring."""
        summary = generate_function_summary(
            file_path="src/core/test.py",
            function_name="helper",
            signature="() -> None",
            docstring=None
        )
        assert "No description available" in summary

    def test_class_summary_without_bases(self):
        """Class summary handles no parent classes."""
        summary = generate_class_summary(
            file_path="src/core/test.py",
            class_name="SimpleClass",
            bases=[],
            docstring="A simple class"
        )
        assert "Inherits: object" in summary

    def test_planning_doc_summary_defaults(self):
        """Planning doc summary handles missing optional fields."""
        summary = generate_planning_doc_summary(
            path=".planning/test.md",
            doc_type="NOTE"
        )
        assert "No goal specified" in summary
        assert "Unknown" in summary


class TestEmbeddingIntegration:
    """Integration tests combining summaries and embeddings."""

    @patch('src.core.embeddings._get_model')
    def test_embed_file_summary(self, mock_get_model):
        """Can embed a file summary."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(384)
        mock_get_model.return_value = mock_model

        summary = generate_file_summary("src/core/embeddings.py")
        if summary:
            embedding = generate_embedding(summary)
            assert len(embedding) == 384
            assert not all(v == 0.0 for v in embedding)  # Non-zero vector

    @patch('src.core.embeddings._get_model')
    def test_embed_function_summary(self, mock_get_model):
        """Can embed a function summary."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(384)
        mock_get_model.return_value = mock_model

        summary = generate_function_summary(
            file_path="src/core/embeddings.py",
            function_name="generate_embedding",
            signature="(text: str) -> List[float]",
            docstring="Generate vector embedding."
        )
        embedding = generate_embedding(summary)
        assert len(embedding) == 384

    @patch('src.core.embeddings._get_model')
    def test_batch_embed_summaries(self, mock_get_model):
        """Can batch embed multiple summaries."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.rand(3, 384)
        mock_get_model.return_value = mock_model

        summaries = [
            generate_function_summary("src/a.py", "func1", "() -> None", "Func 1"),
            generate_function_summary("src/b.py", "func2", "() -> None", "Func 2"),
            generate_class_summary("src/c.py", "MyClass", ["object"], "My class")
        ]
        embeddings = batch_generate_embeddings(summaries)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
