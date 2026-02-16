"""Runtime reliability policy lookup and persistence helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, or_

from src.models import AssistantRuntimePolicy, db


DEFAULT_RETRY_POLICY = {
    "rate_limit": {"max_retries": 3, "strategy": "exponential_jitter"},
    "server_error": {"max_retries": 2, "strategy": "linear"},
    "timeout": {"max_retries": 1, "strategy": "timeout_multiplier"},
    "connectivity": {"max_retries": 3, "strategy": "immediate"},
    "schema_validation": {"max_retries": 1, "strategy": "reflexive_fixer"},
}


@dataclass(frozen=True)
class RuntimePolicySnapshot:
    """Resolved runtime policy and breaker state snapshot."""

    policy_id: int | None
    policy_version: int
    scope_kind: str
    provider_name: str | None
    skill_name: str | None
    breaker_state: str
    breaker_error_count: int
    breaker_request_count: int
    breaker_consecutive_successes: int
    breaker_last_failure_at: datetime | None
    breaker_last_success_at: datetime | None
    breaker_opened_at: datetime | None
    breaker_error_rate_threshold: float
    breaker_latency_p95_tier12_seconds: float
    breaker_latency_p95_tier3_seconds: float
    breaker_window_seconds: int
    breaker_min_sample_size: int
    breaker_open_cooldown_seconds: int
    breaker_half_open_successes: int
    retry_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "scope_kind": self.scope_kind,
            "provider_name": self.provider_name,
            "skill_name": self.skill_name,
            "breaker_state": self.breaker_state,
            "breaker_error_count": self.breaker_error_count,
            "breaker_request_count": self.breaker_request_count,
            "breaker_consecutive_successes": self.breaker_consecutive_successes,
            "breaker_last_failure_at": self.breaker_last_failure_at.isoformat()
            if self.breaker_last_failure_at
            else None,
            "breaker_last_success_at": self.breaker_last_success_at.isoformat()
            if self.breaker_last_success_at
            else None,
            "breaker_opened_at": self.breaker_opened_at.isoformat() if self.breaker_opened_at else None,
            "breaker_error_rate_threshold": self.breaker_error_rate_threshold,
            "breaker_latency_p95_tier12_seconds": self.breaker_latency_p95_tier12_seconds,
            "breaker_latency_p95_tier3_seconds": self.breaker_latency_p95_tier3_seconds,
            "breaker_window_seconds": self.breaker_window_seconds,
            "breaker_min_sample_size": self.breaker_min_sample_size,
            "breaker_open_cooldown_seconds": self.breaker_open_cooldown_seconds,
            "breaker_half_open_successes": self.breaker_half_open_successes,
            "retry_policy": self.retry_policy,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fallback_snapshot(
    *,
    provider_name: str | None = None,
    skill_name: str | None = None,
) -> RuntimePolicySnapshot:
    return RuntimePolicySnapshot(
        policy_id=None,
        policy_version=1,
        scope_kind="global",
        provider_name=provider_name,
        skill_name=skill_name,
        breaker_state="closed",
        breaker_error_count=0,
        breaker_request_count=0,
        breaker_consecutive_successes=0,
        breaker_last_failure_at=None,
        breaker_last_success_at=None,
        breaker_opened_at=None,
        breaker_error_rate_threshold=0.25,
        breaker_latency_p95_tier12_seconds=15.0,
        breaker_latency_p95_tier3_seconds=45.0,
        breaker_window_seconds=300,
        breaker_min_sample_size=10,
        breaker_open_cooldown_seconds=60,
        breaker_half_open_successes=3,
        retry_policy=dict(DEFAULT_RETRY_POLICY),
    )


def _specificity_score(policy: AssistantRuntimePolicy, *, provider_name: str | None, skill_name: str | None) -> int:
    if policy.scope_kind == "provider_skill":
        return 4 if policy.provider_name == provider_name and policy.skill_name == skill_name else -1
    if policy.scope_kind == "provider":
        return 3 if policy.provider_name == provider_name else -1
    if policy.scope_kind == "skill":
        return 2 if policy.skill_name == skill_name else -1
    if policy.scope_kind == "global":
        return 1
    return -1


def _snapshot_from_policy(policy: AssistantRuntimePolicy) -> RuntimePolicySnapshot:
    retry_policy = policy.retry_policy_json if isinstance(policy.retry_policy_json, dict) else {}
    if not retry_policy:
        retry_policy = dict(DEFAULT_RETRY_POLICY)
    return RuntimePolicySnapshot(
        policy_id=policy.id,
        policy_version=policy.policy_version,
        scope_kind=policy.scope_kind,
        provider_name=policy.provider_name,
        skill_name=policy.skill_name,
        breaker_state=policy.breaker_state,
        breaker_error_count=policy.breaker_error_count,
        breaker_request_count=policy.breaker_request_count,
        breaker_consecutive_successes=policy.breaker_consecutive_successes,
        breaker_last_failure_at=policy.breaker_last_failure_at,
        breaker_last_success_at=policy.breaker_last_success_at,
        breaker_opened_at=policy.breaker_opened_at,
        breaker_error_rate_threshold=policy.breaker_error_rate_threshold,
        breaker_latency_p95_tier12_seconds=policy.breaker_latency_p95_tier12_seconds,
        breaker_latency_p95_tier3_seconds=policy.breaker_latency_p95_tier3_seconds,
        breaker_window_seconds=policy.breaker_window_seconds,
        breaker_min_sample_size=policy.breaker_min_sample_size,
        breaker_open_cooldown_seconds=policy.breaker_open_cooldown_seconds,
        breaker_half_open_successes=policy.breaker_half_open_successes,
        retry_policy=retry_policy,
    )


def ensure_default_runtime_policy(*, changed_by_id: int | None = None) -> AssistantRuntimePolicy:
    """Ensure the global default policy exists."""
    existing = (
        AssistantRuntimePolicy.query.filter_by(
            scope_kind="global",
            provider_name=None,
            skill_name=None,
            policy_version=1,
        )
        .order_by(AssistantRuntimePolicy.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    policy = AssistantRuntimePolicy(
        scope_kind="global",
        policy_version=1,
        is_active=True,
        effective_at=_now(),
        changed_by_id=changed_by_id,
        retry_policy_json=dict(DEFAULT_RETRY_POLICY),
    )
    db.session.add(policy)
    db.session.commit()
    return policy


def get_runtime_policy_snapshot(
    *,
    provider_name: str | None = None,
    skill_name: str | None = None,
    now_utc: datetime | None = None,
    allow_fallback: bool = True,
) -> RuntimePolicySnapshot:
    """
    Resolve the most specific active policy snapshot.

    Falls back to a static policy when database/app context is unavailable.
    """
    now_utc = now_utc or _now()
    try:
        candidates = (
            AssistantRuntimePolicy.query.filter(
                and_(
                    AssistantRuntimePolicy.is_active.is_(True),
                    AssistantRuntimePolicy.effective_at <= now_utc,
                    or_(
                        AssistantRuntimePolicy.scope_kind == "global",
                        AssistantRuntimePolicy.scope_kind == "provider",
                        AssistantRuntimePolicy.scope_kind == "skill",
                        AssistantRuntimePolicy.scope_kind == "provider_skill",
                    ),
                )
            )
            .order_by(
                AssistantRuntimePolicy.policy_version.desc(),
                AssistantRuntimePolicy.effective_at.desc(),
                AssistantRuntimePolicy.id.desc(),
            )
            .all()
        )
    except Exception:
        if allow_fallback:
            return _fallback_snapshot(provider_name=provider_name, skill_name=skill_name)
        raise

    ranked: list[tuple[int, AssistantRuntimePolicy]] = []
    for policy in candidates:
        score = _specificity_score(policy, provider_name=provider_name, skill_name=skill_name)
        if score >= 0:
            ranked.append((score, policy))

    if ranked:
        ranked.sort(key=lambda item: (item[0], item[1].policy_version, item[1].effective_at), reverse=True)
        return _snapshot_from_policy(ranked[0][1])

    if not allow_fallback:
        raise LookupError("No active runtime policy found.")
    return _fallback_snapshot(provider_name=provider_name, skill_name=skill_name)


def persist_breaker_state(
    *,
    policy_id: int | None,
    breaker_state: str,
    error_count: int,
    request_count: int,
    consecutive_successes: int,
    opened_at: datetime | None,
    last_failure_at: datetime | None,
    last_success_at: datetime | None,
) -> None:
    """Persist breaker counters when policy is database-backed."""
    if policy_id is None:
        return
    policy = AssistantRuntimePolicy.query.get(policy_id)
    if policy is None:
        return
    policy.breaker_state = breaker_state
    policy.breaker_error_count = max(0, int(error_count))
    policy.breaker_request_count = max(0, int(request_count))
    policy.breaker_consecutive_successes = max(0, int(consecutive_successes))
    policy.breaker_opened_at = opened_at
    policy.breaker_last_failure_at = last_failure_at
    policy.breaker_last_success_at = last_success_at
    db.session.commit()


def retry_limit_for_class(snapshot: RuntimePolicySnapshot, error_class: str, *, default: int = 1) -> int:
    """Return configured retry budget for a given error class."""
    retry_policy = snapshot.retry_policy if isinstance(snapshot.retry_policy, dict) else {}
    row = retry_policy.get(error_class, {})
    if not isinstance(row, dict):
        return default
    raw = row.get("max_retries")
    try:
        value = int(raw)
    except Exception:
        return default
    return max(0, value)
