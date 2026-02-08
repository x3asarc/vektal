"""
Vector Embedding Generation

This module generates 768-dimensional semantic embeddings for products
using sentence-transformers, enabling semantic search in Phase 11.
"""

from .generator import EmbeddingGenerator

__all__ = ['EmbeddingGenerator']
