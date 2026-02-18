"""Lease-based batch checkout lock service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models import db
from src.models.resolution_batch import ResolutionBatch


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _lock_expired(batch: ResolutionBatch, now: datetime) -> bool:
    expires_at = _as_utc(batch.lock_expires_at)
    return expires_at is None or expires_at <= now


def acquire_batch_lock(*, batch_id: int, user_id: int, lease_seconds: int = 300) -> tuple[bool, ResolutionBatch]:
    """
    Acquire lock for a review batch.

    Returns (granted, batch).
    """
    now = _now()
    batch = ResolutionBatch.query.filter_by(id=batch_id).with_for_update().first()
    if batch is None:
        raise ValueError("Batch not found")

    if batch.lock_owner_user_id in (None, user_id) or _lock_expired(batch, now):
        batch.lock_owner_user_id = user_id
        batch.lock_heartbeat_at = now
        batch.lock_expires_at = now + timedelta(seconds=max(30, lease_seconds))
        db.session.commit()
        return True, batch

    return False, batch


def heartbeat_batch_lock(*, batch_id: int, user_id: int, lease_seconds: int = 300) -> bool:
    """Extend lock lease when owner is active."""
    now = _now()
    batch = ResolutionBatch.query.filter_by(id=batch_id).with_for_update().first()
    if batch is None:
        raise ValueError("Batch not found")
    if batch.lock_owner_user_id != user_id:
        return False

    batch.lock_heartbeat_at = now
    batch.lock_expires_at = now + timedelta(seconds=max(30, lease_seconds))
    db.session.commit()
    return True


def release_batch_lock(*, batch_id: int, user_id: int) -> bool:
    """Release lock if caller is owner."""
    batch = ResolutionBatch.query.filter_by(id=batch_id).with_for_update().first()
    if batch is None:
        raise ValueError("Batch not found")
    if batch.lock_owner_user_id != user_id:
        return False

    batch.lock_owner_user_id = None
    batch.lock_heartbeat_at = None
    batch.lock_expires_at = None
    db.session.commit()
    return True

