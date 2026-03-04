"""
Vector embedding generation for codebase knowledge graph.

Uses sentence-transformers (local, free) for semantic similarity search.
Embeddings stored IN Neo4j (not separate vector DB) for integrated graph+vector queries.

Phase 14 - Codebase Knowledge Graph & Continual Learning
"""

import logging
import os
import hashlib
import asyncio
import threading
from typing import List, Optional, Callable, Any
import numpy as np
from src.graph.backend_resolver import runtime_backend_mode as _read_runtime_backend_mode

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


def _runtime_backend_mode() -> str:
    return _read_runtime_backend_mode()


def _should_force_hash_fallback() -> bool:
    if os.environ.get("GRAPH_EMBEDDINGS_FORCE_HASH", "false").lower() == "true":
        return True
    local_snapshot_hash = os.environ.get("GRAPH_EMBEDDINGS_LOCAL_SNAPSHOT_HASH", "true").lower() == "true"
    return local_snapshot_hash and _runtime_backend_mode() == "local_snapshot"


def _deterministic_embedding(text: str) -> List[float]:
    """
    Generate a deterministic offline embedding from text.

    This is a sandbox-safe fallback when sentence-transformers model files
    are unavailable and remote downloads are blocked.
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    repeats = (EMBEDDING_DIMENSION // len(seed)) + 1
    raw = (seed * repeats)[:EMBEDDING_DIMENSION]
    vector = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
    vector = (vector - 127.5) / 127.5
    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector = vector / norm
    return vector.tolist()


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
        offline_mode = os.environ.get("GRAPH_EMBEDDINGS_OFFLINE", "true").lower() == "true"
        kwargs = {"local_files_only": True} if offline_mode else {}
        _model = SentenceTransformer(EMBEDDING_MODEL, **kwargs)
        _model_loaded = True
        logger.info(
            "Loaded embedding model: %s (offline=%s)",
            EMBEDDING_MODEL,
            offline_mode,
        )
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

    if _should_force_hash_fallback():
        return _deterministic_embedding(text)

    model = _get_model()
    if model is None:
        if os.environ.get("GRAPH_EMBEDDINGS_HASH_FALLBACK", "true").lower() == "true":
            logger.warning("Model unavailable - using deterministic hash embedding fallback")
            return _deterministic_embedding(text)
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

    if _should_force_hash_fallback():
        return [_deterministic_embedding(text or "") for text in texts]

    model = _get_model()
    if model is None:
        if os.environ.get("GRAPH_EMBEDDINGS_HASH_FALLBACK", "true").lower() == "true":
            logger.warning("Model unavailable - using deterministic hash embedding fallback")
            return [_deterministic_embedding(text or "") for text in texts]
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


def _execute_query(driver, query: str, parameters: dict) -> List[dict]:
    """Execute query using driver, automatically handling sync/async and existing event loops."""
    # Definitively detect sync vs async by inspecting a session instance
    session = driver.session()
    
    if hasattr(session, "__enter__"):
        # Synchronous driver
        with session:
            result = session.run(query, **parameters)
            return [record.data() for record in result]

    # Asynchronous driver (Aura / Graphiti default)
    async def _run_async():
        async with session:
            result = await session.run(query, **parameters)
            return await result.data()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run_async())

    if loop.is_running():
        res_container = []
        err_container = []

        def _thread_target():
            try:
                # New loop in new thread
                res_container.append(asyncio.run(_run_async()))
            except Exception as e:
                err_container.append(e)

        t = threading.Thread(target=_thread_target)
        t.start()
        t.join()
        
        if err_container:
            raise err_container[0]
        return res_container[0]
    else:
        return loop.run_until_complete(_run_async())

def create_vector_index(client) -> bool:
    """
    Create Neo4j vector index for codebase embeddings.
    """
    if client is None or not hasattr(client, "driver"):
        return False

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
        try:
            _execute_query(client.driver, query, {})
            logger.info(f"Created vector index: {VECTOR_INDEX_CONFIG['index_name']}")
        except Exception as e:
            if "already exists" in str(e).lower() or "equivalent index" in str(e).lower():
                logger.info(f"Vector index already exists: {VECTOR_INDEX_CONFIG['index_name']}")
            else:
                raise
        return True
    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        return False


def similarity_search(client, query_embedding: List[float], top_k: int = 5, min_score: float = 0.7) -> List[dict]:
    """
    Search for similar code entities using vector similarity.
    """
    if client is None or not hasattr(client, "driver") or not query_embedding:
        return []

    try:
        query = f"""
        CALL db.index.vector.queryNodes(
            '{VECTOR_INDEX_CONFIG['index_name']}',
            {top_k * 2},
            $embedding
        )
        YIELD node, score
        WHERE score >= $min_score
        RETURN node.path as path, node.entity_type as entity_type, score, node.summary as summary
        ORDER BY score DESC
        LIMIT $top_k
        """
        return _execute_query(client.driver, query, {
            "embedding": query_embedding,
            "min_score": min_score,
            "top_k": top_k
        })
    except Exception as e:
        logger.error(f"Failed to search similar entities: {e}")
        return []
