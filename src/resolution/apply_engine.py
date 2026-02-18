"""Guarded apply execution for approved resolution batches."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import sleep
from typing import Any, Callable

from src.models import db
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.resolution_snapshot import ResolutionSnapshot
from src.resolution.preflight import PreflightReport, run_preflight
from src.resolution.throttle import AdaptiveThrottleController, ThrottleSignal, parse_throttle_signal


MutationHandler = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class ApplyBatchResult:
    batch_id: int
    status: str
    applied_item_ids: list[int]
    conflicted_item_ids: list[int]
    failed_item_ids: list[int]
    deferred_item_ids: list[int]
    retryable_item_ids: list[int]
    paused: bool
    critical_errors: int
    backoff_events: int
    rerun_conflicted_item_ids: list[int]
    terminal_summary: dict[str, int]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _default_mutation_handler(*, item: ResolutionItem, idempotency_key: str, mode: str) -> dict[str, Any]:
    """
    Default no-op mutation handler.

    Phase 8 wiring can inject real Shopify mutation adapters through this hook.
    """
    return {"success": True, "critical": False, "throttle": None}


def _apply_item_decisions(item: ResolutionItem) -> None:
    item.status = "applied"
    for change in item.changes.order_by("id").all():
        if change.status in {"rejected", "blocked_exclusion", "structural_conflict"}:
            continue
        change.status = "applied"


def _to_signal(raw: Any) -> ThrottleSignal | None:
    if raw is None:
        return None
    if isinstance(raw, ThrottleSignal):
        return raw
    if isinstance(raw, dict):
        if {"currently_available", "maximum_available", "restore_rate"} <= raw.keys():
            return ThrottleSignal(
                currently_available=float(raw["currently_available"]),
                maximum_available=float(raw["maximum_available"]),
                restore_rate=float(raw["restore_rate"]),
            )
        return parse_throttle_signal(graphql_payload=raw)
    return None


def _is_transient_failure(result: dict[str, Any]) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("transient") is True:
        return True
    status_code = result.get("status_code")
    if isinstance(status_code, int) and (status_code == 429 or status_code >= 500):
        return True
    error_class = str(result.get("error_class") or "").lower()
    if error_class in {"timeout", "connection_error", "temporary_unavailable"}:
        return True
    return False


def _latest_prechange_snapshot_id(batch_id: int, item_id: int) -> int | None:
    row = (
        ResolutionSnapshot.query.filter_by(
            batch_id=batch_id,
            item_id=item_id,
            snapshot_type="product_pre_change",
        )
        .order_by(ResolutionSnapshot.created_at.desc())
        .first()
    )
    return row.id if row else None


def _record_deferred_recovery(
    *,
    batch: ResolutionBatch,
    item: ResolutionItem,
    actor_user_id: int | None,
    idempotency_key: str,
    attempts: int,
    result: dict[str, Any],
) -> None:
    existing = RecoveryLog.query.filter_by(
        batch_id=batch.id,
        item_id=item.id,
        reason_code="critical_apply_failure",
    ).first()
    if existing is not None:
        return

    log = RecoveryLog(
        batch_id=batch.id,
        item_id=item.id,
        store_id=batch.store_id,
        reason_code="critical_apply_failure",
        reason_detail="Transient apply retries exhausted; item deferred for deterministic replay.",
        payload={
            "item_status": item.status,
            "product_label": item.product_label,
            "shopify_product_id": item.shopify_product_id,
            "shopify_variant_id": item.shopify_variant_id,
        },
        replay_metadata={
            "batch_id": batch.id,
            "item_id": item.id,
            "attempts": attempts,
            "idempotency_key": idempotency_key,
            "last_result": result,
            "replay_action": "retry_apply_item",
        },
        snapshot_id=_latest_prechange_snapshot_id(batch.id, item.id),
        created_by_user_id=actor_user_id,
    )
    db.session.add(log)


def apply_batch(
    *,
    batch_id: int,
    actor_user_id: int | None = None,
    mode: str | None = None,
    critical_threshold: int | None = None,
    mutation_handler: MutationHandler | None = None,
    preflight_report: PreflightReport | None = None,
    sleep_fn: Callable[[float], None] = sleep,
) -> ApplyBatchResult:
    """Apply eligible changes with pre-flight checks and adaptive throttling."""
    batch = ResolutionBatch.query.filter_by(id=batch_id).first()
    if batch is None:
        raise ValueError(f"Resolution batch {batch_id} not found.")

    effective_mode = mode or batch.apply_mode
    threshold = critical_threshold if critical_threshold is not None else batch.critical_error_threshold
    handler = mutation_handler or _default_mutation_handler

    report = preflight_report or run_preflight(
        batch_id=batch_id,
        actor_user_id=actor_user_id,
        mutation_started_at=_now(),
    )

    metadata = dict(batch.metadata_json or {})
    if not report.within_window:
        metadata["preflight_window_violation"] = True
        batch.metadata_json = metadata
        batch.status = "failed"
        batch.applied_at = _now()
        db.session.commit()
        return ApplyBatchResult(
            batch_id=batch.id,
            status=batch.status,
            applied_item_ids=[],
            conflicted_item_ids=report.conflicted_item_ids,
            failed_item_ids=[],
            deferred_item_ids=[],
            retryable_item_ids=[],
            paused=False,
            critical_errors=0,
            backoff_events=0,
            rerun_conflicted_item_ids=report.conflicted_item_ids if effective_mode == "scheduled" else [],
            terminal_summary={"success": 0, "failed": 0, "deferred": 0, "retryable": 0},
        )

    batch.status = "applying"
    db.session.flush()

    controller = AdaptiveThrottleController(
        initial_concurrency=max(1, min(10, metadata.get("initial_concurrency", 5))),
    )
    transient_retry_max_attempts = int(max(1, metadata.get("transient_retry_max_attempts", 3)))
    transient_retry_base_seconds = float(max(0.1, metadata.get("transient_retry_base_seconds", 1.0)))

    applied: list[int] = []
    failed: list[int] = []
    deferred: list[int] = []
    retryable: list[int] = []
    critical_errors = 0
    backoff_events = 0
    paused = False

    for item_id in report.eligible_item_ids:
        item = ResolutionItem.query.filter_by(id=item_id, batch_id=batch.id).first()
        if item is None:
            continue

        idempotency_key = f"resolution-{batch.id}-{item.id}"
        attempt = 0
        last_result: dict[str, Any] = {"success": False, "critical": True}
        succeeded = False

        while attempt < transient_retry_max_attempts:
            attempt += 1
            result = handler(
                item=item,
                idempotency_key=idempotency_key,
                mode=effective_mode,
            )
            last_result = result

            signal = _to_signal(result.get("throttle"))
            controller.observe(signal)
            backoff_seconds = controller.recommended_backoff_seconds(signal)
            if backoff_seconds > 0:
                backoff_events += 1
                sleep_fn(backoff_seconds)

            if result.get("success", False):
                _apply_item_decisions(item)
                applied.append(item.id)
                succeeded = True
                break

            if _is_transient_failure(result) and attempt < transient_retry_max_attempts:
                retry_backoff = transient_retry_base_seconds * (2 ** (attempt - 1))
                backoff_events += 1
                sleep_fn(retry_backoff)
                continue
            break

        if succeeded:
            continue

        item.status = "failed"
        failed.append(item.id)

        if _is_transient_failure(last_result):
            deferred.append(item.id)
            retryable.append(item.id)
            _record_deferred_recovery(
                batch=batch,
                item=item,
                actor_user_id=actor_user_id,
                idempotency_key=idempotency_key,
                attempts=attempt,
                result=last_result,
            )
            continue

        if last_result.get("critical", True):
            critical_errors += 1
            if critical_errors > threshold:
                paused = True
                break

    rerun_conflicted_item_ids: list[int] = []
    if effective_mode == "scheduled" and report.conflicted_item_ids:
        rerun_conflicted_item_ids = list(report.conflicted_item_ids)
        metadata["rerun_conflicted_only"] = rerun_conflicted_item_ids

    if paused:
        batch.status = "failed"
        metadata["paused_due_to_critical_errors"] = True
    elif failed or report.conflicted_item_ids or deferred:
        batch.status = "applied_with_conflicts"
    else:
        batch.status = "applied"

    terminal_summary = {
        "success": len(applied),
        "failed": len([item_id for item_id in failed if item_id not in deferred]),
        "deferred": len(deferred),
        "retryable": len(retryable),
    }
    metadata["last_concurrency"] = controller.current_concurrency
    metadata["backoff_events"] = backoff_events
    metadata["terminal_summary"] = terminal_summary
    batch.metadata_json = metadata
    batch.applied_at = _now()
    db.session.commit()

    return ApplyBatchResult(
        batch_id=batch.id,
        status=batch.status,
        applied_item_ids=applied,
        conflicted_item_ids=report.conflicted_item_ids,
        failed_item_ids=failed,
        deferred_item_ids=deferred,
        retryable_item_ids=retryable,
        paused=paused,
        critical_errors=critical_errors,
        backoff_events=backoff_events,
        rerun_conflicted_item_ids=rerun_conflicted_item_ids,
        terminal_summary=terminal_summary,
    )
