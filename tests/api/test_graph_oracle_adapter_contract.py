"""
Contract tests for GraphOracleAdapter and fail-open behavior.

Tests mock graph client - no live Neo4j required.

Phase 13.2 - Oracle Framework Reuse
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.assistant.governance.graph_oracle_adapter import (
    GraphOracleAdapter,
    OracleSignal,
    FAIL_OPEN_SIGNAL,
    query_graph_evidence
)


# ===========================================
# Test Fail-Open Behavior
# ===========================================

def test_query_evidence_returns_fail_open_when_graph_unavailable():
    """
    query_evidence returns FAIL_OPEN_SIGNAL when graph is unavailable.
    """
    adapter = GraphOracleAdapter()

    # Mock check_graph_availability to return False
    with patch('src.assistant.governance.graph_oracle_adapter.check_graph_availability') as mock_check:
        mock_check.return_value = False

        # Mock get_graphiti_client to return valid client
        with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
            mock_get_client.return_value = MagicMock()

            signal = adapter.query_evidence(
                action_type='enrichment',
                target_module='src.tasks.enrichment',
                store_id='store_123'
            )

            # Should return fail-open signal
            assert signal == FAIL_OPEN_SIGNAL
            assert signal.decision == 'pass'
            assert signal.confidence == 0.5
            assert signal.reason_codes == []
            assert signal.evidence_refs == []
            assert signal.source == 'graph_unavailable'


def test_query_evidence_returns_fail_open_when_client_unavailable():
    """
    query_evidence returns FAIL_OPEN_SIGNAL when client cannot be initialized.
    """
    adapter = GraphOracleAdapter()

    # Mock get_graphiti_client to return None
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_get_client.return_value = None

        signal = adapter.query_evidence(
            action_type='enrichment',
            target_module='src.tasks.enrichment',
            store_id='store_123'
        )

        # Should return fail-open signal
        assert signal == FAIL_OPEN_SIGNAL


def test_query_evidence_returns_fail_open_on_error():
    """
    query_evidence returns FAIL_OPEN_SIGNAL when query raises exception.
    """
    adapter = GraphOracleAdapter()

    # Mock successful client init and availability check
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.assistant.governance.graph_oracle_adapter.check_graph_availability') as mock_check:
            mock_check.return_value = True

            # Mock query_failure_history to raise
            with patch.object(adapter, 'query_failure_history') as mock_query:
                mock_query.side_effect = Exception("Database connection error")

                signal = adapter.query_evidence(
                    action_type='enrichment',
                    target_module='src.tasks.enrichment',
                    store_id='store_123'
                )

                # Should return fail-open signal
                assert signal == FAIL_OPEN_SIGNAL


# ===========================================
# Test OracleSignal Contract
# ===========================================

def test_oracle_signal_has_required_fields():
    """
    OracleSignal has all required contract fields.
    """
    signal = OracleSignal(
        decision='pass',
        confidence=0.85,
        reason_codes=['no_failures_found'],
        evidence_refs=[],
        requires_user_action=False,
        source='graph'
    )

    # Verify required fields
    assert signal.decision == 'pass'
    assert signal.confidence == 0.85
    assert signal.reason_codes == ['no_failures_found']
    assert signal.evidence_refs == []
    assert signal.requires_user_action is False
    assert signal.source == 'graph'


def test_oracle_signal_is_immutable():
    """
    OracleSignal is frozen (immutable dataclass).
    """
    signal = OracleSignal(
        decision='pass',
        confidence=0.85,
        reason_codes=[],
        evidence_refs=[]
    )

    # Should not be able to modify fields
    with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
        signal.decision = 'fail'


def test_fail_open_signal_has_safe_defaults():
    """
    FAIL_OPEN_SIGNAL has safe default values.
    """
    assert FAIL_OPEN_SIGNAL.decision == 'pass'
    assert FAIL_OPEN_SIGNAL.confidence == 0.5
    assert FAIL_OPEN_SIGNAL.reason_codes == []
    assert FAIL_OPEN_SIGNAL.evidence_refs == []
    assert FAIL_OPEN_SIGNAL.requires_user_action is False
    assert FAIL_OPEN_SIGNAL.source == 'graph_unavailable'


# ===========================================
# Test Decision Logic
# ===========================================

def test_no_prior_failures_yields_pass_decision():
    """
    query_evidence returns 'pass' decision when no failures found.
    """
    adapter = GraphOracleAdapter()

    # Mock successful client and availability
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.assistant.governance.graph_oracle_adapter.check_graph_availability') as mock_check:
            mock_check.return_value = True

            # Mock query to return no failures
            with patch.object(adapter, 'query_failure_history') as mock_query:
                mock_query.return_value = []

                signal = adapter.query_evidence(
                    action_type='enrichment',
                    target_module='src.tasks.enrichment',
                    store_id='store_123'
                )

                # Should return pass decision
                assert signal.decision == 'pass'
                assert signal.confidence == 0.8
                assert 'no_failures_found' in signal.reason_codes
                assert signal.source == 'graph'


def test_prior_failures_yields_review_decision():
    """
    query_evidence returns 'review' decision when non-critical failures found.
    """
    adapter = GraphOracleAdapter()

    # Mock successful client and availability
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.assistant.governance.graph_oracle_adapter.check_graph_availability') as mock_check:
            mock_check.return_value = True

            # Mock query to return non-critical failures
            with patch.object(adapter, 'query_failure_history') as mock_query:
                mock_query.return_value = [
                    {'id': 'f1', 'failure_type': 'timeout'},
                    {'id': 'f2', 'failure_type': 'validation'},
                ]

                signal = adapter.query_evidence(
                    action_type='enrichment',
                    target_module='src.tasks.enrichment',
                    store_id='store_123'
                )

                # Should return review decision
                assert signal.decision == 'review'
                assert signal.confidence == 0.6
                assert 'prior_failures_detected' in signal.reason_codes
                assert len(signal.evidence_refs) == 2
                assert signal.requires_user_action is False


def test_critical_warnings_yields_fail_decision():
    """
    query_evidence returns 'fail' decision with critical failures.
    """
    adapter = GraphOracleAdapter()

    # Mock successful client and availability
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        with patch('src.assistant.governance.graph_oracle_adapter.check_graph_availability') as mock_check:
            mock_check.return_value = True

            # Mock query to return critical failures
            with patch.object(adapter, 'query_failure_history') as mock_query:
                mock_query.return_value = [
                    {'id': 'f1', 'failure_type': 'critical_error'},
                    {'id': 'f2', 'failure_type': 'data_loss'},
                ]

                signal = adapter.query_evidence(
                    action_type='remediation',
                    target_module='src.tasks.enrichment',
                    store_id='store_123'
                )

                # Should return fail decision
                assert signal.decision == 'fail'
                assert signal.confidence == 0.9
                assert 'critical_failures_detected' in signal.reason_codes
                assert len(signal.evidence_refs) == 2
                assert signal.requires_user_action is True


# ===========================================
# Test query_failure_history
# ===========================================

def test_query_failure_history_returns_empty_when_client_unavailable():
    """
    query_failure_history returns empty list when client unavailable.
    """
    adapter = GraphOracleAdapter()

    # Mock client to be unavailable
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_get_client.return_value = None

        failures = adapter.query_failure_history(
            module_path='src.tasks.enrichment',
            store_id='store_123',
            lookback_days=30
        )

        # Should return empty list (fail-open)
        assert failures == []


def test_query_failure_history_returns_empty_on_error():
    """
    query_failure_history returns empty list when query raises exception.
    """
    adapter = GraphOracleAdapter()

    # Mock successful client init
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_client = MagicMock()
        # Make client raise when accessed
        mock_client.search_episodes.side_effect = Exception("Query error")
        mock_get_client.return_value = mock_client

        failures = adapter.query_failure_history(
            module_path='src.tasks.enrichment',
            store_id='store_123',
            lookback_days=30
        )

        # Should return empty list (fail-open)
        assert failures == []


# ===========================================
# Test Module-Level Convenience Function
# ===========================================

def test_query_graph_evidence_uses_singleton_adapter():
    """
    query_graph_evidence uses singleton adapter instance.
    """
    # Reset singleton
    import src.assistant.governance.graph_oracle_adapter
    src.assistant.governance.graph_oracle_adapter._adapter = None

    # Mock get_graphiti_client
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_get_client.return_value = None

        # Call function twice
        signal1 = query_graph_evidence(
            action_type='enrichment',
            target_module='src.tasks.enrichment',
            store_id='store_123'
        )

        signal2 = query_graph_evidence(
            action_type='enrichment',
            target_module='src.tasks.enrichment',
            store_id='store_123'
        )

        # Both should return fail-open (since client is None)
        assert signal1 == FAIL_OPEN_SIGNAL
        assert signal2 == FAIL_OPEN_SIGNAL

        # Singleton should be created
        assert src.assistant.governance.graph_oracle_adapter._adapter is not None


def test_query_graph_evidence_respects_timeout():
    """
    query_graph_evidence respects timeout parameter.
    """
    # Reset singleton
    import src.assistant.governance.graph_oracle_adapter
    src.assistant.governance.graph_oracle_adapter._adapter = None

    # Mock get_graphiti_client
    with patch('src.assistant.governance.graph_oracle_adapter.get_graphiti_client') as mock_get_client:
        mock_get_client.return_value = None

        signal = query_graph_evidence(
            action_type='enrichment',
            target_module='src.tasks.enrichment',
            store_id='store_123',
            timeout=5.0
        )

        # Verify adapter was created with custom timeout
        adapter = src.assistant.governance.graph_oracle_adapter._adapter
        assert adapter.timeout == 5.0
