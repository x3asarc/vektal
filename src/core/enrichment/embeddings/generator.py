"""
Embedding Generator for Product Semantic Search

Generates 768-dimensional embeddings using sentence-transformers
paraphrase-multilingual-mpnet-base-v2 model.

Architecture:
- Lazy model loading (load on first use)
- Field weighting (title 2x, description 1x, tags 1.5x)
- Batch processing for efficiency
- Content hashing to detect when re-embedding needed
"""

import hashlib
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """Generate 768-dimensional embeddings for product semantic search"""

    # Model configuration
    MODEL_NAME = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
    EMBEDDING_DIM = 768

    # Field weights for search text
    FIELD_WEIGHTS = {
        'title': 2.0,      # Title most important
        'description': 1.0,
        'tags': 1.5,       # Tags are good signals
    }

    def __init__(self, model_name: str = None):
        """
        Initialize with sentence-transformers model.
        Model is loaded once and cached.
        """
        self.model_name = model_name or self.MODEL_NAME
        self._model: Optional[SentenceTransformer] = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model on first use"""
        if self._model is None:
            print(f"Loading embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build_search_text(self, product: dict) -> str:
        """
        Build weighted search text from product fields.

        Weighting is done by repetition:
        - title (2x): "Pentart Acrylfarbe Pentart Acrylfarbe"
        - description (1x): "Hochwertige Farbe..."
        - tags (1.5x): "decoupage craft decoupage craft"
        """
        parts = []

        title = str(product.get('title', ''))
        if title:
            parts.append(title * int(self.FIELD_WEIGHTS['title']))

        description = str(product.get('description', ''))
        if description:
            parts.append(description)

        tags = product.get('tags', '')
        if tags:
            tag_text = ' '.join(tags) if isinstance(tags, list) else str(tags)
            # Approximate 1.5x by adding tags + half again
            parts.append(tag_text)
            parts.append(' '.join(tag_text.split()[:len(tag_text.split())//2]))

        return ' '.join(parts)

    def generate_embedding(self, product: dict) -> np.ndarray:
        """
        Generate embedding for a single product.

        Returns 768-dimensional numpy array.
        """
        search_text = self.build_search_text(product)
        return self.model.encode(search_text)

    def generate_batch(self, products: List[dict],
                      batch_size: int = 32,
                      show_progress: bool = True) -> List[np.ndarray]:
        """
        Generate embeddings for multiple products efficiently.

        Args:
            products: List of product dicts
            batch_size: Number to encode at once
            show_progress: Print progress updates

        Returns list of 768-dim numpy arrays.
        """
        if show_progress:
            print(f"Generating embeddings for {len(products)} products...")

        # Build all search texts first
        search_texts = [self.build_search_text(p) for p in products]

        # Batch encode for efficiency
        embeddings = self.model.encode(
            search_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress
        )

        if show_progress:
            print(f"Generated {len(embeddings)} embeddings ({self.EMBEDDING_DIM}-dim)")

        return list(embeddings)

    def compute_content_hash(self, product: dict) -> str:
        """
        Compute hash of searchable content.
        Used to detect when re-embedding is needed.

        Only hash title + description + tags (not price/inventory).
        """
        content = (
            str(product.get('title', '')) +
            str(product.get('description', '')) +
            str(product.get('tags', ''))
        )
        return hashlib.md5(content.encode()).hexdigest()

    def needs_reembedding(self, product: dict, stored_hash: str) -> bool:
        """Check if product content changed and needs new embedding"""
        current_hash = self.compute_content_hash(product)
        return current_hash != stored_hash

    @property
    def embedding_dimension(self) -> int:
        """Return embedding dimension (768 for mpnet)"""
        return self.EMBEDDING_DIM
