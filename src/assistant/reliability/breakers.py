"""Circuit-breaker gate and transition helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.assistant.reliability.policy_store import RuntimePolicySnapshot


@dataclass(frozen=True)
class BreakerDecision:
    """One gate decision for the current breaker state."""

    current_state: str
    next_state: str
    allow_request: bool
    reason: str
    cooldown_remaining_seconds: int = 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_breaker_gate(
    *,
    snapshot: RuntimePolicySnapshot,
    now_utc: datetime | None = None,
) -> BreakerDecision:
    """Decide whether request admission is allowed for current breaker state."""
    now_utc = now_utc or _now()
    state = snapshot.breaker_state
    if state == "open":
        opened_at = snapshot.breaker_opened_at
        if opened_at is None:
            return BreakerDecision(
                current_state=state,
                next_state="half_open",
                allow_request=True,
                reason="open_without_timestamp_promoted_to_half_open",
            )
        elapsed = max(0.0, (now_utc - opened_at).total_seconds())
        cooldown = float(snapshot.breaker_open_cooldown_seconds)
        if elapsed >= cooldown:
            return BreakerDecision(
                current_state=state,
                next_state="half_open",
                allow_request=True,
                reason="cooldown_elapsed",
            )
        remaining = int(round(cooldown - elapsed))
        return BreakerDecision(
            current_state=state,
            next_state="open",
            allow_request=False,
            reason="cooldown_active",
            cooldown_remaining_seconds=max(0, remaining),
        )
    if state == "half_open":
        return BreakerDecision(
            current_state=state,
            next_state="half_open",
            allow_request=True,
            reason="half_open_probe",
        )
    return BreakerDecision(
        current_state=state,
        next_state="closed",
        allow_request=True,
        reason="closed",
    )


def evaluate_failure_transition(
    *,
    snapshot: RuntimePolicySnapshot,
    observed_latency_p95_seconds: float | None = None,
    now_utc: datetime | None = None,
    tier: str = "tier_2",
) -> BreakerDecision:
    """
    Compute deterministic breaker state after one execution failure.

    Fails in `half_open` always trip to `open`.
    In `closed`, trip only after minimum sample and threshold breach.
    """
    now_utc = now_utc or _now()
    current_state = snapshot.breaker_state
    if current_state == "half_open":
        return BreakerDecision(
            current_state=current_state,
            next_state="open",
            allow_request=False,
            reason="half_open_failure_trip",
            cooldown_remaining_seconds=snapshot.breaker_open_cooldown_seconds,
        )
    if current_state == "open":
        return BreakerDecision(
            current_state=current_state,
            next_state="open",
            allow_request=False,
            reason="already_open",
            cooldown_remaining_seconds=snapshot.breaker_open_cooldown_seconds,
        )

    projected_requests = snapshot.breaker_request_count + 1
    projected_errors = snapshot.breaker_error_count + 1
    if projected_requests < snapshot.breaker_min_sample_size:
        return BreakerDecision(
            current_state=current_state,
            next_state="closed",
            allow_request=True,
            reason="min_sample_not_reached",
        )

    error_rate = projected_errors / float(max(1, projected_requests))
    latency_threshold = (
        snapshot.breaker_latency_p95_tier3_seconds
        if tier == "tier_3"
        else snapshot.breaker_latency_p95_tier12_seconds
    )
    latency_breach = (
        observed_latency_p95_seconds is not None
        and observed_latency_p95_seconds > latency_threshold
    )
    error_rate_breach = error_rate > snapshot.breaker_error_rate_threshold
    if error_rate_breach or latency_breach:
        reason = "error_rate_threshold_breach" if error_rate_breach else "latency_threshold_breach"
        return BreakerDecision(
            current_state=current_state,
            next_state="open",
            allow_request=False,
            reason=reason,
            cooldown_remaining_seconds=snapshot.breaker_open_cooldown_seconds,
        )
    return BreakerDecision(
        current_state=current_state,
        next_state="closed",
        allow_request=True,
        reason="threshold_not_breached",
    )

