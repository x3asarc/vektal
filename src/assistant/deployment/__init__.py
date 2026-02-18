"""Phase 13 deployment services (provider routing, observability, redaction)."""

from .canary_guard import CanaryDecision, evaluate_canary_rollback
from .observability import (
    AVAILABILITY_TARGET,
    ERROR_BUDGET_SECONDS_30D,
    AvailabilityComputation,
    compute_availability_sli,
    resolve_correlation_id,
)
from .provider_router import (
    DeploymentPolicySnapshot,
    ProviderRouteDecision,
    ensure_default_deployment_policy,
    get_deployment_policy_snapshot,
    persist_provider_route_event,
    resolve_provider_route,
)
from .redaction import (
    AUDIT_RETENTION_DAYS,
    BACKUP_PURGE_DAYS,
    LIVE_PURGE_HOURS,
    TRACE_RETENTION_DAYS,
    purge_deadline,
    redact_structured,
    redact_unstructured,
    retention_contract_snapshot,
    retention_deadline,
)

__all__ = [
    "AVAILABILITY_TARGET",
    "ERROR_BUDGET_SECONDS_30D",
    "AUDIT_RETENTION_DAYS",
    "BACKUP_PURGE_DAYS",
    "LIVE_PURGE_HOURS",
    "TRACE_RETENTION_DAYS",
    "AvailabilityComputation",
    "CanaryDecision",
    "DeploymentPolicySnapshot",
    "ProviderRouteDecision",
    "compute_availability_sli",
    "ensure_default_deployment_policy",
    "evaluate_canary_rollback",
    "get_deployment_policy_snapshot",
    "persist_provider_route_event",
    "purge_deadline",
    "redact_structured",
    "redact_unstructured",
    "resolve_correlation_id",
    "resolve_provider_route",
    "retention_contract_snapshot",
    "retention_deadline",
]

