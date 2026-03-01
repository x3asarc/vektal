"""Post-execution verification oracle and deferred-verification workflows."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from src.models import AssistantVerificationEvent, db


DEFAULT_POLL_SCHEDULE_SECONDS = [5, 10, 15]
DEFAULT_DEFERRED_RECHECK_SECONDS = 300

VerificationProbe = Callable[[int, int], Any]
DeferredVerificationProbe = Callable[[AssistantVerificationEvent], Any]


@dataclass(frozen=True)
class VerificationOutcome:
    event_id: int | None
    status: str
    attempt_count: int
    waited_seconds: int
    poll_schedule_seconds: list[int]
    message: str
    oracle_result: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "waited_seconds": self.waited_seconds,
            "poll_schedule_seconds": self.poll_schedule_seconds,
            "message": self.message,
            "oracle_result": self.oracle_result,
        }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_probe_result(result: Any) -> tuple[str, dict[str, Any], str]:
    if isinstance(result, bool):
        status = "verified" if result else "deferred"
        message = "Verification confirmed." if result else "Verification pending."
        return status, {"verified": result}, message
    if isinstance(result, dict):
        if result.get("status") in {"verified", "deferred", "failed"}:
            status = str(result["status"])
        else:
            status = "verified" if bool(result.get("verified")) else "deferred"
        message = str(result.get("message") or "").strip()
        if not message:
            if status == "verified":
                message = "Verification confirmed."
            elif status == "failed":
                message = "Verification failed."
            else:
                message = "Verification pending."
        return status, result, message
    return "deferred", {"verified": False, "raw_result": result}, "Verification pending."


def verify_execution_finality(
    *,
    action_id: int | None,
    batch_id: int | None,
    store_id: int | None,
    user_id: int | None,
    correlation_id: str | None = None,
    oracle_name: str = "post_apply_finality",
    poll_schedule_seconds: list[int] | None = None,
    verification_probe: VerificationProbe | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> VerificationOutcome:
    """Run verification polling and persist verified/deferred/failed event lineage."""
    schedule = [int(max(0, value)) for value in (poll_schedule_seconds or DEFAULT_POLL_SCHEDULE_SECONDS)]
    if not schedule:
        schedule = list(DEFAULT_POLL_SCHEDULE_SECONDS)

    attempt_count = 0
    waited_seconds = 0
    status = "deferred"
    message = "Verification pending."
    oracle_result: dict[str, Any] = {"verified": False}

    for attempt_index, delay_seconds in enumerate(schedule, start=1):
        attempt_count = attempt_index
        probe_result = (
            verification_probe(attempt_index, waited_seconds)
            if verification_probe is not None
            else {"verified": True, "message": "Verification confirmed from apply result."}
        )
        status, oracle_result, message = _normalize_probe_result(probe_result)
        if status in {"verified", "failed"}:
            break
        waited_seconds += delay_seconds
        if sleep_fn is not None and attempt_index < len(schedule):
            sleep_fn(delay_seconds)

    if status == "deferred":
        message = (
            "Update sent to Shopify, but confirmation is delayed. "
            "I will verify in the background."
        )

    event = AssistantVerificationEvent(
        action_id=action_id,
        batch_id=batch_id,
        store_id=store_id,
        user_id=user_id,
        correlation_id=correlation_id,
        oracle_name=oracle_name,
        status=status,
        attempt_count=max(1, attempt_count),
        poll_schedule_json=schedule,
        waited_seconds=max(0, waited_seconds),
        status_message=message,
        oracle_result_json=oracle_result,
        metadata_json=metadata_json or {},
        deferred_until=(
            _now() + timedelta(seconds=DEFAULT_DEFERRED_RECHECK_SECONDS)
            if status == "deferred"
            else None
        ),
        verified_at=_now() if status == "verified" else None,
        failed_at=_now() if status == "failed" else None,
    )
    db.session.add(event)
    db.session.commit()

    return VerificationOutcome(
        event_id=event.id,
        status=status,
        attempt_count=max(1, attempt_count),
        waited_seconds=max(0, waited_seconds),
        poll_schedule_seconds=schedule,
        message=message,
        oracle_result=oracle_result,
    )


def process_deferred_verifications(
    *,
    limit: int = 50,
    verification_probe: DeferredVerificationProbe | None = None,
) -> dict[str, int]:
    """Retry deferred verification records, for background verifier worker loops."""
    now_utc = _now()
    rows = (
        AssistantVerificationEvent.query.filter(
            AssistantVerificationEvent.status == "deferred",
            (AssistantVerificationEvent.deferred_until.is_(None))
            | (AssistantVerificationEvent.deferred_until <= now_utc),
        )
        .order_by(AssistantVerificationEvent.created_at.asc())
        .limit(max(1, int(limit)))
        .all()
    )

    checked = 0
    verified = 0
    failed = 0
    still_deferred = 0
    for row in rows:
        checked += 1
        probe_result = (
            verification_probe(row) if verification_probe is not None else {"verified": False}
        )
        status, oracle_result, message = _normalize_probe_result(probe_result)
        row.attempt_count = max(1, int(row.attempt_count or 1) + 1)
        row.oracle_result_json = oracle_result
        row.status_message = message
        if status == "verified":
            row.status = "verified"
            row.verified_at = now_utc
            row.deferred_until = None
            verified += 1
        elif status == "failed":
            row.status = "failed"
            row.failed_at = now_utc
            row.deferred_until = None
            failed += 1
        else:
            row.status = "deferred"
            row.deferred_until = now_utc + timedelta(seconds=DEFAULT_DEFERRED_RECHECK_SECONDS)
            still_deferred += 1

    if checked:
        db.session.commit()

    # Emit oracle decision episodes for verified/failed events (Phase 13.2)
    try:
        from src.tasks.graphiti_sync import emit_episode, emit_episodes_batch
        from src.core.synthex_entities import EpisodeType

        episodes_to_emit = []
        for row in rows:
            if row.status in {"verified", "failed"}:
                try:
                    payload = {
                        "decision": row.status,
                        "confidence": 0.95 if row.status == "verified" else 0.8,
                        "reason_codes": [],
                        "evidence_refs": [],
                        "requires_user_action": row.status == "failed",
                        "source_adapter": row.oracle_name or "verification_oracle",
                    }
                    episodes_to_emit.append(
                        {
                            "episode_type": EpisodeType.ORACLE_DECISION.value,
                            "store_id": str(row.store_id),
                            "payload": payload,
                            "correlation_id": row.correlation_id,
                        }
                    )
                except Exception as inner_e:
                    import logging

                    logging.getLogger(__name__).warning(f"Failed to prepare oracle episode: {inner_e}")

        if len(episodes_to_emit) > 5:
            emit_episodes_batch.delay(episodes_to_emit)
        else:
            for ep in episodes_to_emit:
                emit_episode.delay(**ep)

    except Exception:
        pass  # Fail-open: do not break verification flow if graph emission fails

    return {
        "checked": checked,
        "verified": verified,
        "failed": failed,
        "still_deferred": still_deferred,
    }


def build_oracle_signal_payload(
    *,
    decision: str,
    confidence: float,
    reason_codes: list[str] | tuple[str, ...],
    evidence_refs: list[str] | tuple[str, ...] | None = None,
    requires_user_action: bool,
) -> dict[str, Any]:
    """
    Normalize Oracle adapter output into one shared verification signal payload.
    """
    return {
        "decision": str(decision),
        "confidence": float(confidence),
        "reason_codes": list(reason_codes),
        "evidence_refs": list(evidence_refs or ()),
        "requires_user_action": bool(requires_user_action),
    }
