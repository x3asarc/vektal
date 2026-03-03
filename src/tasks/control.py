"""Control-plane Celery tasks (cancel, finalize, retention cleanup)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.celery_app import app
from src.core.sentry_metrics import count as sentry_count
from src.core.sentry_metrics import distribution as sentry_distribution
from src.core.sentry_metrics import gauge as sentry_gauge
from src.jobs.cancellation import request_cancellation
from src.jobs.finalizer import finalize_job as run_finalizer
from src.models import Job, JobStatus, db


def _now() -> datetime:
    return datetime.now(timezone.utc)


@app.task(name="src.tasks.control.cancel_job")
def cancel_job(job_id: int, terminate: bool = False) -> dict:
    """Cooperative cancellation endpoint for asynchronous callers."""
    return request_cancellation(job_id=job_id, terminate=terminate)


@app.task(name="src.tasks.control.finalize_job")
def finalize_job(job_id: int, mode: str | None = None) -> dict:
    """Run finalizer convergence for a single job."""
    return run_finalizer(job_id=job_id, mode=mode)


@app.task(name="src.tasks.control.cleanup_old_jobs")
def cleanup_old_jobs(retention_days: int = 30, dry_run: bool = True) -> dict:
    """
    Cleanup old terminal jobs.

    Dry-run mode is default for safety.
    """
    cutoff = _now() - timedelta(days=max(retention_days, 1))
    terminal_statuses = [
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.FAILED_TERMINAL,
        JobStatus.CANCELLED,
    ]
    query = Job.query.filter(
        Job.status.in_(terminal_statuses),
        Job.completed_at.isnot(None),
        Job.completed_at <= cutoff,
    )
    jobs = query.all()

    if dry_run:
        return {
            "dry_run": True,
            "retention_days": retention_days,
            "candidate_count": len(jobs),
            "candidate_ids": [job.id for job in jobs],
        }

    deleted = 0
    for job in jobs:
        db.session.delete(job)
        deleted += 1
    db.session.commit()
    return {
        "dry_run": False,
        "retention_days": retention_days,
        "deleted_count": deleted,
    }


@app.task(name="src.tasks.control.sentry_metrics_smoke")
def sentry_metrics_smoke(source: str = "ops_api", correlation_id: str | None = None) -> dict:
    """Emit a deterministic set of worker-side Sentry metrics for smoke validation."""
    tags = {"source": source}
    sentry_count("workers.sentry.smoke.count", 1, tags=tags)
    sentry_gauge("workers.sentry.smoke.gauge", 42, tags=tags)
    sentry_distribution("workers.sentry.smoke.distribution", 187.5, tags=tags)
    return {
        "status": "ok",
        "source": source,
        "correlation_id": correlation_id,
        "metrics": [
            "workers.sentry.smoke.count",
            "workers.sentry.smoke.gauge",
            "workers.sentry.smoke.distribution",
        ],
    }
