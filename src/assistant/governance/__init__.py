"""Phase 13 governance services for verification, kill-switches, and field policy."""

from .field_policy import (
    FieldPolicyDecision,
    FieldPolicySnapshot,
    ensure_default_field_policy,
    evaluate_change_policy,
    get_field_policy_snapshot,
)
from .kill_switch import (
    KillSwitchBlockedError,
    KillSwitchDecision,
    assert_mutation_allowed,
    get_kill_switch_decision,
)
from .verification_oracle import (
    VerificationOutcome,
    process_deferred_verifications,
    verify_execution_finality,
)
from .graph_oracle_adapter import (
    GraphOracleAdapter,
    OracleSignal,  # Deprecated alias, kept for backward compatibility
    query_graph_evidence,
    FAIL_OPEN_SIGNAL,
)
# Import unified contract from canonical location
from src.core.enrichment.oracle_contract import OracleDecision

__all__ = [
    "FieldPolicyDecision",
    "FieldPolicySnapshot",
    "KillSwitchDecision",
    "KillSwitchBlockedError",
    "VerificationOutcome",
    "assert_mutation_allowed",
    "ensure_default_field_policy",
    "evaluate_change_policy",
    "get_field_policy_snapshot",
    "get_kill_switch_decision",
    "process_deferred_verifications",
    "verify_execution_finality",
    "GraphOracleAdapter",
    "OracleDecision",  # Unified Oracle contract
    "OracleSignal",  # Deprecated: Use OracleDecision instead
    "query_graph_evidence",
    "FAIL_OPEN_SIGNAL",
]

