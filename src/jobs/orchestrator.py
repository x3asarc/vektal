"""Phase 6 ingest orchestration and chunk execution service."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, List

from sqlalchemy import and_

from src.celery_app import app as celery_app
from src.jobs.checkpoints import crossed_checkpoints, upsert_checkpoint_intents
from src.jobs.queueing import normalize_tier, queue_for_tier
from src.models import (
    IngestChunk,
    IngestChunkStatus,
    Job,
    JobResult,
    JobStatus,
    JobType,
    Product,
    User,
    db,
)


DEFAULT_CHUNK_SIZE = int(os.getenv("INGEST_CHUNK_SIZE", "100"))
STALE_AFTER_MINUTES = int(os.getenv("INGEST_STALE_AFTER_MINUTES", "10"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _split_chunks(product_ids: List[int], chunk_size: int) -> Iterable[List[int]]:
    for start in range(0, len(product_ids), chunk_size):
        yield product_ids[start:start + chunk_size]


def _ingest_task_name_for_tier(tier: str | None) -> str:
    tier_key = normalize_tier(tier)
    suffix = {"tier_1": "t1", "tier_2": "t2", "tier_3": "t3"}[tier_key]
    return f"src.tasks.ingest.ingest_chunk_{suffix}"


def _active_ingest_exists(store_id: int, excluded_job_id: int) -> bool:
    active_statuses = [
        JobStatus.PENDING,
        JobStatus.QUEUED,
        JobStatus.RUNNING,
        JobStatus.CANCEL_REQUESTED,
    ]
    existing = (
        Job.query.filter(
            Job.store_id == store_id,
            Job.job_type == JobType.INGEST_CATALOG,
            Job.status.in_(active_statuses),
            Job.id != excluded_job_id,
        )
        .with_for_update(read=True)
        .first()
    )
    return existing is not None


def start_ingest(job_id: int, store_id: int, user_id: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> dict:
    """
    Freeze membership, create chunk rows, and enqueue tier-routed chunk tasks.

    Returns summary metadata for API response/tests.
    """
    job = (
        Job.query.filter_by(id=job_id, store_id=store_id, user_id=user_id)
        .with_for_update()
        .first()
    )
    if not job:
        raise ValueError("Job not found for start_ingest")

    if _active_ingest_exists(store_id=store_id, excluded_job_id=job_id):
        raise ValueError("Active ingest already exists for store")

    if job.is_terminal:
        raise ValueError(f"Cannot start terminal job status={job.status.value}")

    if job.status == JobStatus.CANCEL_REQUESTED:
        job.status = JobStatus.CANCELLED
        job.completed_at = _now()
        job.terminal_reason = "cancel_requested_before_queue"
        db.session.commit()
        return {
            "job_id": job.id,
            "store_id": store_id,
            "chunk_count": 0,
            "queued_task": None,
            "queue": None,
            "skipped": "cancel_requested",
        }

    ordered_ids = [
        row[0]
        for row in db.session.query(Product.id)
        .filter(Product.store_id == store_id)
        .order_by(Product.id.asc())
        .all()
    ]

    # Reset orchestration state if this endpoint is retried before worker starts.
    IngestChunk.query.filter_by(job_id=job.id).delete()
    job.total_products = len(ordered_ids)
    job.total_items = len(ordered_ids)
    job.processed_count = 0
    job.processed_items = 0
    job.successful_items = 0
    job.failed_items = 0
    job.status = JobStatus.QUEUED
    job.started_at = _now()

    chunks: list[IngestChunk] = []
    for idx, product_ids in enumerate(_split_chunks(ordered_ids, chunk_size)):
        chunks.append(
            IngestChunk(
                job_id=job.id,
                store_id=store_id,
                chunk_idx=idx,
                status=IngestChunkStatus.PENDING,
                attempts=0,
                processed_expected=len(product_ids),
                processed_actual=0,
                product_ids_json=product_ids,
            )
        )
    db.session.add_all(chunks)
    db.session.commit()

    user = User.query.get(user_id)
    tier_value = user.tier.value if user and user.tier else None
    task_name = _ingest_task_name_for_tier(tier_value)
    target_queue = queue_for_tier(tier_value, kind="batch")

    for chunk in chunks:
        async_result = celery_app.send_task(
            task_name,
            kwargs={"job_id": job.id, "store_id": store_id, "chunk_idx": chunk.chunk_idx},
            queue=target_queue,
        )
        chunk.task_id = async_result.id
    db.session.commit()

    return {
        "job_id": job.id,
        "store_id": store_id,
        "chunk_count": len(chunks),
        "queued_task": task_name,
        "queue": target_queue,
    }


def _claim_chunk(job: Job, chunk_idx: int, stale_after: timedelta) -> IngestChunk | None:
    """Claim pending chunk or reclaim stale in-progress chunk."""
    if job.status in {JobStatus.CANCEL_REQUESTED, JobStatus.CANCELLED}:
        return None

    chunk = (
        IngestChunk.query.filter_by(job_id=job.id, chunk_idx=chunk_idx)
        .with_for_update()
        .first()
    )
    if chunk is None:
        return None

    now = _now()
    stale_cutoff = now - stale_after

    if chunk.status in {IngestChunkStatus.COMPLETED, IngestChunkStatus.FAILED_TERMINAL}:
        return None

    if chunk.status == IngestChunkStatus.IN_PROGRESS and chunk.claimed_at and chunk.claimed_at > stale_cutoff:
        return None

    chunk.status = IngestChunkStatus.IN_PROGRESS
    chunk.claim_token = uuid.uuid4().hex
    chunk.claimed_at = now
    chunk.attempts += 1
    return chunk


def _record_chunk_results(job: Job, product_ids: list[int]) -> int:
    """Persist per-item outcomes idempotently."""
    inserted = 0
    for product_id in product_ids:
        identifier = f"product:{product_id}"
        exists = JobResult.query.filter_by(job_id=job.id, item_identifier=identifier).first()
        if exists:
            continue
        db.session.add(
            JobResult(
                job_id=job.id,
                item_identifier=identifier,
                status="success",
                result_data={"product_id": product_id},
            )
        )
        inserted += 1
    return inserted


def ingest_chunk(job_id: int, store_id: int, chunk_idx: int) -> dict:
    """
    Execute chunk with stale-aware claim/reclaim and idempotent completion.

    Progress increment and checkpoint intent creation happen in one transaction.
    """
    job = Job.query.filter_by(id=job_id, store_id=store_id).first()
    if not job:
        return {"skipped": True, "reason": "job-not-found"}

    stale_after = timedelta(minutes=STALE_AFTER_MINUTES)
    chunk = _claim_chunk(job=job, chunk_idx=chunk_idx, stale_after=stale_after)
    if chunk is None:
        db.session.rollback()
        return {"skipped": True, "reason": "not-claimed"}

    if job.status in {JobStatus.PENDING, JobStatus.QUEUED}:
        job.status = JobStatus.RUNNING

    frozen_ids = list(chunk.product_ids_json or [])
    processed_actual = len(frozen_ids)
    inserted_results = _record_chunk_results(job, frozen_ids)

    rowcount = (
        IngestChunk.query.filter(
            and_(
                IngestChunk.id == chunk.id,
                IngestChunk.status == IngestChunkStatus.IN_PROGRESS,
                IngestChunk.claim_token == chunk.claim_token,
            )
        )
        .update(
            {
                IngestChunk.status: IngestChunkStatus.COMPLETED,
                IngestChunk.processed_actual: processed_actual,
                IngestChunk.completed_at: _now(),
                IngestChunk.last_error: None,
            },
            synchronize_session=False,
        )
    )
    if rowcount != 1:
        db.session.rollback()
        return {"skipped": True, "reason": "already-completed-or-not-owned"}

    previous_count = job.processed_count
    new_count = min(job.total_products, previous_count + processed_actual)
    job.processed_count = new_count
    job.processed_items = new_count
    job.successful_items += processed_actual

    checkpoints = crossed_checkpoints(
        previous_count=previous_count,
        new_count=new_count,
        total_products=job.total_products,
    )
    upsert_checkpoint_intents(db.session, job=job, checkpoints=checkpoints)
    db.session.commit()

    return {
        "processed_actual": processed_actual,
        "inserted_results": inserted_results,
        "processed_count": new_count,
        "checkpoints_created": checkpoints,
    }
