"""Assistant runtime task scaffolding for tier-routed execution."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.celery_app import app
from src.assistant.reliability import (
    classify_retry_class,
    evaluate_breaker_gate,
    evaluate_failure_transition,
    evaluate_retry_decision,
    get_runtime_policy_snapshot,
)
from src.assistant.reliability.policy_store import persist_breaker_state
from src.jobs.queueing import (
    dead_letter_payload_for_expiry,
    is_tier3_payload_expired,
    queue_for_tier_runtime,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


@app.task(name="src.tasks.assistant_runtime.run_tier_runtime", bind=True)
def run_tier_runtime(self, *, route_decision: str, payload: dict[str, Any] | None = None):
    """Execute tier-routed runtime payload with reliability guardrails."""
    payload = payload if isinstance(payload, dict) else {}
    queue_name = queue_for_tier_runtime(route_decision)
    snapshot = get_runtime_policy_snapshot(
        provider_name=payload.get("provider_name"),
        skill_name=payload.get("skill_name"),
    )
    breaker_gate = evaluate_breaker_gate(snapshot=snapshot, now_utc=_now())

    if not breaker_gate.allow_request:
        return {
            "task_id": self.request.id,
            "route_decision": route_decision,
            "queue": queue_name,
            "status": "blocked_by_breaker",
            "breaker": {
                "current_state": breaker_gate.current_state,
                "next_state": breaker_gate.next_state,
                "reason": breaker_gate.reason,
                "cooldown_remaining_seconds": breaker_gate.cooldown_remaining_seconds,
                "policy_version": snapshot.policy_version,
            },
            "payload": payload,
        }

    if queue_name == "assistant.t3":
        expired, age_seconds, ttl_seconds = is_tier3_payload_expired(payload, now_utc=_now())
        if expired:
            dead_letter = dead_letter_payload_for_expiry(
                payload,
                age_seconds=age_seconds,
                ttl_seconds=ttl_seconds,
            )
            return {
                "task_id": self.request.id,
                "route_decision": route_decision,
                "queue": queue_name,
                "status": "expired_not_run",
                "dead_letter": dead_letter,
                "payload": payload,
            }

    simulated_failure = payload.get("simulated_failure")
    if isinstance(simulated_failure, dict):
        retry_class = classify_retry_class(
            status_code=simulated_failure.get("status_code"),
            error_class=simulated_failure.get("error_class"),
        )
        attempt_number = int(simulated_failure.get("attempt_number") or 1)
        retry_after_seconds = simulated_failure.get("retry_after_seconds")
        retry_decision = evaluate_retry_decision(
            retry_class=retry_class,
            attempt_number=attempt_number,
            retry_after_seconds=retry_after_seconds,
            retry_policy=snapshot.retry_policy,
        )
        breaker_failure = evaluate_failure_transition(
            snapshot=snapshot,
            observed_latency_p95_seconds=simulated_failure.get("latency_p95_seconds"),
            now_utc=_now(),
            tier=route_decision,
        )
        persist_breaker_state(
            policy_id=snapshot.policy_id,
            breaker_state=breaker_failure.next_state,
            error_count=snapshot.breaker_error_count + 1,
            request_count=snapshot.breaker_request_count + 1,
            consecutive_successes=0,
            opened_at=_now() if breaker_failure.next_state == "open" else snapshot.breaker_opened_at,
            last_failure_at=_now(),
            last_success_at=snapshot.breaker_last_success_at,
        )
        status = "retry_scheduled" if retry_decision.should_retry else "failed_terminal"
        return {
            "task_id": self.request.id,
            "route_decision": route_decision,
            "queue": queue_name,
            "status": status,
            "retry": {
                "retry_class": retry_decision.retry_class,
                "should_retry": retry_decision.should_retry,
                "delay_seconds": retry_decision.delay_seconds,
                "max_retries": retry_decision.max_retries,
                "strategy": retry_decision.strategy,
                "invoke_reflexive_fixer": retry_decision.invoke_reflexive_fixer,
            },
            "breaker": {
                "current_state": breaker_failure.current_state,
                "next_state": breaker_failure.next_state,
                "reason": breaker_failure.reason,
            },
            "payload": payload,
        }

    qos = {"task_acks_late": True, "worker_prefetch_multiplier": 1}
    fallback_stage = payload.get("fallback_stage")
    next_state = snapshot.breaker_state
    next_successes = snapshot.breaker_consecutive_successes
    if snapshot.breaker_state == "half_open":
        next_successes = snapshot.breaker_consecutive_successes + 1
        if next_successes >= snapshot.breaker_half_open_successes:
            next_state = "closed"
            next_successes = 0
    persist_breaker_state(
        policy_id=snapshot.policy_id,
        breaker_state=next_state,
        error_count=snapshot.breaker_error_count,
        request_count=snapshot.breaker_request_count + 1,
        consecutive_successes=next_successes,
        opened_at=snapshot.breaker_opened_at if next_state != "closed" else None,
        last_failure_at=snapshot.breaker_last_failure_at,
        last_success_at=_now(),
    )
    return {
        "task_id": self.request.id,
        "route_decision": route_decision,
        "queue": queue_name,
        "qos": qos,
        "status": "accepted",
        "fallback_stage": fallback_stage,
        "reliability": {
            "policy_version": snapshot.policy_version,
            "policy_scope": snapshot.scope_kind,
            "breaker_state": next_state,
        },
        "payload": payload,
    }
