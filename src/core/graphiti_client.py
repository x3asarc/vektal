"""
Graphiti client singleton for temporal knowledge graph integration.

Provides fail-open behavior for Oracle queries to prevent graph unavailability
from blocking critical mutation flows. All graph operations are bounded by timeouts
and return fallback values on error.

Phase 13.2 - Oracle Framework Reuse
"""

import os
import logging
from typing import Optional, Callable, TypeVar, Any
import asyncio

logger = logging.getLogger(__name__)

# Singleton client instance
_graphiti_client: Optional[Any] = None
_import_failed = False

# Try to import graphiti-core (may not be installed in all environments)
try:
    from graphiti_core import Graphiti
except ImportError:
    logger.warning("graphiti-core not installed - graph Oracle will be unavailable")
    Graphiti = None
    _import_failed = True

T = TypeVar('T')


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

    # Check if graph Oracle is enabled
    if not os.environ.get('GRAPH_ORACLE_ENABLED', 'false').lower() == 'true':
        return None

    # Return None if import failed
    if _import_failed or Graphiti is None:
        return None

    # Return existing instance if already initialized
    if _graphiti_client is not None:
        return _graphiti_client

    # Initialize new client
    try:
        neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
        neo4j_password = os.environ.get('NEO4J_PASSWORD')

        if not neo4j_password:
            logger.warning("NEO4J_PASSWORD not set - graph Oracle unavailable")
            return None

        # Initialize Graphiti client
        _graphiti_client = Graphiti(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )

        logger.info(f"Graphiti client initialized with URI: {neo4j_uri}")
        return _graphiti_client

    except Exception as e:
        logger.error(f"Failed to initialize Graphiti client: {e}", exc_info=True)
        return None


def check_graph_availability(timeout_seconds: float = 2.0) -> bool:
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
    timeout: float = 2.0
) -> T:
    """
    Execute graph query with timeout and fallback.

    Implements fail-open pattern: returns fallback value on timeout or error.
    Logs warnings but never raises exceptions.

    Args:
        query_fn: Async callable that performs graph query
        fallback_value: Value to return on timeout or error
        timeout: Maximum time to wait for query completion

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
        return result

    except asyncio.TimeoutError:
        logger.warning(f"Graph query timed out after {timeout}s - using fallback")
        return fallback_value

    except Exception as e:
        logger.warning(f"Graph query failed: {e} - using fallback")
        return fallback_value
