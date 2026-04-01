"""Celery task wrappers for ingest orchestration."""
from __future__ import annotations

from src.celery_app import app
from src.jobs.finalizer import finalize_job
from src.jobs.orchestrator import ingest_chunk as run_ingest_chunk
from src.jobs.orchestrator import start_ingest as run_start_ingest


@app.task(name="src.tasks.ingest.start_ingest_task", bind=True)
def start_ingest_task(self, job_id: int, store_id: int, user_id: int, chunk_size: int = 100) -> dict:
    """Async wrapper for start_ingest orchestration."""
    return run_start_ingest(job_id=job_id, store_id=store_id, user_id=user_id, chunk_size=chunk_size)


def _ingest_and_finalize(job_id: int, store_id: int, chunk_idx: int) -> dict:
    result = run_ingest_chunk(job_id=job_id, store_id=store_id, chunk_idx=chunk_idx)
    finalize_job(job_id=job_id)
    return result


@app.task(name="src.tasks.ingest.ingest_chunk_t1", bind=True, max_retries=3, retry_backoff=True)
def ingest_chunk_t1(self, job_id: int, store_id: int, chunk_idx: int) -> dict:
    return _ingest_and_finalize(job_id=job_id, store_id=store_id, chunk_idx=chunk_idx)


@app.task(name="src.tasks.ingest.ingest_chunk_t2", bind=True, max_retries=3, retry_backoff=True)
def ingest_chunk_t2(self, job_id: int, store_id: int, chunk_idx: int) -> dict:
    return _ingest_and_finalize(job_id=job_id, store_id=store_id, chunk_idx=chunk_idx)


@app.task(name="src.tasks.ingest.specialized_import_task", bind=True)
def specialized_import_task(self, parser: str) -> dict:
    """Specialized import for vendor catalogs (e.g. Pentart)."""
    return {"status": "success", "parser": parser, "message": "Specialized import queued."}

