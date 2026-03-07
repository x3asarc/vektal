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


def _finalize_product_metrics(job: Job) -> None:
    """
    Compute completeness scores for all products in the store and update watermarks.
    
    This is triggered upon successful completion of an ingest job.
    """
    if not job.store_id:
        return

    # 1. Update Completeness Scores for all products in this store
    from src.models.product import Product
    from src.core.products.completeness import calculate_completeness
    
    # We load all products for the store. 
    # For very large catalogs (>10k), we might want to chunk this, 
    # but for Phase 17's target (4k SKUs), a single batch is efficient.
    products = Product.query.filter_by(store_id=job.store_id).all()
    
    updates = []
    for p in products:
        metrics = calculate_completeness(p)
        updates.append({
            "id": p.id,
            "completeness_score": metrics["completeness_score"]
        })
        
    if updates:
        db.session.bulk_update_mappings(Product, updates)

    # 2. Update Store Watermarks if this was a Shopify Ingest
    from src.models.job import JobType
    if job.job_type == JobType.INGEST_SHOPIFY:
        store = job.store
        if store:
            store.last_full_ingest_at = _now()
            # Cursor is stored in job parameters if provided by the scraper/ingest logic
            if job.parameters and "last_shopify_cursor" in job.parameters:
                store.last_shopify_cursor = job.parameters["last_shopify_cursor"]

    db.session.commit()


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

        # Emit vendor catalog change episode (Phase 13.2)
        try:
            from src.tasks.graphiti_sync import emit_episode
            from src.core.synthex_entities import EpisodeType

            ingest_summary = {
                'vendor_id': 'shopify',
                'change_type': 'catalog_ingest',
                'affected_product_count': job.total_products or 0,
                'change_summary': f"Vendor catalog ingest completed for job {job.id}",
            }
            emit_episode.delay(
                EpisodeType.VENDOR_CATALOG_CHANGE.value,
                str(job.store_id),
                ingest_summary,
                correlation_id=f"ingest-job-{job.id}"
            )
        except Exception:
            pass  # Fail-open: do not break ingest flow if graph emission fails

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

    if job.status == JobStatus.COMPLETED:
        # Phase 17: Update product completeness metrics and watermarks
        from src.models.job import JobType
        if job.job_type in {JobType.INGEST_CATALOG, JobType.INGEST_SHOPIFY}:
            try:
                _finalize_product_metrics(job)
            except Exception as e:
                # Fail-open: don't break the whole finalizer if metrics fail
                print(f"Error finalizing product metrics for job {job.id}: {e}")

        try:
            from src.tasks.graphiti_sync import emit_episode
            from src.core.synthex_entities import EpisodeType

            ingest_summary = {
                'vendor_id': 'shopify',
                'change_type': 'catalog_ingest',
                'affected_product_count': job.successful_items or 0,
                'change_summary': f"Vendor catalog ingest finalized for job {job.id} ({job.successful_items} products)",
            }
            emit_episode.delay(
                EpisodeType.VENDOR_CATALOG_CHANGE.value,
                str(job.store_id),
                ingest_summary,
                correlation_id=f"ingest-job-{job.id}"
            )
        except Exception:
            pass  # Fail-open: do not break ingest flow if graph emission fails

    return {"status": "finalized", "job_status": job.status.value, "mode": finalizer_mode}
