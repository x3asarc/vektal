"""Resolution rules and checkout-lock endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
import json

from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError

from src.api.core.errors import ProblemDetails
from src.api.v1.resolution import resolution_bp
from src.api.v1.resolution.schemas import (
    DryRunBatchResponse,
    DryRunCreateRequest,
    DryRunCreateResponse,
    DryRunFieldChangeResponse,
    DryRunLineageResponse,
    DryRunProductGroupResponse,
    LockResponse,
    ResolutionRuleListResponse,
    ResolutionRulePatch,
    ResolutionRuleRequest,
    ResolutionRuleResponse,
)
from src.models import db
from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch
from src.models.resolution_rule import ResolutionRule
from src.models.resolution_snapshot import ResolutionSnapshot
from src.models.shopify import ShopifyStore
from src.resolution.apply_engine import apply_batch
from src.resolution.audit_export import render_audit_export
from src.resolution.dry_run_compiler import compile_dry_run
from src.resolution.locks import acquire_batch_lock, heartbeat_batch_lock, release_batch_lock
from src.resolution.lineage import build_batch_lineage
from src.resolution.preflight import run_preflight
from src.resolution.progress_contract import build_apply_progress_payload
from src.resolution.snapshot_lifecycle import resolve_snapshot_chain


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def create_dry_run_batch_for_user(
    *,
    user_id: int,
    supplier_code: str,
    supplier_verified: bool,
    rows: list[dict],
    apply_mode: str = "immediate",
    scheduled_for: datetime | None = None,
) -> ResolutionBatch:
    """Shared dry-run builder used by API and chat orchestration paths."""
    store = ShopifyStore.query.filter_by(user_id=user_id, is_active=True).first()
    if store is None:
        raise ValueError("store-not-connected")

    for idx, row in enumerate(rows):
        if not any([row.get("sku"), row.get("barcode"), row.get("title")]):
            raise ValueError(f"invalid-row-{idx + 1}")

    return compile_dry_run(
        user_id=user_id,
        store_id=store.id,
        supplier_code=supplier_code,
        supplier_verified=supplier_verified,
        rows=rows,
        apply_mode=apply_mode,
        scheduled_for=scheduled_for,
    )


def _rule_to_response(rule: ResolutionRule) -> ResolutionRuleResponse:
    return ResolutionRuleResponse(
        id=rule.id,
        supplier_code=rule.supplier_code,
        field_group=rule.field_group,
        rule_type=rule.rule_type,
        action=rule.action,
        consented=bool(rule.consented),
        enabled=bool(rule.enabled),
        expires_at=_iso(rule.expires_at),
        config=rule.config,
        notes=rule.notes,
        created_at=_iso(rule.created_at),
        updated_at=_iso(rule.updated_at),
    )


def _get_batch_or_error(batch_id: int):
    batch = ResolutionBatch.query.filter_by(id=batch_id).first()
    if batch is None:
        return None, ProblemDetails.not_found("resolution-batch", batch_id)
    if batch.user_id != current_user.id:
        return None, ProblemDetails.forbidden("You do not have access to this resolution batch.")
    return batch, None


def _lock_conflict_response(batch: ResolutionBatch):
    return ProblemDetails.business_error(
        "batch-lock-conflict",
        "Batch Lock Conflict",
        "Another user is currently reviewing this batch.",
        status=409,
        lock_owner=batch.lock_owner_user_id,
        lock_expires_at=_iso(batch.lock_expires_at),
    )


def _serialize_recovery_log(row: RecoveryLog) -> dict:
    return {
        "id": row.id,
        "batch_id": row.batch_id,
        "item_id": row.item_id,
        "reason_code": row.reason_code,
        "reason_detail": row.reason_detail,
        "payload": row.payload,
        "replay_metadata": row.replay_metadata,
        "deferred_until": _iso(row.deferred_until),
        "snapshot_id": row.snapshot_id,
        "created_by_user_id": row.created_by_user_id,
        "created_at": _iso(row.created_at),
    }


@resolution_bp.route("/rules", methods=["GET"])
@login_required
def list_rules():
    supplier_code = request.args.get("supplier_code")
    field_group = request.args.get("field_group")

    query = ResolutionRule.query.filter_by(user_id=current_user.id).order_by(ResolutionRule.created_at.desc())
    if supplier_code:
        query = query.filter_by(supplier_code=supplier_code)
    if field_group:
        query = query.filter_by(field_group=field_group)

    rows = query.all()
    response = ResolutionRuleListResponse(
        rules=[_rule_to_response(row) for row in rows],
        total=len(rows),
    )
    return response.model_dump(), 200


@resolution_bp.route("/rules", methods=["POST"])
@login_required
def create_rule():
    try:
        payload = ResolutionRuleRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    rule = ResolutionRule(
        user_id=current_user.id,
        supplier_code=payload.supplier_code,
        field_group=payload.field_group,
        rule_type=payload.rule_type,
        action=payload.action,
        consented=payload.consented,
        enabled=payload.enabled,
        expires_at=payload.expires_at,
        config=payload.config,
        notes=payload.notes,
        created_by_user_id=current_user.id,
    )
    db.session.add(rule)
    db.session.commit()
    return _rule_to_response(rule).model_dump(), 201


@resolution_bp.route("/rules/<int:rule_id>", methods=["PATCH"])
@login_required
def patch_rule(rule_id: int):
    rule = ResolutionRule.query.filter_by(id=rule_id, user_id=current_user.id).first()
    if rule is None:
        return ProblemDetails.not_found("resolution-rule", rule_id)

    try:
        patch = ResolutionRulePatch(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    for key, value in patch.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    db.session.commit()
    return _rule_to_response(rule).model_dump(), 200


@resolution_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
@login_required
def delete_rule(rule_id: int):
    rule = ResolutionRule.query.filter_by(id=rule_id, user_id=current_user.id).first()
    if rule is None:
        return ProblemDetails.not_found("resolution-rule", rule_id)
    db.session.delete(rule)
    db.session.commit()
    return {"deleted": True, "rule_id": rule_id}, 200


@resolution_bp.route("/locks/<int:batch_id>", methods=["GET"])
@login_required
def get_lock(batch_id: int):
    batch = ResolutionBatch.query.filter_by(id=batch_id, user_id=current_user.id).first()
    if batch is None:
        return ProblemDetails.not_found("resolution-batch", batch_id)

    resp = LockResponse(
        batch_id=batch.id,
        locked=batch.lock_owner_user_id is not None,
        lock_owner_user_id=batch.lock_owner_user_id,
        lock_expires_at=_iso(batch.lock_expires_at),
        lock_heartbeat_at=_iso(batch.lock_heartbeat_at),
    )
    return resp.model_dump(), 200


@resolution_bp.route("/locks/<int:batch_id>/acquire", methods=["POST"])
@login_required
def acquire_lock(batch_id: int):
    lease_seconds = int((request.get_json(silent=True) or {}).get("lease_seconds", 300))
    batch = ResolutionBatch.query.filter_by(id=batch_id, user_id=current_user.id).first()
    if batch is None:
        return ProblemDetails.not_found("resolution-batch", batch_id)

    granted, locked_batch = acquire_batch_lock(
        batch_id=batch_id, user_id=current_user.id, lease_seconds=lease_seconds
    )
    status_code = 200 if granted else 409
    if not granted:
        return ProblemDetails.business_error(
            "batch-lock-conflict",
            "Batch Lock Conflict",
            "Another user is currently reviewing this batch.",
            status=409,
            lock_owner=locked_batch.lock_owner_user_id,
            lock_expires_at=_iso(locked_batch.lock_expires_at),
        )
    resp = LockResponse(
        batch_id=locked_batch.id,
        locked=True,
        lock_owner_user_id=locked_batch.lock_owner_user_id,
        lock_expires_at=_iso(locked_batch.lock_expires_at),
        lock_heartbeat_at=_iso(locked_batch.lock_heartbeat_at),
        granted=granted,
    )
    return resp.model_dump(), status_code


@resolution_bp.route("/locks/<int:batch_id>/heartbeat", methods=["POST"])
@login_required
def heartbeat_lock(batch_id: int):
    lease_seconds = int((request.get_json(silent=True) or {}).get("lease_seconds", 300))
    batch = ResolutionBatch.query.filter_by(id=batch_id, user_id=current_user.id).first()
    if batch is None:
        return ProblemDetails.not_found("resolution-batch", batch_id)

    ok = heartbeat_batch_lock(batch_id=batch_id, user_id=current_user.id, lease_seconds=lease_seconds)
    if not ok:
        return ProblemDetails.business_error(
            "batch-lock-not-owned",
            "Batch Lock Not Owned",
            "Cannot heartbeat a lock owned by another user.",
            status=409,
        )

    refreshed = ResolutionBatch.query.get(batch_id)
    resp = LockResponse(
        batch_id=batch_id,
        locked=refreshed.lock_owner_user_id is not None,
        lock_owner_user_id=refreshed.lock_owner_user_id,
        lock_expires_at=_iso(refreshed.lock_expires_at),
        lock_heartbeat_at=_iso(refreshed.lock_heartbeat_at),
        granted=True,
    )
    return resp.model_dump(), 200


@resolution_bp.route("/locks/<int:batch_id>/release", methods=["POST"])
@login_required
def release_lock(batch_id: int):
    batch = ResolutionBatch.query.filter_by(id=batch_id, user_id=current_user.id).first()
    if batch is None:
        return ProblemDetails.not_found("resolution-batch", batch_id)

    ok = release_batch_lock(batch_id=batch_id, user_id=current_user.id)
    if not ok:
        return ProblemDetails.business_error(
            "batch-lock-not-owned",
            "Batch Lock Not Owned",
            "Cannot release a lock owned by another user.",
            status=409,
        )
    return {"released": True, "batch_id": batch_id}, 200


@resolution_bp.route("/status", methods=["GET"])
@login_required
def resolution_status():
    """Lightweight health/status endpoint for frontend integration tests."""
    return {
        "status": "ok",
        "user_id": current_user.id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, 200


@resolution_bp.route("/dry-runs", methods=["POST"])
@login_required
def create_dry_run():
    try:
        payload = DryRunCreateRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc, status=422)

    rows = [row.model_dump() for row in payload.rows]
    try:
        batch = create_dry_run_batch_for_user(
            user_id=current_user.id,
            supplier_code=payload.supplier_code,
            supplier_verified=payload.supplier_verified,
            rows=rows,
            apply_mode=payload.apply_mode,
            scheduled_for=payload.scheduled_for,
        )
    except ValueError as exc:
        if str(exc) == "store-not-connected":
            return ProblemDetails.business_error(
                "store-not-connected",
                "Store Not Connected",
                "Connect a Shopify store before launching ingest jobs.",
                status=409,
            )
        if str(exc).startswith("invalid-row-"):
            row_idx = str(exc).split("-")[-1]
            return ProblemDetails.business_error(
                "invalid-dry-run-row",
                "Invalid Dry-Run Row",
                f"Row {row_idx} must include at least one identifier (sku, barcode, or title).",
                status=422,
            )
        raise

    manifest = ResolutionSnapshot.query.filter_by(
        batch_id=batch.id,
        snapshot_type="batch_manifest",
    ).first()
    counts = manifest.payload if manifest else {}
    response = DryRunCreateResponse(
        batch_id=batch.id,
        status=batch.status,
        apply_mode=batch.apply_mode,
        supplier_code=payload.supplier_code,
        counts=counts,
    )
    return response.model_dump(), 201


@resolution_bp.route("/dry-runs/<int:batch_id>", methods=["GET"])
@login_required
def get_dry_run(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error

    require_lock = request.args.get("require_lock", "false").lower() in {"1", "true", "yes"}
    if require_lock and batch.lock_owner_user_id not in (None, current_user.id):
        return _lock_conflict_response(batch)

    groups: list[DryRunProductGroupResponse] = []
    item_rows = batch.items.order_by("id").all()
    for item in item_rows:
        snapshot = ResolutionSnapshot.query.filter_by(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
        ).first()
        source_used = None
        if snapshot is not None:
            source_used = (snapshot.payload or {}).get("source_used")

        changes = []
        for change in item.changes.order_by("id").all():
            reason_factors = change.reason_factors or {}
            changes.append(
                DryRunFieldChangeResponse(
                    change_id=change.id,
                    field_group=change.field_group,
                    field_name=change.field_name,
                    before_value=change.before_value,
                    after_value=change.after_value,
                    status=change.status,
                    reason_sentence=change.reason_sentence,
                    reason_factors=reason_factors,
                    confidence_score=float(change.confidence_score) if change.confidence_score is not None else None,
                    confidence_badge=reason_factors.get("confidence_badge"),
                    applied_rule_id=change.applied_rule_id,
                    blocked_by_rule_id=change.blocked_by_rule_id,
                )
            )

        groups.append(
            DryRunProductGroupResponse(
                item_id=item.id,
                product_label=item.product_label,
                status=item.status,
                structural_state=item.structural_state,
                conflict_reason=item.conflict_reason,
                source_used=source_used,
                changes=changes,
            )
        )

    response = DryRunBatchResponse(
        batch_id=batch.id,
        status=batch.status,
        apply_mode=batch.apply_mode,
        scheduled_for=_iso(batch.scheduled_for),
        read_only=batch.lock_owner_user_id not in (None, current_user.id),
        lock_owner_user_id=batch.lock_owner_user_id,
        groups=groups,
    )
    return response.model_dump(), 200


@resolution_bp.route("/dry-runs/<int:batch_id>/lineage", methods=["GET"])
@login_required
def get_dry_run_lineage(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error

    entries = build_batch_lineage(batch)
    response = DryRunLineageResponse(batch_id=batch.id, entries=entries)
    return response.model_dump(), 200


@resolution_bp.route("/activity", methods=["GET"])
@login_required
def get_activity():
    current_rows = (
        ResolutionBatch.query.filter(
            ResolutionBatch.user_id == current_user.id,
            ResolutionBatch.status.in_(["ready_for_review", "applying"]),
        )
        .order_by(ResolutionBatch.updated_at.desc())
        .limit(20)
        .all()
    )
    next_rows = (
        ResolutionBatch.query.filter(
            ResolutionBatch.user_id == current_user.id,
            ResolutionBatch.status.in_(["approved", "scheduled"]),
        )
        .order_by(ResolutionBatch.scheduled_for.asc().nullslast(), ResolutionBatch.updated_at.desc())
        .limit(20)
        .all()
    )

    def to_activity(row: ResolutionBatch):
        mode = "review"
        if row.status == "applying":
            mode = "apply"
        elif row.status in {"approved", "scheduled"}:
            mode = "scheduled"
        return {
            "batchId": row.id,
            "label": row.metadata_json.get("supplier_code", f"Batch {row.id}") if row.metadata_json else f"Batch {row.id}",
            "ownerUserId": row.lock_owner_user_id,
            "mode": mode,
            "scheduledFor": _iso(row.scheduled_for),
            "status": row.status,
        }

    return {
        "currently_happening": [to_activity(row) for row in current_rows],
        "coming_up_next": [to_activity(row) for row in next_rows],
    }, 200


@resolution_bp.route("/suggestions", methods=["GET"])
@login_required
def list_suggestions():
    # Placeholder until learning engine materializes persisted suggestions.
    return {"suggestions": []}, 200


@resolution_bp.route("/suggestions/decline", methods=["POST"])
@login_required
def decline_suggestion():
    body = request.get_json(silent=True) or {}
    suggestion_id = body.get("suggestion_id")
    if not suggestion_id:
        return ProblemDetails.business_error(
            "missing-suggestion-id",
            "Missing Suggestion ID",
            "Provide suggestion_id when declining a suggestion.",
            status=422,
        )
    return {"declined": True, "suggestion_id": suggestion_id}, 200


@resolution_bp.route("/dry-runs/<int:batch_id>/preflight", methods=["POST"])
@login_required
def preflight_dry_run(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error

    report = run_preflight(batch_id=batch.id, actor_user_id=current_user.id)
    return {
        "batch_id": report.batch_id,
        "within_window": report.within_window,
        "eligible_item_ids": report.eligible_item_ids,
        "conflicted_item_ids": report.conflicted_item_ids,
        "reasons": report.reasons,
    }, 200


@resolution_bp.route("/dry-runs/<int:batch_id>/apply", methods=["POST"])
@login_required
def apply_dry_run(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error

    body = request.get_json(silent=True) or {}
    mode = body.get("mode") or batch.apply_mode
    threshold = body.get("critical_error_threshold")
    result = apply_batch(
        batch_id=batch.id,
        actor_user_id=current_user.id,
        mode=mode,
        critical_threshold=int(threshold) if threshold is not None else None,
    )
    return {
        "batch_id": result.batch_id,
        "status": result.status,
        "applied_item_ids": result.applied_item_ids,
        "conflicted_item_ids": result.conflicted_item_ids,
        "failed_item_ids": result.failed_item_ids,
        "deferred_item_ids": result.deferred_item_ids,
        "retryable_item_ids": result.retryable_item_ids,
        "paused": result.paused,
        "critical_errors": result.critical_errors,
        "backoff_events": result.backoff_events,
        "rerun_conflicted_item_ids": result.rerun_conflicted_item_ids,
        "terminal_summary": result.terminal_summary,
    }, 200


@resolution_bp.route("/dry-runs/<int:batch_id>/apply/progress", methods=["GET"])
@login_required
def get_apply_progress(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error
    return build_apply_progress_payload(batch), 200


@resolution_bp.route("/dry-runs/<int:batch_id>/snapshot-chain", methods=["GET"])
@login_required
def get_snapshot_chain(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error
    item_id = request.args.get("item_id", type=int)
    chain = resolve_snapshot_chain(batch_id=batch.id, item_id=item_id)
    return chain, 200


@resolution_bp.route("/dry-runs/<int:batch_id>/audit-export", methods=["GET"])
@login_required
def export_dry_run_audit(batch_id: int):
    batch, error = _get_batch_or_error(batch_id)
    if error:
        return error

    fmt = (request.args.get("format") or "json").strip().lower()
    try:
        rendered, content_type = render_audit_export(batch, fmt=fmt)
    except ValueError:
        return ProblemDetails.business_error(
            "unsupported-export-format",
            "Unsupported Export Format",
            "Use format=json or format=csv.",
            status=422,
        )

    if fmt == "json":
        return json.loads(rendered), 200
    return rendered, 200, {"Content-Type": content_type}


@resolution_bp.route("/recovery-logs", methods=["GET"])
@login_required
def list_recovery_logs():
    batch_id = request.args.get("batch_id", type=int)
    query = (
        RecoveryLog.query.join(ResolutionBatch, RecoveryLog.batch_id == ResolutionBatch.id)
        .filter(ResolutionBatch.user_id == current_user.id)
        .order_by(RecoveryLog.created_at.desc())
    )
    if batch_id is not None:
        query = query.filter(RecoveryLog.batch_id == batch_id)

    rows = query.limit(200).all()
    logs = [_serialize_recovery_log(row) for row in rows]
    return {"logs": logs, "total": len(logs)}, 200


@resolution_bp.route("/recovery-logs/<int:log_id>", methods=["GET"])
@login_required
def get_recovery_log(log_id: int):
    row = (
        RecoveryLog.query.join(ResolutionBatch, RecoveryLog.batch_id == ResolutionBatch.id)
        .filter(RecoveryLog.id == log_id, ResolutionBatch.user_id == current_user.id)
        .first()
    )
    if row is None:
        return ProblemDetails.not_found("recovery-log", log_id)
    return _serialize_recovery_log(row), 200


@resolution_bp.route("/recovery-logs/<int:log_id>/chain", methods=["GET"])
@login_required
def get_recovery_log_chain(log_id: int):
    row = (
        RecoveryLog.query.join(ResolutionBatch, RecoveryLog.batch_id == ResolutionBatch.id)
        .filter(RecoveryLog.id == log_id, ResolutionBatch.user_id == current_user.id)
        .first()
    )
    if row is None:
        return ProblemDetails.not_found("recovery-log", log_id)
    chain = resolve_snapshot_chain(batch_id=row.batch_id, item_id=row.item_id)
    return {"log": _serialize_recovery_log(row), "chain": chain}, 200
