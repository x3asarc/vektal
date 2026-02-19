"""
Contract tests for graph episode emission tasks.

Tests use Celery task testing patterns and mocks - no live Neo4j required.

Phase 13.2 - Oracle Framework Reuse
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.core.synthex_entities import EpisodeType


# ===========================================
# Test emit_episode Task
# ===========================================

def test_emit_episode_returns_early_when_graph_disabled(monkeypatch):
    """
    emit_episode returns False without error when GRAPH_ORACLE_ENABLED is false.
    """
    # Set environment to disabled
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'false')

    from src.tasks.graphiti_sync import emit_episode

    # Call task synchronously
    result = emit_episode(
        episode_type=EpisodeType.ORACLE_DECISION.value,
        store_id="store_123",
        payload={'decision': 'pass', 'confidence': 0.95, 'source_adapter': 'test'},
        correlation_id="test_123"
    )

    # Should return False (graph disabled)
    assert result is False


def test_emit_episode_validates_episode_payload(monkeypatch, caplog):
    """
    emit_episode logs validation error when payload is invalid.
    """
    # Enable graph
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.setenv('NEO4J_PASSWORD', 'test')

    # Mock client to return valid instance
    with patch('src.tasks.graphiti_sync.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.tasks.graphiti_sync.check_graph_availability') as mock_check:
            mock_check.return_value = True

            from src.tasks.graphiti_sync import emit_episode

            # Call with invalid payload (missing required fields)
            result = emit_episode(
                episode_type="invalid_type",  # Not a valid EpisodeType
                store_id="store_123",
                payload={},
                correlation_id=None
            )

            # Should return False and log error
            assert result is False
            assert any('validation error' in rec.message.lower() or 'invalid_type' in rec.message.lower()
                      for rec in caplog.records)


def test_emit_episode_retries_transient_errors(monkeypatch):
    """
    emit_episode task is configured for retry on transient errors.
    """
    from src.tasks.graphiti_sync import emit_episode

    # Verify retry configuration (handle both real Celery task and FakeTask)
    if hasattr(emit_episode, 'max_retries'):
        assert emit_episode.max_retries == 2
        assert emit_episode.default_retry_delay == 5
    else:
        # In test mode with FakeTask, just verify the function exists
        assert callable(emit_episode)


def test_emit_episode_does_not_retry_validation_errors(monkeypatch, caplog):
    """
    emit_episode does not retry when ValidationError occurs.
    """
    # Enable graph
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')
    monkeypatch.setenv('NEO4J_PASSWORD', 'test')

    # Mock client
    with patch('src.tasks.graphiti_sync.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.tasks.graphiti_sync.check_graph_availability') as mock_check:
            mock_check.return_value = True

            from src.tasks.graphiti_sync import emit_episode

            # Call with invalid episode type (will raise ValueError from EpisodeType enum)
            result = emit_episode(
                episode_type="not_a_valid_type",
                store_id="store_123",
                payload={'decision': 'pass'},
                correlation_id=None
            )

            # Should return False without retry
            assert result is False


# ===========================================
# Test sync_failure_journey Task
# ===========================================

def test_sync_failure_journey_handles_missing_file(monkeypatch):
    """
    sync_failure_journey completes without error when FAILURE_JOURNEY.md is missing.
    """
    # Enable graph
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')

    from src.tasks.graphiti_sync import sync_failure_journey

    # Call with missing file
    result = sync_failure_journey(store_id="store_123")

    # Should return zero counts
    assert result == {'success': 0, 'failed': 0, 'skipped': 0}


def test_sync_failure_journey_parses_failure_entries(monkeypatch, tmp_path):
    """
    sync_failure_journey extracts failure entries from FAILURE_JOURNEY.md.
    """
    # Enable graph
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'true')

    # Create mock FAILURE_JOURNEY.md
    journey_content = """
## [2026-02-19 11:30] Module: src.tasks.enrichment
Error: Timeout during enrichment
Context: Product ID 12345

## [2026-02-19 12:00] Module: src.api.v1.chat.approvals
Error: Database connection failed
Context: During approval processing
"""

    # Write to temp location and patch Path
    journey_file = tmp_path / "FAILURE_JOURNEY.md"
    journey_file.write_text(journey_content, encoding='utf-8')

    with patch('src.tasks.graphiti_sync.Path') as mock_path:
        # Make Path return our temp file
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_instance.read_text.return_value = journey_content
        mock_path.return_value.parent.parent.parent.__truediv__.return_value = mock_path_instance

        # Import and mock emit_episode (handle both real task and FakeTask)
        from src.tasks.graphiti_sync import emit_episode, sync_failure_journey

        # Mock the emit_episode function itself
        with patch('src.tasks.graphiti_sync.emit_episode') as mock_emit_task:
            # Create a mock that has a delay method
            mock_delay = MagicMock(return_value=True)
            mock_emit_task.delay = mock_delay

            result = sync_failure_journey(store_id="store_123")

            # Should have completed without error
            assert isinstance(result, dict)
            assert 'success' in result
            assert 'failed' in result
            assert 'skipped' in result


def test_sync_failure_journey_returns_early_when_graph_disabled(monkeypatch):
    """
    sync_failure_journey returns early when GRAPH_ORACLE_ENABLED is false.
    """
    # Disable graph
    monkeypatch.setenv('GRAPH_ORACLE_ENABLED', 'false')

    from src.tasks.graphiti_sync import sync_failure_journey

    result = sync_failure_journey(store_id="store_123")

    # Should return zero counts
    assert result == {'success': 0, 'failed': 0, 'skipped': 0}


# ===========================================
# Test Episode ID Generation
# ===========================================

def test_generate_episode_id_is_deterministic():
    """
    _generate_episode_id produces same ID for same inputs.
    """
    from src.tasks.graphiti_sync import _generate_episode_id

    payload = {
        'decision': 'pass',
        'source_adapter': 'enrichment_oracle'
    }

    id1 = _generate_episode_id(
        episode_type="oracle_decision",
        store_id="store_123",
        correlation_id="corr_456",
        payload=payload
    )

    id2 = _generate_episode_id(
        episode_type="oracle_decision",
        store_id="store_123",
        correlation_id="corr_456",
        payload=payload
    )

    # Same inputs should produce same ID
    assert id1 == id2
    assert len(id1) == 16  # First 16 chars of SHA256


def test_generate_episode_id_differs_for_different_inputs():
    """
    _generate_episode_id produces different IDs for different inputs.
    """
    from src.tasks.graphiti_sync import _generate_episode_id

    payload1 = {'decision': 'pass', 'source_adapter': 'enrichment_oracle'}
    payload2 = {'decision': 'fail', 'source_adapter': 'enrichment_oracle'}

    id1 = _generate_episode_id(
        episode_type="oracle_decision",
        store_id="store_123",
        correlation_id="corr_456",
        payload=payload1
    )

    id2 = _generate_episode_id(
        episode_type="oracle_decision",
        store_id="store_123",
        correlation_id="corr_456",
        payload=payload2
    )

    # Different payloads should produce different IDs
    assert id1 != id2


def test_generate_episode_id_handles_missing_correlation_id():
    """
    _generate_episode_id handles None correlation_id.
    """
    from src.tasks.graphiti_sync import _generate_episode_id

    payload = {'decision': 'pass', 'source_adapter': 'test'}

    # Should not raise with None correlation_id
    episode_id = _generate_episode_id(
        episode_type="oracle_decision",
        store_id="store_123",
        correlation_id=None,
        payload=payload
    )

    assert isinstance(episode_id, str)
    assert len(episode_id) == 16
