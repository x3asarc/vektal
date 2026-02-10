"""Checkpoint policy and outbox upsert helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models import AuditCheckpoint, AuditDispatchStatus, Job


LOW_VOLUME_MILESTONES = [25, 35, 45, 55, 65, 75, 85, 95, 100]
HIGH_VOLUME_MILESTONES = [100]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def milestone_policy(total_products: int) -> list[int]:
    """Return locked checkpoint policy from Phase 6 context."""
    if total_products >= 1000:
        return HIGH_VOLUME_MILESTONES
    return LOW_VOLUME_MILESTONES


def crossed_checkpoints(
    previous_count: int,
    new_count: int,
    total_products: int,
) -> list[int]:
    """Compute newly crossed integer checkpoints."""
    if total_products <= 0:
        return []
    prev_percent = int((max(previous_count, 0) * 100) / total_products)
    new_percent = int((max(new_count, 0) * 100) / total_products)
    return [
        checkpoint
        for checkpoint in milestone_policy(total_products)
        if prev_percent < checkpoint <= new_percent
    ]


def upsert_checkpoint_intents(
    session,
    job: Job,
    checkpoints: Iterable[int],
) -> None:
    """Durably persist dispatch intents with idempotent upsert."""
    checkpoint_list: List[int] = sorted(set(int(c) for c in checkpoints))
    if not checkpoint_list:
        return

    bind = session.get_bind() if hasattr(session, "get_bind") else getattr(session, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", None)

    if dialect_name == "postgresql":
        for checkpoint in checkpoint_list:
            stmt = pg_insert(AuditCheckpoint).values(
                job_id=job.id,
                store_id=job.store_id,
                checkpoint=checkpoint,
                dispatch_status=AuditDispatchStatus.PENDING_DISPATCH,
                dispatch_attempts=0,
                next_dispatch_at=None,
                last_error=None,
                payload={"job_id": job.id, "checkpoint": checkpoint},
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[AuditCheckpoint.job_id, AuditCheckpoint.checkpoint],
                set_={
                    "dispatch_status": AuditDispatchStatus.PENDING_DISPATCH,
                    "next_dispatch_at": None,
                    "last_error": None,
                    "updated_at": now_utc(),
                },
            )
            session.execute(stmt)
        return

    # SQLite/test fallback
    for checkpoint in checkpoint_list:
        row = (
            session.query(AuditCheckpoint)
            .filter_by(job_id=job.id, checkpoint=checkpoint)
            .one_or_none()
        )
        if row is None:
            session.add(
                AuditCheckpoint(
                    job_id=job.id,
                    store_id=job.store_id,
                    checkpoint=checkpoint,
                    dispatch_status=AuditDispatchStatus.PENDING_DISPATCH,
                    dispatch_attempts=0,
                    payload={"job_id": job.id, "checkpoint": checkpoint},
                )
            )
            continue
        row.dispatch_status = AuditDispatchStatus.PENDING_DISPATCH
        row.next_dispatch_at = None
        row.last_error = None
        row.updated_at = now_utc()
