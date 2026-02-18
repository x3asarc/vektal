"""Phase 13 instrumentation signal capture helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.models import (
    AssistantPreferenceSignal,
    AssistantVerificationSignal,
    ChatAction,
    db,
)


MANDATORY_CORRELATION_TIERS = {"tier_2", "tier_3"}


class InstrumentationLinkError(ValueError):
    """Raised when mandatory correlation linkage is missing."""


@dataclass(frozen=True)
class ActionRuntimeContext:
    tier: str
    correlation_id: str | None
    reasoning_trace_tokens: int | None
    cost_usd: float | None


def _normalized_tier(value: str | None) -> str:
    candidate = str(value or "").strip().lower()
    if candidate in {"tier_1", "tier_2", "tier_3"}:
        return candidate
    return "tier_1"


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(float(value.strip()))
        except ValueError:
            return None
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def extract_action_runtime_context(action: ChatAction, *, fallback_tier: str | None = None) -> ActionRuntimeContext:
    """Extract normalized instrumentation context from action payload runtime metadata."""
    payload = action.payload_json if isinstance(action.payload_json, dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}

    tier = _normalized_tier(
        runtime.get("tier")
        or runtime.get("route_decision")
        or payload.get("tier")
        or fallback_tier
    )
    correlation_id = (
        str(runtime.get("correlation_id") or payload.get("correlation_id") or "").strip() or None
    )
    tokens = _to_int(runtime.get("reasoning_trace_tokens") or payload.get("reasoning_trace_tokens"))
    cost = _to_float(runtime.get("cost_usd") or payload.get("cost_usd"))

    return ActionRuntimeContext(
        tier=tier,
        correlation_id=correlation_id,
        reasoning_trace_tokens=tokens,
        cost_usd=cost,
    )


def _assert_correlation_link(*, tier: str, correlation_id: str | None) -> None:
    if tier in MANDATORY_CORRELATION_TIERS and not correlation_id:
        raise InstrumentationLinkError(
            "Missing correlation_id for mandatory Tier 2/3 instrumentation path."
        )


def capture_preference_signal(
    *,
    action: ChatAction,
    user_id: int | None,
    store_id: int | None,
    session_id: int | None,
    preference_signal: str,
    signal_kind: str = "approval",
    selected_change_count: int = 0,
    override_count: int = 0,
    comment: str | None = None,
    tier: str | None = None,
    correlation_id: str | None = None,
    reasoning_trace_tokens: int | None = None,
    cost_usd: float | None = None,
    metadata_json: dict[str, Any] | None = None,
    require_link: bool = True,
) -> AssistantPreferenceSignal:
    """Persist preference/feedback signal for joinable instrumentation lineage."""
    runtime = extract_action_runtime_context(action, fallback_tier=tier)
    resolved_tier = _normalized_tier(tier or runtime.tier)
    resolved_correlation = str(correlation_id or runtime.correlation_id or "").strip() or None
    if require_link:
        _assert_correlation_link(tier=resolved_tier, correlation_id=resolved_correlation)

    row = AssistantPreferenceSignal(
        action_id=action.id,
        session_id=session_id,
        store_id=store_id,
        user_id=user_id,
        correlation_id=resolved_correlation,
        tier=resolved_tier,
        signal_kind=signal_kind,
        preference_signal=preference_signal,
        selected_change_count=max(0, int(selected_change_count)),
        override_count=max(0, int(override_count)),
        comment=comment,
        reasoning_trace_tokens=(
            _to_int(reasoning_trace_tokens)
            if reasoning_trace_tokens is not None
            else runtime.reasoning_trace_tokens
        ),
        cost_usd=(
            _to_float(cost_usd)
            if cost_usd is not None
            else runtime.cost_usd
        ),
        metadata_json=metadata_json or {},
    )
    db.session.add(row)
    return row


def capture_verification_signal(
    *,
    action: ChatAction,
    user_id: int | None,
    store_id: int | None,
    session_id: int | None,
    verification_status: str,
    oracle_signal: bool,
    verification_event_id: int | None = None,
    attempt_count: int = 1,
    waited_seconds: int = 0,
    tier: str | None = None,
    correlation_id: str | None = None,
    reasoning_trace_tokens: int | None = None,
    cost_usd: float | None = None,
    metadata_json: dict[str, Any] | None = None,
    require_link: bool = True,
) -> AssistantVerificationSignal:
    """Persist binary oracle verification signal for downstream correctness joins."""
    runtime = extract_action_runtime_context(action, fallback_tier=tier)
    resolved_tier = _normalized_tier(tier or runtime.tier)
    resolved_correlation = str(correlation_id or runtime.correlation_id or "").strip() or None
    if require_link:
        _assert_correlation_link(tier=resolved_tier, correlation_id=resolved_correlation)
    if not resolved_correlation:
        raise InstrumentationLinkError("Verification signal requires correlation_id.")

    normalized_status = str(verification_status or "").strip().lower()
    if normalized_status not in {"verified", "deferred", "failed"}:
        normalized_status = "deferred"

    row = AssistantVerificationSignal(
        action_id=action.id,
        session_id=session_id,
        store_id=store_id,
        user_id=user_id,
        verification_event_id=verification_event_id,
        correlation_id=resolved_correlation,
        tier=resolved_tier,
        verification_status=normalized_status,
        oracle_signal=bool(oracle_signal),
        attempt_count=max(1, int(attempt_count)),
        waited_seconds=max(0, int(waited_seconds)),
        reasoning_trace_tokens=(
            _to_int(reasoning_trace_tokens)
            if reasoning_trace_tokens is not None
            else runtime.reasoning_trace_tokens
        ),
        cost_usd=(
            _to_float(cost_usd)
            if cost_usd is not None
            else runtime.cost_usd
        ),
        metadata_json=metadata_json or {},
    )
    db.session.add(row)
    return row
