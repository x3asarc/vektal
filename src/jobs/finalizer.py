"""Finalizer convergence for Phase 6 job state machine."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_

from src.models import (
    AuditCheckpoint,
    AuditDispatchStatus,
    IngestChunk,
    IngestChunkStatus,
    Job,
    JobStatus,
    db,
)
from src.jobs.progress import announce_job_progress


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _due_pending_checkpoints(job_id: int, now: datetime) -> int:
    return (
        db.session.query(func.count(AuditCheckpoint.id))
        .filter(
            AuditCheckpoint.job_id == job_id,
            AuditCheckpoint.dispatch_status == AuditDispatchStatus.PENDING_DISPATCH,
            or_(
                AuditCheckpoint.next_dispatch_at.is_(None),
                AuditCheckpoint.next_dispatch_at <= now,
            ),
        )
        .scalar()
        or 0
    )


def _chunk_counts(job_id: int) -> dict:
    rows = (
        db.session.query(IngestChunk.status, func.count(IngestChunk.id))
        .filter(IngestChunk.job_id == job_id)
        .group_by(IngestChunk.status)
        .all()
    )
    counts = {
        IngestChunkStatus.PENDING: 0,
        IngestChunkStatus.IN_PROGRESS: 0,
        IngestChunkStatus.COMPLETED: 0,
        IngestChunkStatus.FAILED_TERMINAL: 0,
    }
    for status, value in rows:
        counts[status] = value
    counts["total"] = sum(counts.values())
    return counts


def _resolve_mode(mode: str | None) -> str:
    explicit = (mode or "").strip().lower()
    if explicit in {"strict", "lenient"}:
        return explicit
    return os.getenv("PHASE6_FINALIZER_MODE", "strict").strip().lower() or "strict"


def finalize_job(job_id: int, mode: str | None = None) -> dict:
    """
    Converge job status to terminal state when DB conditions are satisfied.

    Strict mode is default: any failed_terminal chunk causes failed_terminal job.
    """
    now = _now()
    job = Job.query.filter_by(id=job_id).with_for_update().first()
    if not job:
        return {"status": "missing-job"}
    if job.is_terminal:
        return {"status": "already-terminal", "job_status": job.status.value}

    counts = _chunk_counts(job_id)
    due_checkpoints = _due_pending_checkpoints(job_id=job_id, now=now)
    finalizer_mode = _resolve_mode(mode)

    if job.status == JobStatus.CANCEL_REQUESTED:
        if counts[IngestChunkStatus.IN_PROGRESS] > 0:
            return {"status": "waiting-in-progress", "in_progress": counts[IngestChunkStatus.IN_PROGRESS]}

        updated = (
            IngestChunk.query.filter(
                and_(
                    IngestChunk.job_id == job_id,
                    IngestChunk.status == IngestChunkStatus.PENDING,
                )
            )
            .update(
                {
                    IngestChunk.status: IngestChunkStatus.FAILED_TERMINAL,
                    IngestChunk.last_error: "cancel_requested",
                    IngestChunk.cancellation_code: "cancel_requested",
                    IngestChunk.completed_at: now,
                },
                synchronize_session=False,
            )
        )
        if updated:
            counts = _chunk_counts(job_id)

        if counts[IngestChunkStatus.IN_PROGRESS] == 0 and counts[IngestChunkStatus.PENDING] == 0:
            job.status = JobStatus.CANCELLED
            job.completed_at = now
            job.terminal_reason = "cancel_requested"
            db.session.commit()
            announce_job_progress(job_id=job.id, job=job)
            return {"status": "cancelled", "job_status": job.status.value}
        return {"status": "waiting-cancel-convergence"}

    if job.status not in {JobStatus.RUNNING, JobStatus.QUEUED, JobStatus.PENDING}:
        return {"status": "no-op", "job_status": job.status.value}

    if counts["total"] == 0:
        job.status = JobStatus.COMPLETED
        job.completed_at = now
        db.session.commit()
        announce_job_progress(job_id=job.id, job=job)
        return {"status": "completed-empty", "job_status": job.status.value}

    terminal_chunks = counts[IngestChunkStatus.COMPLETED] + counts[IngestChunkStatus.FAILED_TERMINAL]
    if terminal_chunks < counts["total"]:
        return {"status": "waiting-chunks", "terminal_chunks": terminal_chunks, "total_chunks": counts["total"]}

    if due_checkpoints > 0:
        return {"status": "waiting-checkpoints", "due_checkpoints": due_checkpoints}

    if finalizer_mode == "strict" and counts[IngestChunkStatus.FAILED_TERMINAL] > 0:
        job.status = JobStatus.FAILED_TERMINAL
        job.terminal_reason = "strict_failed_chunk"
    else:
        job.status = JobStatus.COMPLETED
        if counts[IngestChunkStatus.FAILED_TERMINAL] > 0:
            job.terminal_reason = "lenient_partial_failure"
    job.completed_at = now
    db.session.commit()
    announce_job_progress(job_id=job.id, job=job)
    return {"status": "finalized", "job_status": job.status.value, "mode": finalizer_mode}
