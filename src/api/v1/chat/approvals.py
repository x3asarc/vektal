"""Product-scoped chat approval and apply gates."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import db
from src.models.chat_action import ChatAction
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch, ResolutionChange
from src.resolution.apply_engine import apply_batch
from src.resolution.preflight import run_preflight


BLOCKED_CHANGE_STATES = {"blocked_exclusion", "structural_conflict"}


class ApprovalError(Exception):
    """Raised when approval/apply prerequisites are not met."""

    def __init__(
        self,
        *,
        error_type: str,
        title: str,
        detail: str,
        status: int,
        extensions: dict[str, Any] | None = None,
    ):
        super().__init__(detail)
        self.error_type = error_type
        self.title = title
        self.detail = detail
        self.status = status
        self.extensions = extensions or {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dry_run_id(action: ChatAction) -> int:
    payload = action.payload_json or {}
    dry_run_id = payload.get("dry_run_id")
    if not isinstance(dry_run_id, int):
        raise ApprovalError(
            error_type="dry-run-required",
            title="Dry-Run Required",
            detail="This action has no dry-run reference and cannot be approved/applied.",
            status=409,
        )
    return dry_run_id


def _load_batch_for_action(action: ChatAction, *, actor_user_id: int) -> ResolutionBatch:
    dry_run_id = _dry_run_id(action)
    batch = ResolutionBatch.query.filter_by(id=dry_run_id, user_id=actor_user_id).first()
    if batch is None:
        raise ApprovalError(
            error_type="dry-run-not-found",
            title="Dry-Run Not Found",
            detail="Dry-run reference for this action was not found for this user.",
            status=404,
        )
    return batch


def require_dry_run(action: ChatAction) -> bool:
    payload = action.payload_json or {}
    return bool(payload.get("dry_run_required")) and isinstance(payload.get("dry_run_id"), int)


def approve_product_action(
    *,
    action: ChatAction,
    actor_user_id: int,
    selected_change_ids: list[int] | None = None,
    overrides: list[dict[str, Any]] | None = None,
    comment: str | None = None,
) -> ChatAction:
    """Approve a product-scoped action with optional field overrides."""
    if not require_dry_run(action):
        raise ApprovalError(
            error_type="dry-run-required",
            title="Dry-Run Required",
            detail="Action cannot be approved until a dry-run exists.",
            status=409,
        )
    if action.status not in {"dry_run_ready", "awaiting_approval", "approved"}:
        raise ApprovalError(
            error_type="invalid-action-state",
            title="Invalid Action State",
            detail=f"Action is {action.status}. Only dry_run_ready/awaiting_approval actions may be approved.",
            status=409,
        )

    batch = _load_batch_for_action(action, actor_user_id=actor_user_id)
    now = _now()
    selected = set(selected_change_ids or [])
    has_explicit_selection = len(selected) > 0

    override_map: dict[int, Any] = {}
    for override in overrides or []:
        change_id = override.get("change_id")
        if isinstance(change_id, int):
            override_map[change_id] = override.get("after_value")

    all_changes: list[ResolutionChange] = []
    for item in batch.items.order_by("id").all():
        all_changes.extend(item.changes.order_by("id").all())

    approved_ids: list[int] = []
    rejected_ids: list[int] = []
    for change in all_changes:
        if change.status in BLOCKED_CHANGE_STATES:
            continue
        should_approve = not has_explicit_selection or change.id in selected or change.status == "auto_applied"
        if should_approve:
            if change.id in override_map:
                change.after_value = override_map[change.id]
            change.status = "approved"
            change.approved_by_user_id = actor_user_id
            approved_ids.append(change.id)
        else:
            change.status = "rejected"
            change.approved_by_user_id = actor_user_id
            rejected_ids.append(change.id)

    metadata = dict(batch.metadata_json or {})
    if comment:
        metadata["chat_approval_comment"] = comment
    metadata["chat_approved_change_ids"] = approved_ids
    metadata["chat_rejected_change_ids"] = rejected_ids
    batch.metadata_json = metadata
    batch.status = "approved"
    batch.approved_by_user_id = actor_user_id
    batch.approved_at = now

    payload = dict(action.payload_json or {})
    payload["approval"] = {
        "scope": "product",
        "approved_change_ids": approved_ids,
        "rejected_change_ids": rejected_ids,
        "comment": comment,
    }
    action.payload_json = payload
    action.status = "approved"
    action.approved_at = now
    action.error_message = None

    db.session.commit()
    return action


def apply_product_action(
    *,
    action: ChatAction,
    actor_user_id: int,
    mode: str | None = None,
) -> ChatAction:
    """Apply an approved product action through preflight + guarded apply."""
    if not require_dry_run(action):
        raise ApprovalError(
            error_type="dry-run-required",
            title="Dry-Run Required",
            detail="Action cannot be applied without a dry-run.",
            status=409,
        )
    if action.status != "approved":
        raise ApprovalError(
            error_type="approval-required",
            title="Approval Required",
            detail="Approve this product action before apply.",
            status=409,
        )

    batch = _load_batch_for_action(action, actor_user_id=actor_user_id)
    preflight = run_preflight(batch_id=batch.id, actor_user_id=actor_user_id)
    if preflight.conflicted_item_ids:
        logs = (
            RecoveryLog.query.filter(
                RecoveryLog.batch_id == batch.id,
                RecoveryLog.item_id.in_(preflight.conflicted_item_ids),
            )
            .order_by(RecoveryLog.created_at.desc())
            .all()
        )
        action.status = "conflicted"
        action.applied_at = _now()
        action.completed_at = _now()
        action.error_message = "Conflicts detected during preflight. Resolve before apply."
        action.result_json = {
            "status": "conflicted",
            "conflicted_item_ids": preflight.conflicted_item_ids,
            "reasons": preflight.reasons,
            "recovery_log_ids": [log.id for log in logs],
        }
        db.session.commit()
        return action

    result = apply_batch(
        batch_id=batch.id,
        actor_user_id=actor_user_id,
        mode=mode,
        preflight_report=preflight,
    )
    logs = (
        RecoveryLog.query.filter_by(batch_id=batch.id)
        .order_by(RecoveryLog.created_at.desc())
        .limit(50)
        .all()
    )
    status_map = {
        "applied": "completed",
        "applied_with_conflicts": "partial",
        "failed": "failed",
        "cancelled": "cancelled",
    }
    action.status = status_map.get(result.status, "completed")
    action.applied_at = _now()
    action.completed_at = _now()
    action.error_message = None if action.status in {"completed", "partial"} else "Apply failed."
    action.result_json = {
        "status": result.status,
        "applied_item_ids": result.applied_item_ids,
        "conflicted_item_ids": result.conflicted_item_ids,
        "failed_item_ids": result.failed_item_ids,
        "paused": result.paused,
        "critical_errors": result.critical_errors,
        "backoff_events": result.backoff_events,
        "rerun_conflicted_item_ids": result.rerun_conflicted_item_ids,
        "recovery_log_ids": [log.id for log in logs],
    }
    db.session.commit()
    return action
