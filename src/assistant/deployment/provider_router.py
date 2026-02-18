"""Provider ladder routing and fallback-stage persistence helpers."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from src.models import (
    AssistantDeploymentPolicy,
    AssistantProviderRouteEvent,
    db,
)


DEFAULT_PROVIDER_LADDER = [
    {"provider": "qwen", "model": "qwen-2.5-coder", "tier_scope": "tier_1,tier_2"},
    {
        "provider": "openrouter",
        "model": "anthropic/claude-3.5-sonnet",
        "tier_scope": "tier_2,tier_3",
    },
    {"provider": "openrouter", "model": "openai/gpt-4o", "tier_scope": "tier_3"},
]
FALLBACK_FAILURE_CODES = {
    "provider_unavailable",
    "invalid_tool_call",
    "budget_guard",
    "policy_block",
    "latency_guard",
}


@dataclass(frozen=True)
class DeploymentPolicySnapshot:
    policy_id: int | None
    scope_kind: str
    policy_version: int
    store_id: int | None
    primary_provider: str
    primary_model: str
    provider_ladder: list[dict[str, Any]]
    budget_guard_percent: float
    policy_snapshot_hash: str


@dataclass(frozen=True)
class ProviderRouteDecision:
    correlation_id: str
    selected_provider: str
    selected_model: str
    route_stage: str
    route_index: int
    fallback_reason_code: str
    policy_snapshot_hash: str
    route_metadata: dict[str, Any]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_payload(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_ladder(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        output = []
        for item in value:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or "").strip()
            model = str(item.get("model") or "").strip()
            if not provider or not model:
                continue
            output.append(
                {
                    "provider": provider,
                    "model": model,
                    "tier_scope": str(item.get("tier_scope") or "tier_1,tier_2,tier_3"),
                }
            )
        if output:
            return output
    return list(DEFAULT_PROVIDER_LADDER)


def _tier_allowed(item: dict[str, Any], tier: str) -> bool:
    tier_scope = str(item.get("tier_scope") or "tier_1,tier_2,tier_3")
    allowed = {part.strip().lower() for part in tier_scope.split(",") if part.strip()}
    return tier.lower() in allowed


def _snapshot_from_row(row: AssistantDeploymentPolicy) -> DeploymentPolicySnapshot:
    ladder = _normalize_ladder(row.provider_ladder_json)
    payload = {
        "scope_kind": row.scope_kind,
        "store_id": row.store_id,
        "policy_version": row.policy_version,
        "primary_provider": row.primary_provider,
        "primary_model": row.primary_model,
        "provider_ladder": ladder,
        "budget_guard_percent": row.budget_guard_percent,
    }
    return DeploymentPolicySnapshot(
        policy_id=row.id,
        scope_kind=row.scope_kind,
        policy_version=row.policy_version,
        store_id=row.store_id,
        primary_provider=row.primary_provider,
        primary_model=row.primary_model,
        provider_ladder=ladder,
        budget_guard_percent=float(row.budget_guard_percent),
        policy_snapshot_hash=_hash_payload(payload),
    )


def _fallback_snapshot(*, store_id: int | None = None) -> DeploymentPolicySnapshot:
    payload = {
        "scope_kind": "global",
        "store_id": store_id,
        "policy_version": 1,
        "primary_provider": "qwen",
        "primary_model": "qwen-2.5-coder",
        "provider_ladder": list(DEFAULT_PROVIDER_LADDER),
        "budget_guard_percent": 95.0,
    }
    return DeploymentPolicySnapshot(
        policy_id=None,
        scope_kind="global",
        policy_version=1,
        store_id=store_id,
        primary_provider="qwen",
        primary_model="qwen-2.5-coder",
        provider_ladder=list(DEFAULT_PROVIDER_LADDER),
        budget_guard_percent=95.0,
        policy_snapshot_hash=_hash_payload(payload),
    )


def ensure_default_deployment_policy(*, changed_by_id: int | None = None) -> AssistantDeploymentPolicy:
    """Ensure global deployment policy exists."""
    existing = (
        AssistantDeploymentPolicy.query.filter_by(
            scope_kind="global",
            store_id=None,
            policy_version=1,
        )
        .order_by(AssistantDeploymentPolicy.id.asc())
        .first()
    )
    if existing is not None:
        return existing
    row = AssistantDeploymentPolicy(
        scope_kind="global",
        store_id=None,
        policy_version=1,
        is_active=True,
        effective_at=_now(),
        changed_by_id=changed_by_id,
        primary_provider="qwen",
        primary_model="qwen-2.5-coder",
        provider_ladder_json=list(DEFAULT_PROVIDER_LADDER),
        budget_guard_percent=95.0,
    )
    db.session.add(row)
    db.session.commit()
    return row


def get_deployment_policy_snapshot(*, store_id: int | None, allow_fallback: bool = True) -> DeploymentPolicySnapshot:
    """Resolve most specific active deployment policy (tenant first, then global)."""
    now_utc = _now()
    try:
        if store_id is not None:
            tenant = (
                AssistantDeploymentPolicy.query.filter(
                    AssistantDeploymentPolicy.scope_kind == "tenant",
                    AssistantDeploymentPolicy.store_id == store_id,
                    AssistantDeploymentPolicy.is_active.is_(True),
                    AssistantDeploymentPolicy.effective_at <= now_utc,
                )
                .order_by(AssistantDeploymentPolicy.policy_version.desc(), AssistantDeploymentPolicy.id.desc())
                .first()
            )
            if tenant is not None:
                return _snapshot_from_row(tenant)

        global_row = (
            AssistantDeploymentPolicy.query.filter(
                AssistantDeploymentPolicy.scope_kind == "global",
                AssistantDeploymentPolicy.store_id.is_(None),
                AssistantDeploymentPolicy.is_active.is_(True),
                AssistantDeploymentPolicy.effective_at <= now_utc,
            )
            .order_by(AssistantDeploymentPolicy.policy_version.desc(), AssistantDeploymentPolicy.id.desc())
            .first()
        )
        if global_row is not None:
            return _snapshot_from_row(global_row)
    except Exception:
        if allow_fallback:
            return _fallback_snapshot(store_id=store_id)
        raise

    if not allow_fallback:
        raise LookupError("No active deployment policy found.")
    return _fallback_snapshot(store_id=store_id)


def resolve_provider_route(
    *,
    correlation_id: str,
    store_id: int | None,
    intent_type: str,
    tier: str,
    failure_stage: str | None = None,
    budget_percent: float | None = None,
    snapshot: DeploymentPolicySnapshot | None = None,
) -> ProviderRouteDecision:
    """Resolve deterministic provider route from policy ladder + failure signals."""
    snapshot = snapshot or get_deployment_policy_snapshot(store_id=store_id)
    ladder = [item for item in snapshot.provider_ladder if _tier_allowed(item, tier)]
    if not ladder:
        ladder = list(DEFAULT_PROVIDER_LADDER)

    route_stage = "primary"
    route_index = 0
    fallback_reason = "none"

    normalized_failure = str(failure_stage or "").strip().lower()
    budget = float(budget_percent) if isinstance(budget_percent, (int, float)) else None
    if budget is not None and budget >= snapshot.budget_guard_percent and len(ladder) > 1:
        route_stage = "budget_guard"
        route_index = len(ladder) - 1
        fallback_reason = "budget_guard"
    elif normalized_failure in FALLBACK_FAILURE_CODES and len(ladder) > 1:
        route_stage = "fallback"
        route_index = 1
        fallback_reason = normalized_failure
    elif normalized_failure and normalized_failure not in FALLBACK_FAILURE_CODES and len(ladder) > 1:
        route_stage = "fallback"
        route_index = 1
        fallback_reason = "provider_unavailable"

    selected = ladder[min(route_index, len(ladder) - 1)]
    metadata = {
        "intent_type": intent_type,
        "tier": tier,
        "failure_stage": normalized_failure or None,
        "budget_percent": budget,
        "ladder_size": len(ladder),
        "policy_scope": snapshot.scope_kind,
        "policy_version": snapshot.policy_version,
    }
    return ProviderRouteDecision(
        correlation_id=correlation_id,
        selected_provider=str(selected["provider"]),
        selected_model=str(selected["model"]),
        route_stage=route_stage,
        route_index=route_index,
        fallback_reason_code=fallback_reason,
        policy_snapshot_hash=snapshot.policy_snapshot_hash,
        route_metadata=metadata,
    )


def persist_provider_route_event(
    *,
    decision: ProviderRouteDecision,
    user_id: int | None,
    store_id: int | None,
    session_id: int | None,
    action_id: int | None,
    route_event_id: int | None,
    intent_type: str,
) -> AssistantProviderRouteEvent:
    """Persist provider route telemetry row."""
    row = AssistantProviderRouteEvent(
        correlation_id=decision.correlation_id,
        user_id=user_id,
        store_id=store_id,
        session_id=session_id,
        action_id=action_id,
        route_event_id=route_event_id,
        intent_type=intent_type,
        route_stage=decision.route_stage,
        route_index=decision.route_index,
        selected_provider=decision.selected_provider,
        selected_model=decision.selected_model,
        fallback_reason_code=decision.fallback_reason_code,
        policy_snapshot_hash=decision.policy_snapshot_hash,
        route_metadata_json=decision.route_metadata,
    )
    db.session.add(row)
    return row

