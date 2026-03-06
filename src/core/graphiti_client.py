"""
Graphiti client singleton for temporal knowledge graph integration.

Provides fail-open behavior for Oracle queries to prevent graph unavailability
from blocking critical mutation flows. All graph operations are bounded by timeouts
and return fallback values on error.

Phase 13.2 - Oracle Framework Reuse
"""

import os
import logging
import time
from typing import Optional, Callable, TypeVar, Any, Dict
import asyncio
from src.graph.backend_resolver import runtime_backend_mode as _read_runtime_backend_mode

logger = logging.getLogger(__name__)

# Singleton client instance
_graphiti_client: Optional[Any] = None
_import_failed = False
_graph_unavailable_until: float = 0.0
_local_embedder: Optional[Any] = None

# Try to import graphiti-core (may not be installed in all environments)
try:
    from graphiti_core import Graphiti
    from graphiti_core.embedder import EmbedderClient
except ImportError:
    logger.warning("graphiti-core not installed - graph Oracle will be unavailable")
    Graphiti = None
    EmbedderClient = None
    _import_failed = True

T = TypeVar('T')


class LocalSentenceTransformerEmbedder(EmbedderClient if EmbedderClient else object):
    """
    Local sentence-transformers embedder for Graphiti.

    Uses the same model that populated the graph (sentence-transformers/all-MiniLM-L6-v2)
    to ensure embedding consistency between graph nodes and search queries.

    Benefits:
    - Zero cost (no API calls)
    - Faster (local inference, no network latency)
    - Self-contained (no external dependencies)
    - Consistent with graph population
    """

    def __init__(self, model_name: str = 'sentence-transformers/all-MiniLM-L6-v2'):
        """Initialize with sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info(f"Initialized local embedder with model: {model_name}")
        except ImportError:
            logger.error("sentence-transformers not installed - cannot use local embedder")
            raise
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            raise

    async def create(self, input_data: list[str]) -> list[list[float]]:
        """
        Generate embeddings for input texts.

        Args:
            input_data: List of text strings to embed

        Returns:
            List of embedding vectors (lists of floats)
        """
        try:
            # sentence-transformers encode is synchronous, so we run it in executor
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(input_data, convert_to_numpy=True)
            )
            # Convert numpy arrays to lists for Graphiti
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise


def _get_local_embedder() -> Optional[Any]:
    """Get or create singleton local embedder instance."""
    global _local_embedder

    if _local_embedder is not None:
        return _local_embedder

    if EmbedderClient is None:
        return None

    try:
        _local_embedder = LocalSentenceTransformerEmbedder()
        return _local_embedder
    except Exception as e:
        logger.warning(f"Failed to initialize local embedder: {e}")
        return None


def _neo4j_uri_candidates() -> list[str]:
    primary = (os.environ.get("NEO4J_URI") or "").strip()
    fallback_raw = os.environ.get("NEO4J_URI_FALLBACKS", "bolt://localhost:7687")
    fallbacks = [item.strip() for item in fallback_raw.split(",") if item.strip()]
    ordered = [uri for uri in [primary, *fallbacks] if uri]
    return list(dict.fromkeys(ordered))


def _runtime_backend_mode() -> str:
    return _read_runtime_backend_mode()


def _find_reachable_neo4j_uri(user: str, password: str) -> Optional[str]:
    timeout_seconds = float(os.environ.get("NEO4J_CONNECT_TIMEOUT_SECONDS", "5.0"))
    try:
        from neo4j import GraphDatabase
    except Exception:
        return None

    for uri in _neo4j_uri_candidates():
        try:
            with GraphDatabase.driver(uri, auth=(user, password), connection_timeout=timeout_seconds) as driver:
                driver.verify_connectivity()
            return uri
        except Exception:
            continue
    return None


def _graph_backoff_seconds() -> float:
    return float(os.environ.get("NEO4J_UNAVAILABLE_BACKOFF_SECONDS", "30"))


def _is_empty_result(result: Any) -> bool:
    """Return True for graph miss-like results."""
    return result is None or result == [] or result == {} or result == ""


def get_graphiti_client() -> Optional[Any]:
    """
    Get singleton Graphiti client instance.

    Returns None if:
    - GRAPH_ORACLE_ENABLED is false (default)
    - graphiti-core package is not installed
    - Required environment variables are missing

    Implements fail-open pattern: graph unavailability does not block application.

    Returns:
        Optional[Graphiti]: Client instance or None
    """
    global _graphiti_client

    global _graph_unavailable_until

    # Check if graph Oracle is enabled
    if not os.environ.get('GRAPH_ORACLE_ENABLED', 'false').lower() == 'true':
        return None

    pinned_local_snapshot = _runtime_backend_mode() == "local_snapshot"
    force_probe = os.environ.get("GRAPH_FORCE_NEO4J_PROBE", "false").lower() == "true"
    if pinned_local_snapshot and not force_probe:
        return None

    if time.time() < _graph_unavailable_until:
        return None

    # Return None if import failed
    if _import_failed or Graphiti is None:
        return None

    # Return existing instance if already initialized
    if _graphiti_client is not None:
        return _graphiti_client

    def _bridge_openrouter_env() -> None:
        """
        Bridge OpenRouter env vars into OpenAI-compatible vars expected by graphiti-core defaults.
        """
        openai_key = os.environ.get('OPENAI_API_KEY')
        openrouter_key = os.environ.get('OPENROUTER_API_KEY')
        if not openai_key and openrouter_key:
            os.environ['OPENAI_API_KEY'] = openrouter_key
            logger.info("OPENAI_API_KEY not set; bridged from OPENROUTER_API_KEY for Graphiti")

        openai_base = os.environ.get('OPENAI_BASE_URL')
        openrouter_base = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        if not openai_base and os.environ.get('OPENROUTER_API_KEY'):
            os.environ['OPENAI_BASE_URL'] = openrouter_base
            logger.info("OPENAI_BASE_URL not set; bridged to %s for Graphiti", openrouter_base)

    # Initialize new client
    try:
        configured_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
        neo4j_password = os.environ.get('NEO4J_PASSWORD')

        if not neo4j_password:
            logger.warning("NEO4J_PASSWORD not set - graph Oracle unavailable")
            return None

        reachable_uri = _find_reachable_neo4j_uri(neo4j_user, neo4j_password)
        if reachable_uri is None:
            logger.warning(
                "No reachable Neo4j endpoint from candidates %s; graph Oracle unavailable",
                _neo4j_uri_candidates(),
            )
            _graph_unavailable_until = time.time() + _graph_backoff_seconds()
            return None

        # Bridge OpenRouter env vars for Graphiti's LLM client (always needed)
        _bridge_openrouter_env()

        # Get local embedder (sentence-transformers)
        local_embedder = _get_local_embedder()
        if local_embedder is None:
            logger.warning("Local embedder unavailable - using OpenAI for embeddings")
            # Initialize Graphiti client with default OpenAI embedder
            _graphiti_client = Graphiti(
                uri=reachable_uri,
                user=neo4j_user,
                password=neo4j_password
            )
        else:
            # Initialize Graphiti client with local sentence-transformers embedder
            _graphiti_client = Graphiti(
                uri=reachable_uri,
                user=neo4j_user,
                password=neo4j_password,
                embedder=local_embedder
            )
            logger.info("Using local sentence-transformers embedder for query embeddings")

        logger.info(f"Graphiti client initialized with URI: {reachable_uri} (configured={configured_uri})")
        _graph_unavailable_until = 0.0
        return _graphiti_client

    except Exception as e:
        logger.error(f"Failed to initialize Graphiti client: {e}", exc_info=True)
        _graph_unavailable_until = time.time() + _graph_backoff_seconds()
        return None


def check_graph_availability(timeout_seconds: float = 5.0) -> bool:
    """
    Check if graph database is available and responsive.

    Uses bounded timeout to prevent blocking. Returns False on any error
    (fail-open behavior).

    Args:
        timeout_seconds: Maximum time to wait for availability check

    Returns:
        bool: True if graph is available, False otherwise
    """
    client = get_graphiti_client()
    if client is None:
        return False

    try:
        # Run availability check with timeout
        async def _check():
            # Simple connectivity test - attempt to get driver session
            if hasattr(client, 'driver'):
                # Verify driver can connect
                async with client.driver.session() as session:
                    await session.run("RETURN 1")
                return True
            return False

        # Run async check with timeout
        result = asyncio.run(
            asyncio.wait_for(_check(), timeout=timeout_seconds)
        )
        return result

    except asyncio.TimeoutError:
        logger.warning(f"Graph availability check timed out after {timeout_seconds}s")
        return False
    except Exception as e:
        logger.warning(f"Graph availability check failed: {e}")
        return False


def query_with_fallback(
    query_fn: Callable[[], T],
    fallback_value: T,
    timeout: float = 2.0,
    filesystem_search_fn: Optional[Callable[[str], Any]] = None,
    query_text: str = "",
    discrepancy_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    include_source_metadata: bool = False,
) -> T:
    """
    Execute graph query with timeout and fallback.

    Implements fail-open pattern: returns fallback value on timeout or error.
    Logs warnings but never raises exceptions.

    Args:
        query_fn: Async callable that performs graph query
        fallback_value: Value to return on timeout or error
        timeout: Maximum time to wait for query completion
        filesystem_search_fn: Optional callable for fallback filesystem lookup
        query_text: Query text used by filesystem fallback and discrepancy logs
        discrepancy_callback: Optional callback to emit discrepancy event payload
        include_source_metadata: Return dict payload with source metadata when True

    Returns:
        Query result or fallback_value

    Example:
        >>> def get_evidence():
        >>>     return await client.search_episodes(...)
        >>> evidence = query_with_fallback(
        >>>     get_evidence,
        >>>     fallback_value=[],
        >>>     timeout=2.0
        >>> )
    """
    try:
        # Wrap in timeout
        result = asyncio.run(
            asyncio.wait_for(query_fn(), timeout=timeout)
        )
        if not _is_empty_result(result):
            if include_source_metadata:
                return {"results": result, "source": "graph"}  # type: ignore[return-value]
            return result

        # Graph returned empty; check filesystem fallback for discrepancy detection.
        if filesystem_search_fn and query_text:
            fs_results = filesystem_search_fn(query_text)
            if fs_results:
                payload = {
                    "query_text": query_text,
                    "paths": fs_results if isinstance(fs_results, list) else [],
                    "fallback_source": "filesystem",
                }
                logger.warning(
                    "Graph discrepancy detected for query '%s' - filesystem found %s result(s)",
                    query_text,
                    len(payload["paths"]) if isinstance(payload["paths"], list) else 0,
                )
                if discrepancy_callback:
                    try:
                        discrepancy_callback(payload)
                    except Exception as callback_error:
                        logger.warning("Discrepancy callback failed: %s", callback_error)

                if include_source_metadata:
                    return {
                        "results": fs_results,
                        "source": "filesystem_fallback",
                        "discrepancy": True,
                    }  # type: ignore[return-value]
                return fs_results

        if include_source_metadata:
            return {"results": fallback_value, "source": "fallback"}  # type: ignore[return-value]
        return fallback_value

    except asyncio.TimeoutError:
        logger.warning(f"Graph query timed out after {timeout}s - using fallback")
        if include_source_metadata:
            return {"results": fallback_value, "source": "timeout_fallback"}  # type: ignore[return-value]
        return fallback_value

    except Exception as e:
        logger.warning(f"Graph query failed: {e} - using fallback")
        if include_source_metadata:
            return {"results": fallback_value, "source": "error_fallback"}  # type: ignore[return-value]
        return fallback_value
