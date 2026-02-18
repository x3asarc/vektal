"""Operational metrics emitters for Phase 6 runtime visibility."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, or_

from src.models import AuditCheckpoint, AuditDispatchStatus, IngestChunk, IngestChunkStatus, Job, JobStatus, db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def queue_depth_metrics(active_queues: dict | None = None) -> dict[str, int]:
    """
    Estimate queue depth from Celery inspect payload.

    This is intentionally lightweight and test-friendly.
    """
    if active_queues is None:
        from src.celery_app import app as celery_app

        inspector = celery_app.control.inspect()
        active_queues = inspector.active_queues() or {}

    depth: dict[str, int] = {}
    for _worker, queues in (active_queues or {}).items():
        for queue in queues:
            name = queue.get("name")
            if not name:
                continue
            depth[name] = depth.get(name, 0) + 1
    return depth


def chunk_staleness_metrics(stale_after_minutes: int = 10) -> dict[str, int]:
    """Emit count of stale in-progress chunks and oldest staleness age."""
    now = _now()
    cutoff = now - timedelta(minutes=stale_after_minutes)
    stale_rows = (
        db.session.query(IngestChunk.claimed_at)
        .filter(
            IngestChunk.status == IngestChunkStatus.IN_PROGRESS,
            IngestChunk.claimed_at.isnot(None),
            IngestChunk.claimed_at <= cutoff,
        )
        .all()
    )
    if not stale_rows:
        return {"stale_chunk_count": 0, "oldest_stale_minutes": 0}

    oldest = min(row[0] for row in stale_rows if row[0] is not None)
    oldest_minutes = int((now - oldest).total_seconds() // 60) if oldest else 0
    return {"stale_chunk_count": len(stale_rows), "oldest_stale_minutes": oldest_minutes}


def pending_dispatch_metrics() -> dict[str, int]:
    """Emit backlog metrics for checkpoint dispatch queue."""
    now = _now()
    pending = (
        db.session.query(func.count(AuditCheckpoint.id))
        .filter(AuditCheckpoint.dispatch_status == AuditDispatchStatus.PENDING_DISPATCH)
        .scalar()
        or 0
    )
    due = (
        db.session.query(func.count(AuditCheckpoint.id))
        .filter(
            AuditCheckpoint.dispatch_status == AuditDispatchStatus.PENDING_DISPATCH,
            or_(
                AuditCheckpoint.next_dispatch_at.is_(None),
                AuditCheckpoint.next_dispatch_at <= now,
            ),
        )
        .scalar()
        or 0
    )
    return {"pending_dispatch_total": pending, "pending_dispatch_due": due}


def job_staleness_indicator(stale_minutes: int = 30) -> dict[str, int]:
    """Emit count of jobs that appear stuck in active states."""
    cutoff = _now() - timedelta(minutes=stale_minutes)
    stale_jobs = (
        db.session.query(func.count(Job.id))
        .filter(
            Job.status.in_([JobStatus.RUNNING, JobStatus.CANCEL_REQUESTED]),
            Job.updated_at <= cutoff,
        )
        .scalar()
        or 0
    )
    return {"stale_job_count": stale_jobs}


def phase6_metrics_snapshot(active_queues: dict | None = None) -> dict:
    """Aggregate queue, chunk, outbox, and job staleness metrics."""
    return {
        "queue_depth": queue_depth_metrics(active_queues=active_queues),
        "chunks": chunk_staleness_metrics(),
        "outbox": pending_dispatch_metrics(),
        "jobs": job_staleness_indicator(),
    }

