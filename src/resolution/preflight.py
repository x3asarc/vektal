"""Pre-flight validation and recovery-log routing for apply safety."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.models import db
from src.models.product import Product
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionItem
from src.models.resolution_snapshot import ResolutionSnapshot
from src.resolution.snapshot_lifecycle import is_batch_fresh


@dataclass(frozen=True)
class PreflightReport:
    batch_id: int
    executed_at: datetime
    within_window: bool
    eligible_item_ids: list[int]
    conflicted_item_ids: list[int]
    reasons: dict[int, str]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _target_exists(batch: ResolutionBatch, item: ResolutionItem) -> bool:
    if item.product_id:
        return (
            Product.query.filter_by(
                id=item.product_id,
                store_id=batch.store_id,
                is_active=True,
            ).first()
            is not None
        )
    if item.shopify_product_id:
        return (
            Product.query.filter_by(
                shopify_product_id=item.shopify_product_id,
                store_id=batch.store_id,
                is_active=True,
            ).first()
            is not None
        )
    return False


def _upsert_recovery_log(
    *,
    batch: ResolutionBatch,
    item: ResolutionItem,
    reason_code: str,
    reason_detail: str,
    actor_user_id: int | None,
    replay_metadata: dict | None = None,
    deferred_until: datetime | None = None,
) -> None:
    existing = RecoveryLog.query.filter_by(
        batch_id=batch.id,
        item_id=item.id,
        reason_code=reason_code,
    ).first()
    if existing is not None:
        return

    snapshot = ResolutionSnapshot.query.filter_by(
        batch_id=batch.id,
        item_id=item.id,
        snapshot_type="product_pre_change",
    ).order_by(ResolutionSnapshot.created_at.desc()).first()

    log = RecoveryLog(
        batch_id=batch.id,
        item_id=item.id,
        store_id=batch.store_id,
        reason_code=reason_code,
        reason_detail=reason_detail,
        payload={
            "item_status": item.status,
            "product_label": item.product_label,
            "shopify_product_id": item.shopify_product_id,
            "shopify_variant_id": item.shopify_variant_id,
            "structural_state": item.structural_state,
            "conflict_reason": item.conflict_reason,
        },
        replay_metadata=replay_metadata,
        deferred_until=deferred_until,
        snapshot_id=snapshot.id if snapshot else None,
        created_by_user_id=actor_user_id,
    )
    db.session.add(log)


def run_preflight(
    *,
    batch_id: int,
    actor_user_id: int | None = None,
    mutation_started_at: datetime | None = None,
    max_window_seconds: int = 60,
) -> PreflightReport:
    """
    Validate targets immediately before apply and route stale conflicts.

    Returns the split between eligible and conflicted item ids.
    """
    batch = ResolutionBatch.query.filter_by(id=batch_id).first()
    if batch is None:
        raise ValueError(f"Resolution batch {batch_id} not found.")

    now = _now()
    started_at = _as_utc(mutation_started_at) if mutation_started_at else now
    within_execute_window = (now - started_at).total_seconds() <= max_window_seconds
    batch_is_fresh = is_batch_fresh(batch, now_utc=now)
    within_window = within_execute_window and batch_is_fresh

    eligible: list[int] = []
    conflicted: list[int] = []
    reasons: dict[int, str] = {}

    items = batch.items.order_by("id").all()
    for item in items:
        reason_code: str | None = None
        reason_detail: str | None = None

        if not batch_is_fresh:
            reason_code = "stale_target"
            reason_detail = "Dry-run TTL expired; refresh via recompile before apply."
        elif item.status == "structural_conflict":
            reason_code = "preflight_conflict"
            reason_detail = item.conflict_reason or "Item is still in structural conflict state."
        elif not _target_exists(batch, item):
            reason_code = "deleted_target"
            reason_detail = (
                "Target product/variant no longer exists in Shopify state; "
                "item preserved in Recovery Logs."
            )

        if reason_code:
            conflicted.append(item.id)
            reasons[item.id] = reason_code
            _upsert_recovery_log(
                batch=batch,
                item=item,
                reason_code=reason_code,
                reason_detail=reason_detail or "",
                actor_user_id=actor_user_id,
                replay_metadata={
                    "batch_id": batch.id,
                    "item_id": item.id,
                    "reason": reason_code,
                    "replay_action": "rerun_dry_run",
                }
                if reason_code == "stale_target"
                else None,
            )
        else:
            eligible.append(item.id)

    db.session.commit()
    return PreflightReport(
        batch_id=batch.id,
        executed_at=now,
        within_window=within_window,
        eligible_item_ids=eligible,
        conflicted_item_ids=conflicted,
        reasons=reasons,
    )
