"""Celery task wrappers for Phase 8 resolution apply lifecycle."""
from __future__ import annotations

from src.celery_app import app
from src.resolution.apply_engine import apply_batch


@app.task(name="src.tasks.resolution_apply.apply_resolution_batch", bind=True, max_retries=3, retry_backoff=True)
def apply_resolution_batch_task(
    self,
    *,
    batch_id: int,
    actor_user_id: int | None = None,
    mode: str | None = None,
) -> dict:
    result = apply_batch(
        batch_id=batch_id,
        actor_user_id=actor_user_id,
        mode=mode,
    )
    return {
        "batch_id": result.batch_id,
        "status": result.status,
        "applied_item_ids": result.applied_item_ids,
        "conflicted_item_ids": result.conflicted_item_ids,
        "failed_item_ids": result.failed_item_ids,
        "paused": result.paused,
        "critical_errors": result.critical_errors,
        "backoff_events": result.backoff_events,
        "rerun_conflicted_item_ids": result.rerun_conflicted_item_ids,
    }
