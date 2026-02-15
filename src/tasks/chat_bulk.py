"""Queue-backed bulk chat execution task."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.api.v1.chat.bulk import (
    AdaptiveBulkConcurrency,
    create_or_get_bulk_job,
    emit_bulk_job_progress,
    fair_chunk_order,
    summarize_chunk_results,
)
from src.api.v1.resolution.routes import create_dry_run_batch_for_user
from src.celery_app import app
from src.models import Job, JobStatus, db
from src.models.chat_action import ChatAction
from src.models.recovery_log import RecoveryLog
from src.resolution.apply_engine import apply_batch
from src.resolution.preflight import run_preflight


TERMINAL_CHUNK_STATUSES = {"completed", "applied", "partial", "conflicted", "failed", "skipped"}
CHAT_BULK_FAIRNESS_PROFILE = {
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "recommended_worker_mode": "-Ofair",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def _build_rows(*, skus: list[str], operation: str, hints: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sku in skus:
        row: dict[str, Any] = {
            "sku": sku,
            "title": hints.get("title") or f"Chat {sku}",
            "description": hints.get("description") or f"Bulk chat proposal for {sku}.",
            "variant_options": _coerce_list(hints.get("variant_options")),
        }
        if "price" in hints:
            row["price"] = hints.get("price")
        if operation in {"add_product", "create"}:
            row["product_type"] = hints.get("product_type") or "Draft"
        rows.append(row)
    return rows


def _job_status_for_action_status(action_status: str) -> JobStatus:
    if action_status == "failed":
        return JobStatus.FAILED
    return JobStatus.COMPLETED


def _load_or_create_job(action: ChatAction, payload: dict[str, Any], chunk_count: int, total_items: int) -> Job:
    job_id = payload.get("job_id")
    if isinstance(job_id, int):
        existing = Job.query.get(job_id)
        if existing is not None:
            return existing
    return create_or_get_bulk_job(action=action, total_items=total_items, chunk_count=chunk_count)


@app.task(
    name="src.tasks.chat_bulk.run_chat_bulk_action",
    bind=True,
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def run_chat_bulk_action(
    self,
    *,
    action_id: int,
    actor_user_id: int,
    mode: str | None = None,
    job_id: int | None = None,
) -> dict[str, Any]:
    """Execute bulk chat action chunks with replay-safe chunk lineage."""
    action = ChatAction.query.get(action_id)
    if action is None:
        return {"status": "failed", "error": "chat-action-not-found"}

    payload = dict(action.payload_json or {})
    if not bool(payload.get("bulk")):
        return {"status": "failed", "error": "not-a-bulk-action"}

    chunk_plan = dict(payload.get("chunk_plan") or {})
    chunks = list(chunk_plan.get("chunks") or [])
    if not chunks:
        action.status = "failed"
        action.error_message = "Bulk action has no chunk plan."
        action.completed_at = _now()
        db.session.commit()
        return {"status": "failed", "error": "empty-chunk-plan"}

    total_items = int(chunk_plan.get("total_skus") or sum(int(len(chunk.get("skus") or [])) for chunk in chunks))
    job = _load_or_create_job(action, payload, chunk_count=len(chunks), total_items=total_items)
    if isinstance(job_id, int) and job.id != job_id:
        payload["job_id"] = job.id

    action.status = "applying"
    action.applied_at = action.applied_at or _now()
    action.error_message = None
    db.session.flush()

    emit_bulk_job_progress(
        job=job,
        current_step="queued",
        processed_items=0,
        total_items=total_items,
        successful_items=0,
        failed_items=0,
        status=JobStatus.QUEUED,
    )

    chunk_results: dict[str, dict[str, Any]] = dict(payload.get("chunk_results") or {})
    progress_processed = 0
    progress_applied = 0
    progress_failed = 0

    ordered_chunks = fair_chunk_order(chunks)

    for chunk in ordered_chunks:
        chunk_id = str(chunk.get("chunk_id"))
        skus = [str(s).upper() for s in chunk.get("skus") or [] if str(s).strip()]
        existing = chunk_results.get(chunk_id)
        if existing and str(existing.get("status")) in TERMINAL_CHUNK_STATUSES:
            progress_processed += len(skus)
            progress_applied += int(existing.get("applied_count", 0))
            progress_failed += int(existing.get("failed_count", 0))
            continue

        try:
            dry_run_id = chunk.get("dry_run_id")
            if not isinstance(dry_run_id, int):
                rows = _build_rows(
                    skus=skus,
                    operation=str(payload.get("operation") or "update_product"),
                    hints=dict(payload.get("action_hints") or {}),
                )
                batch = create_dry_run_batch_for_user(
                    user_id=actor_user_id,
                    supplier_code=str((payload.get("action_hints") or {}).get("supplier_code") or "CHAT"),
                    supplier_verified=bool((payload.get("action_hints") or {}).get("supplier_verified", False)),
                    rows=rows,
                    apply_mode=mode or str(payload.get("mode") or "immediate"),
                )
                dry_run_id = batch.id
                chunk["dry_run_id"] = dry_run_id

            preflight = run_preflight(batch_id=dry_run_id, actor_user_id=actor_user_id)
            if preflight.conflicted_item_ids:
                logs = (
                    RecoveryLog.query.filter(
                        RecoveryLog.batch_id == dry_run_id,
                        RecoveryLog.item_id.in_(preflight.conflicted_item_ids),
                    )
                    .order_by(RecoveryLog.created_at.desc())
                    .all()
                )
                chunk_results[chunk_id] = {
                    "status": "conflicted",
                    "dry_run_id": dry_run_id,
                    "sku_count": len(skus),
                    "applied_count": 0,
                    "conflicted_count": len(preflight.conflicted_item_ids),
                    "failed_count": 0,
                    "recovery_log_ids": [log.id for log in logs],
                    "reason": "preflight-conflict",
                }
            else:
                apply_result = apply_batch(
                    batch_id=dry_run_id,
                    actor_user_id=actor_user_id,
                    mode=mode or payload.get("mode"),
                    preflight_report=preflight,
                )
                logs = (
                    RecoveryLog.query.filter_by(batch_id=dry_run_id)
                    .order_by(RecoveryLog.created_at.desc())
                    .limit(100)
                    .all()
                )
                chunk_status = "completed"
                if apply_result.status in {"failed", "cancelled"}:
                    chunk_status = "failed"
                elif apply_result.status == "applied_with_conflicts":
                    chunk_status = "partial"

                chunk_results[chunk_id] = {
                    "status": chunk_status,
                    "dry_run_id": dry_run_id,
                    "sku_count": len(skus),
                    "applied_count": len(apply_result.applied_item_ids),
                    "conflicted_count": len(apply_result.conflicted_item_ids),
                    "failed_count": len(apply_result.failed_item_ids),
                    "recovery_log_ids": [log.id for log in logs],
                    "paused": apply_result.paused,
                    "critical_errors": apply_result.critical_errors,
                    "backoff_events": apply_result.backoff_events,
                }
        except Exception as exc:  # pragma: no cover - defensive safety path
            chunk_results[chunk_id] = {
                "status": "failed",
                "sku_count": len(skus),
                "applied_count": 0,
                "conflicted_count": 0,
                "failed_count": len(skus),
                "error": str(exc),
            }

        current = chunk_results.get(chunk_id, {})
        progress_processed += len(skus)
        progress_applied += int(current.get("applied_count", 0))
        progress_failed += int(current.get("failed_count", 0))

        payload["chunk_results"] = chunk_results
        payload["chunk_plan"] = chunk_plan
        action.payload_json = payload
        db.session.flush()

        emit_bulk_job_progress(
            job=job,
            current_step="applying_updates",
            processed_items=min(progress_processed, total_items),
            total_items=total_items,
            successful_items=progress_applied,
            failed_items=progress_failed,
            status=JobStatus.RUNNING,
        )

    summary = summarize_chunk_results(chunk_results)
    if summary["failed"] > 0 and summary["applied"] == 0 and summary["conflicted"] == 0:
        final_action_status = "failed"
    elif summary["failed"] > 0 or summary["conflicted"] > 0:
        final_action_status = "partial"
    else:
        final_action_status = "completed"

    payload["chunk_results"] = chunk_results
    payload["chunk_plan"] = chunk_plan
    payload["bulk_summary"] = summary

    action.payload_json = payload
    action.result_json = {
        "status": final_action_status,
        "summary": summary,
        "chunk_count": len(chunks),
        "total_skus": total_items,
        "job_id": job.id,
    }
    action.status = final_action_status
    action.error_message = None if final_action_status != "failed" else "One or more chunks failed."
    action.completed_at = _now()

    emit_bulk_job_progress(
        job=job,
        current_step="completed" if final_action_status != "failed" else "failed",
        processed_items=total_items,
        total_items=total_items,
        successful_items=summary["applied"],
        failed_items=summary["failed"],
        status=_job_status_for_action_status(final_action_status),
        error_message=action.error_message,
    )

    db.session.commit()
    return action.result_json or {"status": final_action_status}
