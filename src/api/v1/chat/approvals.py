"""Product-scoped chat approval and apply gates."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.assistant.governance import (
    evaluate_change_policy,
    get_field_policy_snapshot,
    verify_execution_finality,
)
from src.assistant.instrumentation import (
    InstrumentationLinkError,
    capture_preference_signal,
    capture_verification_signal,
    extract_action_runtime_context,
)
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


def _runtime_action_kind(action: ChatAction) -> str:
    payload = action.payload_json or {}
    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        action_kind = runtime.get("action_kind")
        if isinstance(action_kind, str) and action_kind:
            return action_kind
    if bool(payload.get("dry_run_required")):
        return "write"
    return "read"


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


def _verification_probe_for_action(*, action: ChatAction, apply_status: str):
    payload = action.payload_json if isinstance(action.payload_json, dict) else {}
    runtime = payload.get("runtime") if isinstance(payload.get("runtime"), dict) else {}
    verification_cfg = (
        runtime.get("verification") if isinstance(runtime.get("verification"), dict) else {}
    )
    forced_state = str(verification_cfg.get("forced_state") or "").strip().lower()

    def _probe(attempt_number: int, waited_seconds: int) -> dict[str, Any]:
        if forced_state == "deferred":
            return {
                "status": "deferred",
                "verified": False,
                "message": "Verification probe pending (forced deferred).",
                "attempt_number": attempt_number,
                "waited_seconds": waited_seconds,
            }
        if forced_state == "failed":
            return {
                "status": "failed",
                "verified": False,
                "message": "Verification probe failed (forced failed).",
                "attempt_number": attempt_number,
                "waited_seconds": waited_seconds,
            }
        if apply_status in {"applied", "applied_with_conflicts"}:
            return {
                "status": "verified",
                "verified": True,
                "message": "Verification confirmed from apply result state.",
                "attempt_number": attempt_number,
                "waited_seconds": waited_seconds,
            }
        return {
            "status": "failed",
            "verified": False,
            "message": "Apply result is not in a verifiable success state.",
            "attempt_number": attempt_number,
            "waited_seconds": waited_seconds,
        }

    return _probe


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
    if _runtime_action_kind(action) != "write":
        raise ApprovalError(
            error_type="read-action-approval-forbidden",
            title="Approval Not Allowed",
            detail="Read-only actions cannot enter approval/apply mutation flow.",
            status=409,
        )
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
    policy_snapshot = get_field_policy_snapshot(store_id=batch.store_id)
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
    immutable_blocked: list[dict[str, Any]] = []
    hitl_threshold_hits: list[dict[str, Any]] = []
    for change in all_changes:
        if change.status in BLOCKED_CHANGE_STATES:
            continue

        policy_decision = evaluate_change_policy(change=change, snapshot=policy_snapshot)
        if policy_decision.is_immutable:
            change.status = "blocked_exclusion"
            change.approved_by_user_id = actor_user_id
            immutable_blocked.append(
                {
                    "change_id": change.id,
                    "field_name": change.field_name,
                    "reason": policy_decision.reason,
                }
            )
            continue

        if policy_decision.requires_hitl:
            hitl_threshold_hits.append(
                {
                    "change_id": change.id,
                    "field_name": change.field_name,
                    "threshold_name": policy_decision.threshold_name,
                    "observed_value": policy_decision.observed_value,
                    "threshold_value": policy_decision.threshold_value,
                    "reason": policy_decision.reason,
                }
            )

        should_approve = (
            not has_explicit_selection or change.id in selected or change.status == "auto_applied"
        )
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
    metadata["policy_immutable_blocked"] = immutable_blocked
    metadata["policy_threshold_hits"] = hitl_threshold_hits
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
        "policy": {
            "field_policy_id": policy_snapshot.policy_id,
            "field_policy_version": policy_snapshot.policy_version,
            "immutable_blocked": immutable_blocked,
            "threshold_hits": hitl_threshold_hits,
            "requires_hitl": bool(hitl_threshold_hits),
        },
    }
    action.payload_json = payload
    action.status = "approved"
    action.approved_at = now
    action.error_message = None

    preference_signal = "edited" if override_map else ("approved_selection" if has_explicit_selection else "approved_all")
    runtime_ctx = extract_action_runtime_context(action)
    try:
        capture_preference_signal(
            action=action,
            user_id=actor_user_id,
            store_id=batch.store_id,
            session_id=action.session_id,
            tier=runtime_ctx.tier,
            correlation_id=runtime_ctx.correlation_id,
            preference_signal=preference_signal,
            signal_kind="edit" if override_map else "approval",
            selected_change_count=len(approved_ids),
            override_count=len(override_map),
            comment=comment,
            reasoning_trace_tokens=runtime_ctx.reasoning_trace_tokens,
            cost_usd=runtime_ctx.cost_usd,
            metadata_json={
                "rejected_change_count": len(rejected_ids),
                "immutable_blocked_count": len(immutable_blocked),
                "threshold_hit_count": len(hitl_threshold_hits),
                "approval_scope": "product",
            },
            require_link=True,
        )
    except InstrumentationLinkError as exc:
        raise ApprovalError(
            error_type="instrumentation-correlation-required",
            title="Instrumentation Link Required",
            detail=str(exc),
            status=409,
        ) from exc

    # Emit user approval episode (Phase 13.2)
    try:
        from src.tasks.graphiti_sync import emit_episode
        from src.core.synthex_entities import EpisodeType

        approval_payload = {
            'action_id': str(action.id),
            'action_type': 'product_action',
            'approval_decision': 'approved',
            'user_id': str(actor_user_id),
            'approved_at': now,
        }
        emit_episode.delay(
            EpisodeType.USER_APPROVAL.value,
            str(batch.store_id),
            approval_payload,
            correlation_id=runtime_ctx.correlation_id or f"chat-action-{action.id}"
        )
    except Exception:
        pass  # Fail-open: do not break approval flow if graph emission fails

    db.session.commit()
    return action


def apply_product_action(
    *,
    action: ChatAction,
    actor_user_id: int,
    mode: str | None = None,
) -> ChatAction:
    """Apply an approved product action through preflight + guarded apply."""
    if _runtime_action_kind(action) != "write":
        raise ApprovalError(
            error_type="read-action-apply-forbidden",
            title="Apply Not Allowed",
            detail="Read-only actions cannot be applied through mutation flow.",
            status=409,
        )
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
    policy_snapshot = get_field_policy_snapshot(store_id=batch.store_id)
    immutable_conflicts: list[dict[str, Any]] = []
    threshold_hits: list[dict[str, Any]] = []
    for item in batch.items.order_by("id").all():
        for change in item.changes.order_by("id").all():
            if change.status not in {"approved", "auto_applied"}:
                continue
            policy_decision = evaluate_change_policy(change=change, snapshot=policy_snapshot)
            if policy_decision.is_immutable:
                immutable_conflicts.append(
                    {
                        "change_id": change.id,
                        "field_name": change.field_name,
                        "reason": policy_decision.reason,
                    }
                )
            elif policy_decision.requires_hitl:
                threshold_hits.append(
                    {
                        "change_id": change.id,
                        "field_name": change.field_name,
                        "threshold_name": policy_decision.threshold_name,
                        "observed_value": policy_decision.observed_value,
                        "threshold_value": policy_decision.threshold_value,
                        "reason": policy_decision.reason,
                    }
                )

    if immutable_conflicts:
        raise ApprovalError(
            error_type="immutable-field-blocked",
            title="Immutable Fields Blocked",
            detail="Apply blocked because immutable field mutations were detected.",
            status=409,
            extensions={"immutable_conflicts": immutable_conflicts},
        )

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
    verification = verify_execution_finality(
        action_id=action.id,
        batch_id=batch.id,
        store_id=batch.store_id,
        user_id=actor_user_id,
        correlation_id=(action.idempotency_key or f"chat-action-{action.id}"),
        verification_probe=_verification_probe_for_action(action=action, apply_status=result.status),
        metadata_json={
            "result_status": result.status,
            "applied_item_ids": result.applied_item_ids,
        },
    )

    action_status = status_map.get(result.status, "completed")
    if verification.status == "deferred" and action_status in {"completed", "partial"}:
        action_status = "partial"
    elif verification.status == "failed" and action_status in {"completed", "partial"}:
        action_status = "failed"

    payload = dict(action.payload_json or {})
    payload["verification"] = verification.to_dict()
    action.payload_json = payload
    action.status = action_status
    action.applied_at = _now()
    action.completed_at = _now()
    if verification.status == "deferred":
        action.error_message = verification.message
    else:
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
        "verification": verification.to_dict(),
        "policy_threshold_hits": threshold_hits,
    }

    runtime_ctx = extract_action_runtime_context(action)
    try:
        capture_verification_signal(
            action=action,
            user_id=actor_user_id,
            store_id=batch.store_id,
            session_id=action.session_id,
            verification_event_id=verification.event_id,
            verification_status=verification.status,
            oracle_signal=verification.status == "verified",
            attempt_count=verification.attempt_count,
            waited_seconds=verification.waited_seconds,
            tier=runtime_ctx.tier,
            correlation_id=runtime_ctx.correlation_id,
            reasoning_trace_tokens=runtime_ctx.reasoning_trace_tokens,
            cost_usd=runtime_ctx.cost_usd,
            metadata_json={
                "result_status": result.status,
                "applied_item_count": len(result.applied_item_ids),
                "failed_item_count": len(result.failed_item_ids),
                "conflicted_item_count": len(result.conflicted_item_ids),
            },
            require_link=True,
        )
    except InstrumentationLinkError as exc:
        raise ApprovalError(
            error_type="instrumentation-correlation-required",
            title="Instrumentation Link Required",
            detail=str(exc),
            status=409,
        ) from exc

    # Emit vendor catalog change episode after successful apply (Phase 13.2)
    try:
        from src.tasks.graphiti_sync import emit_episode
        from src.core.synthex_entities import EpisodeType

        if result.status in {"applied", "applied_with_conflicts"} and result.applied_item_ids:
            change_payload = {
                'vendor_id': 'shopify',  # Shopify is the target system
                'change_type': 'product_update',
                'affected_product_count': len(result.applied_item_ids),
                'change_summary': f"Applied {len(result.applied_item_ids)} product changes via chat action",
            }
            emit_episode.delay(
                EpisodeType.VENDOR_CATALOG_CHANGE.value,
                str(batch.store_id),
                change_payload,
                correlation_id=runtime_ctx.correlation_id or f"chat-action-{action.id}"
            )
    except Exception:
        pass  # Fail-open: do not break apply flow if graph emission fails

    db.session.commit()
    return action
