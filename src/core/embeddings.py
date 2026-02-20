"""
Vector embedding generation for codebase knowledge graph.

Uses sentence-transformers (local, free) for semantic similarity search.
Embeddings stored IN Neo4j (not separate vector DB) for integrated graph+vector queries.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import logging
from typing import List, Optional, Callable, Any
import numpy as np

logger = logging.getLogger(__name__)

# Model configuration
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # 384 dimensions, 23MB, fast
EMBEDDING_DIMENSION = 384

# Neo4j vector index configuration
VECTOR_INDEX_CONFIG = {
    "index_name": "codebase_embeddings",
    "node_label": "CodeEntity",  # Abstract label for all code nodes
    "property_name": "embedding",
    "dimension": 384,
    "similarity_function": "cosine"
}

# Lazy model loading (singleton pattern)
_model: Optional[Any] = None
_model_loaded = False


def _get_model():
    """
    Get or load sentence-transformers model (lazy loading).

    Returns:
        SentenceTransformer model instance
    """
    global _model, _model_loaded

    if _model_loaded:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
        _model_loaded = True
        logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        return _model
    except ImportError:
        logger.warning("sentence-transformers not installed - embeddings unavailable")
        _model_loaded = True  # Don't retry
        return None
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        _model_loaded = True  # Don't retry
        return None


def generate_embedding(text: str) -> List[float]:
    """
    Generate vector embedding for text.

    Uses sentence-transformers 'all-MiniLM-L6-v2' model (384 dimensions).
    Model is loaded lazily on first use and cached.

    Args:
        text: Text to embed (should be summary, not full content)

    Returns:
        384-dimensional float vector, or zero vector if model unavailable/empty text

    Example:
        >>> summary = generate_file_summary("src/core/embeddings.py")
        >>> embedding = generate_embedding(summary)
        >>> len(embedding)
        384
    """
    # Handle empty text
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding - returning zero vector")
        return [0.0] * EMBEDDING_DIMENSION

    model = _get_model()
    if model is None:
        logger.warning("Model unavailable - returning zero vector")
        return [0.0] * EMBEDDING_DIMENSION

    try:
        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return [0.0] * EMBEDDING_DIMENSION


def batch_generate_embeddings(
    texts: List[str],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (batch processing).

    More efficient than calling generate_embedding() in a loop.

    Args:
        texts: List of texts to embed
        progress_callback: Optional callback(current, total) for progress tracking

    Returns:
        List of 384-dimensional float vectors

    Example:
        >>> summaries = [generate_file_summary(f) for f in files]
        >>> embeddings = batch_generate_embeddings(summaries)
        >>> len(embeddings) == len(summaries)
        True
    """
    # Handle empty list
    if not texts:
        return []

    model = _get_model()
    if model is None:
        logger.warning("Model unavailable - returning zero vectors")
        return [[0.0] * EMBEDDING_DIMENSION] * len(texts)

    try:
        # Batch encode
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        # Call progress callback if provided
        if progress_callback:
            for i in range(len(texts)):
                progress_callback(i + 1, len(texts))

        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Failed to batch generate embeddings: {e}")
        return [[0.0] * EMBEDDING_DIMENSION] * len(texts)


def create_vector_index(client) -> bool:
    """
    Create Neo4j vector index for codebase embeddings.

    Uses configuration from VECTOR_INDEX_CONFIG. Idempotent - safe to call multiple times.

    Args:
        client: Graphiti client instance

    Returns:
        True if index created/exists, False on error

    Cypher:
        CALL db.index.vector.createNodeIndex(
            'codebase_embeddings',
            'CodeEntity',
            'embedding',
            384,
            'cosine'
        )
    """
    if client is None:
        logger.warning("Client is None - cannot create vector index")
        return False

    try:
        if not hasattr(client, 'driver'):
            logger.error("Client does not have a valid driver")
            return False

        # Check if index already exists
        async def _create_index():
            async with client.driver.session() as session:
                # Try to create index (will fail if exists, but that's ok)
                try:
                    query = f"""
                    CALL db.index.vector.createNodeIndex(
                        '{VECTOR_INDEX_CONFIG['index_name']}',
                        '{VECTOR_INDEX_CONFIG['node_label']}',
                        '{VECTOR_INDEX_CONFIG['property_name']}',
                        {VECTOR_INDEX_CONFIG['dimension']},
                        '{VECTOR_INDEX_CONFIG['similarity_function']}'
                    )
                    """
                    await session.run(query)
                    logger.info(f"Created vector index: {VECTOR_INDEX_CONFIG['index_name']}")
                except Exception as e:
                    # Index might already exist
                    if 'already exists' in str(e).lower() or 'equivalent index' in str(e).lower():
                        logger.info(f"Vector index already exists: {VECTOR_INDEX_CONFIG['index_name']}")
                    else:
                        raise

        import asyncio
        asyncio.run(_create_index())
        return True

    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        return False


def similarity_search(
    client,
    query_embedding: List[float],
    top_k: int = 5,
    min_score: float = 0.7
) -> List[dict]:
    """
    Search for similar code entities using vector similarity.

    Args:
        client: Graphiti client instance
        query_embedding: Query vector (384 dimensions)
        top_k: Number of results to return
        min_score: Minimum similarity score (0.0-1.0)

    Returns:
        List of similar entities with scores

    Example:
        >>> query = generate_file_summary("src/core/new_module.py")
        >>> query_emb = generate_embedding(query)
        >>> similar = similarity_search(client, query_emb, top_k=5)
        >>> for item in similar:
        ...     print(f"{item['path']}: {item['score']:.2f}")
    """
    if client is None or not query_embedding:
        return []

    try:
        if not hasattr(client, 'driver'):
            return []

        async def _search():
            async with client.driver.session() as session:
                query = f"""
                CALL db.index.vector.queryNodes(
                    '{VECTOR_INDEX_CONFIG['index_name']}',
                    {top_k * 2},  // Get more results to filter by score
                    $embedding
                )
                YIELD node, score
                WHERE score >= $min_score
                RETURN node.path as path, node.entity_type as entity_type, score
                ORDER BY score DESC
                LIMIT $top_k
                """

                result = await session.run(
                    query,
                    embedding=query_embedding,
                    min_score=min_score,
                    top_k=top_k
                )

                records = await result.data()
                return records

        import asyncio
        results = asyncio.run(_search())
        return results

    except Exception as e:
        logger.error(f"Failed to search similar entities: {e}")
        return []
