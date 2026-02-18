"""Snapshot lifecycle helpers for baseline/delta capture, TTL, and chain traversal."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from src.models import db
from src.models.resolution_batch import ResolutionBatch
from src.models.resolution_snapshot import ResolutionSnapshot

DEFAULT_DRY_RUN_TTL_MINUTES = 60
DEFAULT_BASELINE_MAX_AGE_HOURS = 24
DEFAULT_RETENTION_DAYS = 730
DEDUPE_ENABLED_TYPES = {"baseline", "batch_manifest"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def payload_checksum(payload: Any) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def stamp_batch_ttl(
    batch: ResolutionBatch,
    *,
    ttl_minutes: int = DEFAULT_DRY_RUN_TTL_MINUTES,
    now_utc: datetime | None = None,
) -> datetime:
    now = _as_utc(now_utc) if now_utc else _now()
    expires_at = now + timedelta(minutes=max(1, ttl_minutes))
    metadata = dict(batch.metadata_json or {})
    metadata["dry_run_ttl_minutes"] = int(max(1, ttl_minutes))
    metadata["expires_at"] = expires_at.isoformat()
    batch.metadata_json = metadata
    return expires_at


def parse_batch_expiry(batch: ResolutionBatch) -> datetime | None:
    metadata = dict(batch.metadata_json or {})
    expires_raw = metadata.get("expires_at")
    if not expires_raw:
        return None
    if isinstance(expires_raw, datetime):
        return _as_utc(expires_raw)
    if isinstance(expires_raw, str):
        value = expires_raw
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            return _as_utc(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def is_batch_fresh(
    batch: ResolutionBatch,
    *,
    now_utc: datetime | None = None,
    default_ttl_minutes: int = DEFAULT_DRY_RUN_TTL_MINUTES,
) -> bool:
    now = _as_utc(now_utc) if now_utc else _now()
    expiry = parse_batch_expiry(batch)
    if expiry is None:
        metadata = dict(batch.metadata_json or {})
        ttl = int(metadata.get("dry_run_ttl_minutes", default_ttl_minutes))
        base = _as_utc(batch.created_at or now)
        expiry = base + timedelta(minutes=max(1, ttl))
    return now <= expiry


def capture_snapshot(
    *,
    batch_id: int,
    item_id: int | None,
    snapshot_type: str,
    payload: dict[str, Any],
    parent_snapshot_id: int | None = None,
    allow_dedupe: bool = True,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> ResolutionSnapshot:
    checksum = payload_checksum(payload)
    canonical_snapshot_id: int | None = None
    stored_payload = payload

    if allow_dedupe and snapshot_type in DEDUPE_ENABLED_TYPES:
        canonical = (
            ResolutionSnapshot.query.filter(
                ResolutionSnapshot.batch_id == batch_id,
                ResolutionSnapshot.snapshot_type == snapshot_type,
                ResolutionSnapshot.checksum == checksum,
                ResolutionSnapshot.canonical_snapshot_id.is_(None),
            )
            .order_by(ResolutionSnapshot.id.asc())
            .first()
        )
        if canonical is not None:
            canonical_snapshot_id = canonical.id
            stored_payload = {"deduped_from": canonical.id}

    snapshot = ResolutionSnapshot(
        batch_id=batch_id,
        item_id=item_id,
        snapshot_type=snapshot_type,
        checksum=checksum,
        canonical_snapshot_id=canonical_snapshot_id or parent_snapshot_id,
        retention_expires_at=_now() + timedelta(days=max(1, retention_days)),
        payload=stored_payload,
    )
    db.session.add(snapshot)
    db.session.flush()
    return snapshot


def ensure_store_baseline(
    *,
    batch: ResolutionBatch,
    payload: dict[str, Any] | None = None,
    max_age_hours: int = DEFAULT_BASELINE_MAX_AGE_HOURS,
) -> tuple[ResolutionSnapshot, bool]:
    latest = (
        ResolutionSnapshot.query.join(ResolutionBatch, ResolutionSnapshot.batch_id == ResolutionBatch.id)
        .filter(
            ResolutionBatch.store_id == batch.store_id,
            ResolutionSnapshot.snapshot_type == "baseline",
        )
        .order_by(ResolutionSnapshot.created_at.desc())
        .first()
    )

    if latest is not None:
        age = (_now() - _as_utc(latest.created_at)).total_seconds()
        if age < max(1, max_age_hours) * 3600:
            return latest, False

    baseline_payload = payload or {
        "store_id": batch.store_id,
        "captured_from_batch_id": batch.id,
        "captured_at": _now().isoformat(),
    }
    created = capture_snapshot(
        batch_id=batch.id,
        item_id=None,
        snapshot_type="baseline",
        payload=baseline_payload,
        allow_dedupe=True,
    )
    return created, True


def resolve_snapshot_chain(*, batch_id: int, item_id: int | None = None) -> dict[str, Any]:
    batch = ResolutionBatch.query.filter_by(id=batch_id).first()
    if batch is None:
        raise ValueError(f"Resolution batch {batch_id} not found.")

    baseline = (
        ResolutionSnapshot.query.join(ResolutionBatch, ResolutionSnapshot.batch_id == ResolutionBatch.id)
        .filter(
            ResolutionBatch.store_id == batch.store_id,
            ResolutionSnapshot.snapshot_type == "baseline",
        )
        .order_by(ResolutionSnapshot.created_at.desc())
        .first()
    )
    manifest = (
        ResolutionSnapshot.query.filter_by(
            batch_id=batch.id,
            snapshot_type="batch_manifest",
        )
        .order_by(ResolutionSnapshot.created_at.desc())
        .first()
    )

    product_pre_change = None
    if item_id is not None:
        product_pre_change = (
            ResolutionSnapshot.query.filter_by(
                batch_id=batch.id,
                item_id=item_id,
                snapshot_type="product_pre_change",
            )
            .order_by(ResolutionSnapshot.created_at.desc())
            .first()
        )

    return {
        "batch_id": batch.id,
        "store_id": batch.store_id,
        "item_id": item_id,
        "baseline_snapshot_id": baseline.id if baseline else None,
        "manifest_snapshot_id": manifest.id if manifest else None,
        "product_pre_change_snapshot_id": product_pre_change.id if product_pre_change else None,
        "baseline_checksum": baseline.checksum if baseline else None,
        "manifest_checksum": manifest.checksum if manifest else None,
        "product_pre_change_checksum": product_pre_change.checksum if product_pre_change else None,
    }
