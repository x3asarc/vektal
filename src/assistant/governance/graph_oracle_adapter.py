"""
Graph-backed Oracle evidence adapter for governance decisions.

Provides timeout-bounded graph evidence retrieval with fail-open behavior.
Returns OracleDecision contract on success, falls back to safe default on timeout/error.

Uses unified Oracle contract from src.core.enrichment.oracle_contract.

Phase 13.2 - Oracle Framework Reuse
"""

from __future__ import annotations

import logging
from typing import List
from datetime import datetime, timedelta

# Import unified Oracle contract
from src.core.enrichment.oracle_contract import OracleDecision

logger = logging.getLogger(__name__)

# Lazy imports for graph client
try:
    from src.core.graphiti_client import get_graphiti_client, check_graph_availability, query_with_fallback
    from src.core.synthex_entities import EpisodeType
except ImportError:
    # Allow import to succeed even if graphiti not installed
    get_graphiti_client = None
    check_graph_availability = None
    query_with_fallback = None
    EpisodeType = None


# ===========================================
# Unified Oracle Contract
# ===========================================

# Deprecated alias for backward compatibility
OracleSignal = OracleDecision  # Deprecated: Use OracleDecision instead

# Fail-open signal returned when graph unavailable or query times out
FAIL_OPEN_SIGNAL = OracleDecision(
    decision='pass',
    confidence=0.5,
    reason_codes=(),
    evidence_refs=(),
    requires_user_action=False,
    source='graph_unavailable'
)


# ===========================================
# GraphOracleAdapter
# ===========================================

class GraphOracleAdapter:
    """
    Graph-backed Oracle evidence adapter with timeout-bounded queries.

    All queries complete within timeout or return fail-open signal.
    Graph unavailability does not block mutation flows.
    """

    def __init__(self, timeout_seconds: float = 2.0):
        """
        Initialize adapter with timeout configuration.

        Args:
            timeout_seconds: Maximum time for graph queries (default 2.0s)
        """
        self.timeout = timeout_seconds
        self.client = None  # Lazy init on first use

    def _ensure_client(self) -> bool:
        """
        Ensure graph client is initialized.

        Returns:
            bool: True if client available, False otherwise
        """
        if get_graphiti_client is None:
            logger.warning("Graphiti client not available - returning fail-open signal")
            return False

        if self.client is None:
            self.client = get_graphiti_client()

        return self.client is not None

    def query_evidence(
        self,
        action_type: str,
        target_module: str,
        store_id: str
    ) -> OracleDecision:
        """
        Query graph for evidence about proposed action.

        Returns OracleDecision with decision based on historical evidence:
        - No prior failures -> pass (confidence 0.8)
        - Prior failures exist -> review (confidence 0.6)
        - Critical warnings -> fail (confidence 0.9, requires user action)

        Args:
            action_type: Type of action (e.g., 'optimization', 'remediation', 'enrichment')
            target_module: Python module path being acted upon
            store_id: Store ID for multi-tenant filtering

        Returns:
            OracleDecision with decision and evidence references
        """
        # Check graph availability
        if not self._ensure_client():
            return FAIL_OPEN_SIGNAL

        if check_graph_availability is None or not check_graph_availability(timeout_seconds=self.timeout):
            logger.warning("Graph unavailable - returning fail-open signal")
            return FAIL_OPEN_SIGNAL

        try:
            # Query for failure patterns
            failures = self.query_failure_history(
                module_path=target_module,
                store_id=store_id,
                lookback_days=30
            )

            if not failures:
                # No prior failures - safe to proceed
                return OracleDecision(
                    decision='pass',
                    confidence=0.8,
                    reason_codes=('no_failures_found',),
                    evidence_refs=(),
                    requires_user_action=False,
                    source='graph'
                )

            # Check for critical failures
            critical_failures = [
                f for f in failures
                if f.get('failure_type') in ['critical_error', 'data_loss', 'security_breach']
            ]

            if critical_failures:
                return OracleDecision(
                    decision='fail',
                    confidence=0.9,
                    reason_codes=('critical_failures_detected',),
                    evidence_refs=tuple(f"failure_{f.get('id')}" for f in critical_failures[:5]),
                    requires_user_action=True,
                    source='graph'
                )

            # Non-critical failures - suggest review
            return OracleDecision(
                decision='review',
                confidence=0.6,
                reason_codes=('prior_failures_detected',),
                evidence_refs=tuple(f"failure_{f.get('id')}" for f in failures[:5]),
                requires_user_action=False,
                source='graph'
            )

        except Exception as e:
            logger.warning(f"Graph evidence query failed: {e} - returning fail-open signal")
            return FAIL_OPEN_SIGNAL

    def query_failure_history(
        self,
        module_path: str,
        store_id: str,
        lookback_days: int = 30
    ) -> List[dict]:
        """
        Query failure pattern episodes for module.

        Args:
            module_path: Python module path to query
            store_id: Store ID for multi-tenant filtering
            lookback_days: How far back to look for failures (default 30 days)

        Returns:
            List of failure records with timestamps, or empty list on error
        """
        if not self._ensure_client():
            return []

        try:
            # Build time window
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

            # Query for failure_pattern episodes
            # Note: Actual Graphiti query implementation would go here
            # For now, return empty list as fail-open
            # This will be populated when Phase 13.2-02 adds emission hooks

            logger.debug(f"Querying failure history for {module_path} since {cutoff_date}")

            # Placeholder - actual query would use Graphiti client
            # failures = await self.client.search_episodes(
            #     episode_type='failure_pattern',
            #     filters={'module_path': module_path, 'store_id': store_id},
            #     time_range={'start': cutoff_date}
            # )

            return []  # Fail-open: no failures found

        except Exception as e:
            logger.warning(f"Failure history query failed: {e} - returning empty list")
            return []  # Fail-open


# ===========================================
# Module-level convenience function
# ===========================================

# Singleton adapter instance
_adapter: GraphOracleAdapter | None = None


def query_graph_evidence(
    action_type: str,
    target_module: str,
    store_id: str,
    timeout: float = 2.0
) -> OracleDecision:
    """
    Convenience function for graph evidence queries.

    Uses singleton adapter instance.

    Args:
        action_type: Type of action being evaluated
        target_module: Module being acted upon
        store_id: Store ID for filtering
        timeout: Query timeout in seconds (default 2.0)

    Returns:
        OracleDecision with decision and evidence

    Example:
        >>> signal = query_graph_evidence(
        ...     action_type='enrichment',
        ...     target_module='src.tasks.enrichment',
        ...     store_id='store_123'
        ... )
        >>> if signal.decision == 'fail':
        ...     # Escalate to user
    """
    global _adapter

    if _adapter is None:
        _adapter = GraphOracleAdapter(timeout_seconds=timeout)

    return _adapter.query_evidence(
        action_type=action_type,
        target_module=target_module,
        store_id=store_id
    )
