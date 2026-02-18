"""Checkpoint outbox dispatcher with SKIP LOCKED claim semantics."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_, select

from src.models import AuditCheckpoint, AuditDispatchStatus, db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _backoff_seconds(attempts: int, base: int = 15, cap: int = 300) -> int:
    value = base * (2 ** max(attempts - 1, 0))
    return min(value, cap)


def _publish_audit(job_id: int, checkpoint: int) -> str:
    """Default publisher that enqueues audit_run task and returns task id."""
    from src.celery_app import app as celery_app

    result = celery_app.send_task(
        "src.tasks.audits.audit_run",
        kwargs={"job_id": job_id, "checkpoint": checkpoint},
    )
    return result.id


def dispatch_pending_audits(
    batch_size: int = 50,
    publisher: Callable[[int, int], str] | None = None,
) -> dict:
    """
    Claim due checkpoint rows and publish audit tasks.

    Rows are claimed with FOR UPDATE SKIP LOCKED to avoid cross-worker collisions.
    """
    publish = publisher or _publish_audit
    now = _now()

    stmt = (
        select(AuditCheckpoint)
        .where(AuditCheckpoint.dispatch_status == AuditDispatchStatus.PENDING_DISPATCH)
        .where(
            or_(
                AuditCheckpoint.next_dispatch_at.is_(None),
                AuditCheckpoint.next_dispatch_at <= now,
            )
        )
        .order_by(AuditCheckpoint.id.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    rows = db.session.execute(stmt).scalars().all()

    dispatched = 0
    retried = 0
    for row in rows:
        row.dispatch_attempts += 1
        try:
            task_id = publish(row.job_id, row.checkpoint)
            row.dispatch_status = AuditDispatchStatus.DISPATCHED
            row.dispatched_at = now
            row.last_error = None
            row.next_dispatch_at = None
            row.task_id = task_id
            dispatched += 1
        except Exception as exc:  # pragma: no cover - exercised in tests via custom publisher
            row.last_error = str(exc)
            delay = _backoff_seconds(row.dispatch_attempts)
            row.next_dispatch_at = now + timedelta(seconds=delay)
            retried += 1

    db.session.commit()
    return {"claimed": len(rows), "dispatched": dispatched, "scheduled_retry": retried}

