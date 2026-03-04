"""Tests for Neo4j health remediator."""

import pytest
from unittest.mock import patch, MagicMock
from src.graph.remediators.neo4j_health_remediator import Neo4jHealthRemediator


@pytest.mark.asyncio
async def test_validate_environment_success():
    """Test that neo4j module validation succeeds when module is available."""
    remediator = Neo4jHealthRemediator()

    with patch("builtins.__import__"):
        result = await remediator.validate_environment()
        assert result is True


@pytest.mark.asyncio
async def test_validate_environment_failure():
    """Test that validation fails when neo4j module is unavailable."""
    remediator = Neo4jHealthRemediator()

    with patch("builtins.__import__", side_effect=ImportError("No module named 'neo4j'")):
        result = await remediator.validate_environment()
        assert result is False


@pytest.mark.asyncio
async def test_missing_neo4j_uri():
    """Test handling of missing NEO4J_URI configuration."""
    remediator = Neo4jHealthRemediator()

    with patch.dict("os.environ", {"NEO4J_URI_FALLBACKS": "", "GRAPH_ORACLE_ENABLED": "false"}, clear=True):
        result = await remediator.diagnose_and_fix({})

        assert result.success is False
        assert "NEO4J_URI not configured" in result.message
        assert "config_check_failed" in result.actions_taken


@pytest.mark.asyncio
async def test_connection_success_first_attempt():
    """Test successful connection on first attempt."""
    remediator = Neo4jHealthRemediator()

    mock_driver = MagicMock()
    mock_driver.__enter__ = MagicMock(return_value=mock_driver)
    mock_driver.__exit__ = MagicMock(return_value=None)
    mock_driver.verify_connectivity = MagicMock()

    with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "test", "GRAPH_ORACLE_ENABLED": "false"}):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.return_value = mock_driver

            result = await remediator.diagnose_and_fix({})

            assert result.success is True
            assert "attempt 1/3" in result.message
            assert "connection_attempt_1" in result.actions_taken
            assert "connection_success" in result.actions_taken
            mock_driver.verify_connectivity.assert_called_once()


@pytest.mark.asyncio
async def test_connection_success_second_attempt():
    """Test successful connection on second attempt after one failure."""
    remediator = Neo4jHealthRemediator()

    mock_driver = MagicMock()
    mock_driver.__enter__ = MagicMock(return_value=mock_driver)
    mock_driver.__exit__ = MagicMock(return_value=None)
    mock_driver.verify_connectivity = MagicMock()

    call_count = {"count": 0}

    def side_effect_driver(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise ConnectionRefusedError("Connection refused")
        return mock_driver

    with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "test", "GRAPH_ORACLE_ENABLED": "false"}):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = side_effect_driver

            result = await remediator.diagnose_and_fix({})

            assert result.success is True
            assert "attempt 2/3" in result.message
            assert "connection_attempt_1" in result.actions_taken
            assert "connection_attempt_2" in result.actions_taken
            assert "backoff_wait_1s" in result.actions_taken
            assert "connection_success" in result.actions_taken


@pytest.mark.asyncio
async def test_connection_success_on_fallback_uri():
    """Test connection succeeds using NEO4J_URI_FALLBACKS when primary URI is stale."""
    remediator = Neo4jHealthRemediator()

    mock_driver = MagicMock()
    mock_driver.__enter__ = MagicMock(return_value=mock_driver)
    mock_driver.__exit__ = MagicMock(return_value=None)
    mock_driver.verify_connectivity = MagicMock()

    def side_effect_driver(uri, **kwargs):
        if "stale-host" in uri:
            raise ConnectionRefusedError("Connection refused")
        return mock_driver

    with patch.dict(
        "os.environ",
        {
            "NEO4J_URI": "bolt://stale-host:7687",
            "NEO4J_URI_FALLBACKS": "bolt://localhost:7687",
            "NEO4J_PASSWORD": "test",
            "GRAPH_ORACLE_ENABLED": "false",
        },
    ):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = side_effect_driver

            result = await remediator.diagnose_and_fix({})

            assert result.success is True
            assert "attempt 1/3" in result.message
            assert result.output == "Connected to bolt://localhost:7687"


@pytest.mark.asyncio
async def test_all_attempts_fail():
    """Test when all connection attempts fail."""
    remediator = Neo4jHealthRemediator()

    with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "test", "GRAPH_ORACLE_ENABLED": "false"}):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = ConnectionRefusedError("Connection refused")

            result = await remediator.diagnose_and_fix({})

            assert result.success is False
            assert "still unreachable after 3 attempts" in result.message
            assert "connection_attempt_1" in result.actions_taken
            assert "connection_attempt_2" in result.actions_taken
            assert "connection_attempt_3" in result.actions_taken
            assert "all_attempts_failed" in result.actions_taken
            assert "docker compose up" in result.message


@pytest.mark.asyncio
async def test_authentication_error_guidance():
    """Test guidance for authentication errors."""
    remediator = Neo4jHealthRemediator()

    with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "test", "GRAPH_ORACLE_ENABLED": "false"}):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = Exception("Authentication failed: Unauthorized")

            result = await remediator.diagnose_and_fix({})

            assert result.success is False
            assert "NEO4J_USER and NEO4J_PASSWORD" in result.message


@pytest.mark.asyncio
async def test_timeout_error_guidance():
    """Test guidance for timeout errors."""
    remediator = Neo4jHealthRemediator()

    with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_PASSWORD": "test", "GRAPH_ORACLE_ENABLED": "false"}):
        with patch("neo4j.GraphDatabase") as mock_graph_db:
            mock_graph_db.driver.side_effect = Exception("Connection timeout")

            result = await remediator.diagnose_and_fix({})

            assert result.success is False
            assert "starting up or overloaded" in result.message


@pytest.mark.asyncio
async def test_error_guidance_mapping():
    """Test error guidance helper method."""
    remediator = Neo4jHealthRemediator()

    # Test various error types
    assert "credentials" in remediator._get_error_guidance("AuthError", "authentication failed")
    assert "docker compose" in remediator._get_error_guidance("ConnError", "connection refused")
    assert "hostname" in remediator._get_error_guidance("HostError", "unknown host")
    assert "starting up" in remediator._get_error_guidance("TimeoutError", "timeout occurred")
    assert "logs" in remediator._get_error_guidance("UnknownError", "random error")


@pytest.mark.asyncio
async def test_service_name_and_description():
    """Test remediator metadata."""
    remediator = Neo4jHealthRemediator()

    assert remediator.service_name == "neo4j_health"
    assert "Neo4j connection" in remediator.description
    assert "exponential backoff" in remediator.description
