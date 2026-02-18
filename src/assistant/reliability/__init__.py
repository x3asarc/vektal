"""Phase 13 reliability services for policy, breakers, retry, and idempotency."""

from .breakers import BreakerDecision, evaluate_breaker_gate, evaluate_failure_transition
from .idempotency import (
    IdempotencyClaim,
    build_idempotency_key,
    claim_execution_slot,
    compute_payload_hash,
    mark_execution_failed,
    mark_execution_success,
    reset_failed_execution,
)
from .policy_store import RuntimePolicySnapshot, ensure_default_runtime_policy, get_runtime_policy_snapshot
from .retry_matrix import RetryDecision, classify_retry_class, evaluate_retry_decision

__all__ = [
    "BreakerDecision",
    "RetryDecision",
    "RuntimePolicySnapshot",
    "IdempotencyClaim",
    "build_idempotency_key",
    "claim_execution_slot",
    "classify_retry_class",
    "compute_payload_hash",
    "ensure_default_runtime_policy",
    "evaluate_breaker_gate",
    "evaluate_failure_transition",
    "evaluate_retry_decision",
    "get_runtime_policy_snapshot",
    "mark_execution_failed",
    "mark_execution_success",
    "reset_failed_execution",
]

