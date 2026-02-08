"""
Local Vendor Classifier

Uses sentence-transformers for free, local classification.
No API calls - runs entirely on CPU.

Model: all-MiniLM-L6-v2 (120MB, fast inference)
"""

import logging
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load to avoid import-time downloads
_model = None


def _get_model():
    """Lazy load the sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformers model...")
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            _model = False  # Mark as unavailable
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            _model = False
    return _model if _model else None


@dataclass
class ClassificationResult:
    """Result of local classification."""
    vendor_name: Optional[str]
    confidence: float
    method: str = "local_llm"
    needs_api_fallback: bool = False
    similarity_scores: dict = None


# Pre-defined vendor profiles for classification
VENDOR_PROFILES = {
    'ITD Collection': (
        "Italian rice paper decoupage scrapbooking craft supplies "
        "paper napkins mixed media art reispapier serviettentechnik "
        "A4 A3 vintage floral botanical"
    ),
    'Pentart': (
        "Hungarian acrylic paint art supplies stencils mixed media "
        "chalk paint furniture painting decorative craft farbe acryl "
        "crackle paste texture paste"
    ),
    'Aisticraft': (
        "Paper crafts decoupage supplies napkins decorative papers "
        "scrapbooking card making laser cut wooden shapes"
    ),
    'FN Deco': (
        "Decorative paper napkins serviettes party supplies "
        "table decorations themed napkins birthday wedding"
    ),
    'Paper Designs': (
        "Rice paper decoupage craft supplies premium quality "
        "artistic designs German brand hobby basteln"
    ),
    'Stamperia': (
        "Italian scrapbooking supplies paper collections "
        "decoupage mixed media stamps dies cutting dies "
        "patterned papers"
    )
}


class LocalVendorClassifier:
    """
    Classify vendors using local sentence-transformers.

    Free, fast, no API calls.
    Fallback to API when confidence < threshold.
    """

    def __init__(self, confidence_threshold: float = 0.75):
        """
        Initialize classifier.

        Args:
            confidence_threshold: Minimum confidence to accept (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold
        self._vendor_embeddings: dict = {}
        self._embeddings_computed = False

    def _compute_vendor_embeddings(self):
        """Pre-compute embeddings for known vendors."""
        if self._embeddings_computed:
            return

        model = _get_model()
        if not model:
            logger.warning("Model not available, classification disabled")
            return

        logger.info("Computing vendor embeddings...")
        for vendor, profile in VENDOR_PROFILES.items():
            self._vendor_embeddings[vendor] = model.encode(
                profile,
                convert_to_numpy=True
            )

        self._embeddings_computed = True
        logger.info(f"Computed embeddings for {len(self._vendor_embeddings)} vendors")

    @lru_cache(maxsize=1000)
    def classify(
        self,
        text: str,
        additional_context: str = ""
    ) -> ClassificationResult:
        """
        Classify text to identify vendor.

        Args:
            text: Text to classify (search results, product info)
            additional_context: Extra context (store keywords)

        Returns:
            ClassificationResult with vendor and confidence
        """
        model = _get_model()
        if not model:
            return ClassificationResult(
                vendor_name=None,
                confidence=0.0,
                needs_api_fallback=True
            )

        # Ensure embeddings are computed
        self._compute_vendor_embeddings()

        if not self._vendor_embeddings:
            return ClassificationResult(
                vendor_name=None,
                confidence=0.0,
                needs_api_fallback=True
            )

        # Combine text with context
        full_text = f"{text} {additional_context}".strip()

        # Encode input text
        text_embedding = model.encode(full_text, convert_to_numpy=True)

        # Calculate similarity to each vendor
        similarities = {}
        for vendor, vendor_embedding in self._vendor_embeddings.items():
            similarity = self._cosine_similarity(text_embedding, vendor_embedding)
            similarities[vendor] = float(similarity)

        # Find best match
        if not similarities:
            return ClassificationResult(
                vendor_name=None,
                confidence=0.0,
                needs_api_fallback=True
            )

        best_vendor = max(similarities, key=similarities.get)
        best_score = similarities[best_vendor]

        # Determine if we need API fallback
        needs_fallback = best_score < self.confidence_threshold

        return ClassificationResult(
            vendor_name=best_vendor if best_score >= self.confidence_threshold else None,
            confidence=round(best_score, 3),
            needs_api_fallback=needs_fallback,
            similarity_scores=similarities
        )

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add_vendor_profile(self, vendor_name: str, profile: str):
        """Add a new vendor profile dynamically."""
        model = _get_model()
        if model:
            VENDOR_PROFILES[vendor_name] = profile
            self._vendor_embeddings[vendor_name] = model.encode(
                profile,
                convert_to_numpy=True
            )

    def list_vendors(self) -> list[str]:
        """List known vendor profiles."""
        return list(VENDOR_PROFILES.keys())
