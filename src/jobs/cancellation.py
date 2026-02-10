"""Cooperative cancellation flow for Phase 6 jobs."""
from __future__ import annotations

from datetime import datetime, timezone

from src.models import IngestChunk, IngestChunkStatus, Job, JobStatus, db


def _now() -> datetime:
    return datetime.now(timezone.utc)


def request_cancellation(job_id: int, terminate: bool = False) -> dict:
    """
    Request cooperative cancellation and revoke queued-not-started tasks.

    `terminate=True` is reserved for emergency fallback use only.
    """
    query = Job.query.filter_by(id=job_id)
    if hasattr(query, "with_for_update"):
        query = query.with_for_update()
    job = query.first()
    if not job:
        return {"status": "missing-job"}

    if job.status in {JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.FAILED_TERMINAL}:
        return {"status": "already-terminal", "job_status": job.status.value}

    if job.status == JobStatus.CANCEL_REQUESTED:
        return {"status": "already-requested", "job_status": job.status.value}

    job.status = JobStatus.CANCEL_REQUESTED
    job.cancellation_requested_at = _now()

    revoke_count = 0
    from src.celery_app import app as celery_app

    pending_chunks = IngestChunk.query.filter_by(
        job_id=job.id,
        status=IngestChunkStatus.PENDING,
    ).all()
    for chunk in pending_chunks:
        if not chunk.task_id:
            continue
        celery_app.control.revoke(chunk.task_id, terminate=terminate)
        revoke_count += 1

    # Kick finalizer asynchronously so the state converges quickly.
    celery_app.send_task("src.tasks.control.finalize_job", kwargs={"job_id": job.id})
    db.session.commit()
    return {
        "status": "cancel_requested",
        "job_status": job.status.value,
        "revoked_tasks": revoke_count,
        "terminate_used": bool(terminate),
    }
