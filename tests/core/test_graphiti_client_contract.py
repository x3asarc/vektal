"""
Contract tests for Graphiti client singleton and fail-open behavior.

Tests do NOT require live Neo4j - all tests use mocks and environment overrides.

Phase 13.2 - Oracle Framework Reuse
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import asyncio
import src.core.graphiti_client


@pytest.fixture(autouse=True)
def reset_graphiti_singleton():
    """Reset the Graphiti client singleton before each test."""
    original_client = src.core.graphiti_client._graphiti_client
    original_import_failed = src.core.graphiti_client._import_failed
    original_unavailable_until = src.core.graphiti_client._graph_unavailable_until
    
    src.core.graphiti_client._graphiti_client = None
    src.core.graphiti_client._import_failed = False
    src.core.graphiti_client._graph_unavailable_until = 0.0
    
    yield
    
    src.core.graphiti_client._graphiti_client = original_client
    src.core.graphiti_client._import_failed = original_import_failed
    src.core.graphiti_client._graph_unavailable_until = original_unavailable_until


# ===========================================
# Test Client Singleton Behavior
# ===========================================

def test_get_graphiti_client_returns_none_when_disabled(monkeypatch):
    """
    Client returns None when GRAPH_ORACLE_ENABLED is false.
    """
    # Set environment to disabled
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'false')

    # Import after environment is set
    from src.core.graphiti_client import get_graphiti_client

    client = get_graphiti_client()
    assert client is None


def test_get_graphiti_client_returns_none_when_password_missing(monkeypatch):
    """
    Client returns None when NEO4J_PASSWORD is not set.
    """
    # Enable graph but remove password
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.delenv('NEO4J_PASSWORD', raising=False)

    # Import after environment is set
    from src.core.graphiti_client import get_graphiti_client

    client = get_graphiti_client()
    assert client is None


def test_check_graph_availability_returns_false_when_disabled(monkeypatch):
    """
    Availability check returns False when graph is disabled.
    """
    # Set environment to disabled
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'false')

    # Import after environment is set
    from src.core.graphiti_client import check_graph_availability

    available = check_graph_availability()
    assert available is False


def test_check_graph_availability_returns_false_when_client_unavailable(monkeypatch):
    """
    Availability check returns False when client cannot be initialized.
    """
    # Enable graph but remove password
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.delenv('NEO4J_PASSWORD', raising=False)

    # Import after environment is set
    from src.core.graphiti_client import check_graph_availability

    available = check_graph_availability()
    assert available is False


# ===========================================
# Test Fail-Open Behavior
# ===========================================

def test_query_with_fallback_returns_fallback_on_timeout():
    """
    query_with_fallback returns fallback value when query times out.
    """
    from src.core.graphiti_client import query_with_fallback

    # Create a query that hangs
    async def slow_query():
        await asyncio.sleep(10)  # Longer than timeout
        return "should not reach this"

    # Query with 0.1s timeout
    result = query_with_fallback(
        slow_query,
        fallback_value="fallback_result",
        timeout=0.1
    )

    assert result == "fallback_result"


def test_query_with_fallback_returns_fallback_on_error():
    """
    query_with_fallback returns fallback value when query raises exception.
    """
    from src.core.graphiti_client import query_with_fallback

    # Create a query that raises
    async def failing_query():
        raise ValueError("Intentional test error")

    # Query should return fallback
    result = query_with_fallback(
        failing_query,
        fallback_value=[],
        timeout=2.0
    )

    assert result == []


def test_query_with_fallback_returns_result_on_success():
    """
    query_with_fallback returns actual result when query succeeds.
    """
    from src.core.graphiti_client import query_with_fallback

    # Create a successful query
    async def successful_query():
        return {"data": "success"}

    # Query should return actual result
    result = query_with_fallback(
        successful_query,
        fallback_value={},
        timeout=2.0
    )

    assert result == {"data": "success"}


def test_query_with_fallback_flags_discrepancy_with_filesystem_results():
    """
    query_with_fallback returns filesystem results and triggers discrepancy callback on graph miss.
    """
    from src.core.graphiti_client import query_with_fallback

    async def empty_query():
        return []

    captured = {}

    def callback(payload):
        captured.update(payload)

    result = query_with_fallback(
        empty_query,
        fallback_value=[],
        filesystem_search_fn=lambda q: ["src/core/synthex_entities.py"],
        query_text="what imports src/core/synthex_entities.py",
        discrepancy_callback=callback,
        include_source_metadata=True,
    )

    assert result["source"] == "filesystem_fallback"
    assert result["discrepancy"] is True
    assert captured["query_text"] == "what imports src/core/synthex_entities.py"


# ===========================================
# Test Environment Configuration
# ===========================================

def test_client_reads_neo4j_uri_from_env(monkeypatch):
    """
    Client initialization reads NEO4J_URI from environment.
    """
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.setenv('NEO4J_URI', 'bolt://custom-host:7687')
    monkeypatch.setenv('NEO4J_USER', 'test_user')
    monkeypatch.setenv('NEO4J_PASSWORD', 'test_password')

    # Mock Graphiti class and connectivity probe
    with patch.object(src.core.graphiti_client, 'Graphiti') as mock_graphiti, \
         patch('src.core.graphiti_client._find_reachable_neo4j_uri') as mock_probe:
        
        mock_probe.return_value = 'bolt://custom-host:7687'
        mock_instance = MagicMock()
        mock_graphiti.return_value = mock_instance

        from src.core.graphiti_client import get_graphiti_client

        client = get_graphiti_client()

        # Verify Graphiti was called with correct URI
        mock_graphiti.assert_called_once_with(
            uri='bolt://custom-host:7687',
            user='test_user',
            password='test_password'
        )


def test_client_reads_neo4j_credentials_from_env(monkeypatch):
    """
    Client initialization reads NEO4J_USER and NEO4J_PASSWORD from environment.
    """
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_USER', 'custom_user')
    monkeypatch.setenv('NEO4J_PASSWORD', 'custom_password')

    # Mock Graphiti class and connectivity probe
    with patch.object(src.core.graphiti_client, 'Graphiti') as mock_graphiti, \
         patch('src.core.graphiti_client._find_reachable_neo4j_uri') as mock_probe:
        
        mock_probe.return_value = 'bolt://localhost:7687'
        mock_instance = MagicMock()
        mock_graphiti.return_value = mock_instance

        from src.core.graphiti_client import get_graphiti_client

        client = get_graphiti_client()

        # Verify Graphiti was called with correct credentials
        mock_graphiti.assert_called_once_with(
            uri='bolt://localhost:7687',
            user='custom_user',
            password='custom_password'
        )


def test_client_bridges_openrouter_env_to_openai(monkeypatch):
    """
    Client bridges OPENROUTER_* env vars to OPENAI_* vars for Graphiti defaults.
    """
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.setenv('NEO4J_URI', 'bolt://localhost:7687')
    monkeypatch.setenv('NEO4J_USER', 'neo4j')
    monkeypatch.setenv('NEO4J_PASSWORD', 'test_password')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_BASE_URL', raising=False)
    monkeypatch.setenv('OPENROUTER_API_KEY', 'or_test_key')
    monkeypatch.setenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')

    with patch.object(src.core.graphiti_client, 'Graphiti') as mock_graphiti, \
         patch('src.core.graphiti_client._find_reachable_neo4j_uri') as mock_probe:
        
        mock_probe.return_value = 'bolt://localhost:7687'
        mock_instance = MagicMock()
        mock_graphiti.return_value = mock_instance

        from src.core.graphiti_client import get_graphiti_client

        client = get_graphiti_client()
        assert client is mock_instance
        assert os.environ.get('OPENAI_API_KEY') == 'or_test_key'
        assert os.environ.get('OPENAI_BASE_URL') == 'https://openrouter.ai/api/v1'
        mock_graphiti.assert_called_once_with(
            uri='bolt://localhost:7687',
            user='neo4j',
            password='test_password'
        )


# ===========================================
# Test Import Failure Handling
# ===========================================

def test_client_handles_missing_graphiti_import_gracefully():
    """
    Client handles missing graphiti-core package gracefully.
    """
    # Simulate import failure by setting _import_failed flag
    import src.core.graphiti_client
    original_flag = src.core.graphiti_client._import_failed

    try:
        src.core.graphiti_client._import_failed = True
        src.core.graphiti_client.Graphiti = None

        from src.core.graphiti_client import get_graphiti_client

        # Client should return None
        client = get_graphiti_client()
        assert client is None

    finally:
        # Restore original state
        src.core.graphiti_client._import_failed = original_flag


def test_runtime_backend_mode_reads_backend_schema():
    """
    Runtime mode reader supports canonical backend schema (backend/reason).
    """
    with patch("src.graph.backend_resolver.os.path.exists", return_value=True), patch(
        "src.graph.backend_resolver.open",
        mock_open(read_data=json.dumps({"backend": "local_snapshot", "reason": "snapshot pin"})),
    ):
        from src.core.graphiti_client import _runtime_backend_mode

        assert _runtime_backend_mode() == "local_snapshot"


def test_runtime_backend_mode_maps_local_neo4j_to_legacy_mode():
    """
    Runtime mode reader maps backend=local_neo4j to mode=neo4j.
    """
    with patch("src.graph.backend_resolver.os.path.exists", return_value=True), patch(
        "src.graph.backend_resolver.open",
        mock_open(read_data=json.dumps({"backend": "local_neo4j", "reason": "local graph available"})),
    ):
        from src.core.graphiti_client import _runtime_backend_mode

        assert _runtime_backend_mode() == "neo4j"
