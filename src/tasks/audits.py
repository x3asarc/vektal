"""Audit and dispatcher Celery tasks."""
from __future__ import annotations

from src.celery_app import app
from src.jobs.dispatcher import dispatch_pending_audits as run_dispatcher
from src.jobs.finalizer import finalize_job
from src.models import JobResult, db


@app.task(name="src.tasks.audits.dispatch_pending_audits")
def dispatch_pending_audits(batch_size: int = 50) -> dict:
    """Dispatch due audit checkpoints from DB outbox."""
    result = run_dispatcher(batch_size=batch_size)
    return result


@app.task(name="src.tasks.audits.audit_run", bind=True, max_retries=3, retry_backoff=True)
def audit_run(self, job_id: int, checkpoint: int) -> dict:
    """
    Idempotent checkpoint audit write keyed by (job_id, checkpoint).

    For Phase 6, this persists audit evidence in `job_results`.
    """
    identifier = f"audit:{checkpoint}"
    row = JobResult.query.filter_by(job_id=job_id, item_identifier=identifier).first()
    if row is None:
        row = JobResult(
            job_id=job_id,
            item_identifier=identifier,
            status="audit",
            result_data={"checkpoint": checkpoint},
        )
        db.session.add(row)
        db.session.commit()

    finalize_job(job_id=job_id)
    return {"job_id": job_id, "checkpoint": checkpoint, "idempotent": True}

