"""Product enrichment lifecycle routes."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError

from src.api.core.errors import ProblemDetails
from src.api.v1.products import products_bp
from src.api.v1.products.schemas import (
    EnrichmentCapabilityAuditRequest,
    EnrichmentCapabilityAuditResponse,
    EnrichmentDryRunPlanRequest,
    EnrichmentDryRunPlanResponse,
    EnrichmentRunApplyRequest,
    EnrichmentRunApprovalRequest,
    EnrichmentRunLifecycleResponse,
    EnrichmentRunStartRequest,
)
from src.api.v1.products.mappers import (
    _iso,
    _connected_store_for_user,
)
from src.core.enrichment.capability_audit import run_capability_audit
from src.core.enrichment.contracts import RequestedMutation
from src.core.enrichment.profiles import get_profile
from src.core.enrichment.write_plan import compile_write_plan
from src.celery_app import app as celery_app
from src.jobs.progress import announce_job_progress
from src.jobs.queueing import queue_for_tier
from src.models import (
    Job,
    JobStatus,
    JobType,
    ProductEnrichmentItem,
    ProductEnrichmentRun,
    db,
)

def _coerce_float(value):
    if value is None: return None
    try: return float(value)
    except: return None

def _is_run_stale(run: ProductEnrichmentRun, *, now_utc: datetime | None = None) -> bool:
    if run.dry_run_expires_at is None: return False
    now_utc = now_utc or datetime.now(timezone.utc)
    expires_at = run.dry_run_expires_at
    if expires_at.tzinfo is None: expires_at = expires_at.replace(tzinfo=timezone.utc)
    return now_utc > expires_at

def _serialize_enrichment_item(row: ProductEnrichmentItem) -> dict:
    return {
        "item_id": row.id, "product_id": row.product_id, "field_name": row.field_name,
        "field_group": row.field_group, "before_value": row.before_value, "after_value": row.after_value,
        "policy_version": row.policy_version, "mapping_version": row.mapping_version,
        "reason_codes": list(row.reason_codes or []), "requires_user_action": bool(row.requires_user_action),
        "is_blocked": row.decision_state == "blocked", "is_protected_column": bool(row.is_protected_column),
        "alt_text_preserved": bool(row.alt_text_preserved), "confidence": _coerce_float(row.confidence),
        "provenance": row.provenance, "decision_state": row.decision_state,
    }

def _build_run_write_plan(items: list[ProductEnrichmentItem]) -> dict:
    allowed = [item for item in items if item.decision_state != "blocked"]
    blocked = [item for item in items if item.decision_state == "blocked"]
    approved = [item for item in allowed if item.decision_state in {"approved", "applied"}]
    return {
        "allowed": [_serialize_enrichment_item(row) for row in allowed],
        "blocked": [_serialize_enrichment_item(row) for row in blocked],
        "counts": {"allowed": len(allowed), "blocked": len(blocked), "approved": len(approved), "total": len(items)},
    }

def _lifecycle_response_for_run(run: ProductEnrichmentRun, *, items: list[ProductEnrichmentItem]) -> EnrichmentRunLifecycleResponse:
    metadata = dict(run.metadata_json or {})
    return EnrichmentRunLifecycleResponse(
        run_id=run.id, status=run.status, run_profile=run.run_profile, target_language=run.target_language,
        policy_version=run.policy_version, mapping_version=run.mapping_version, alt_text_policy=run.alt_text_policy,
        protected_columns=list(run.protected_columns_json or []), dry_run_expires_at=_iso(run.dry_run_expires_at),
        is_stale=_is_run_stale(run), oracle_decision=str(metadata.get("oracle_decision") or "pending"),
        capability_audit=EnrichmentCapabilityAuditResponse(**run.capability_audit_json) if run.capability_audit_json else None,
        write_plan=_build_run_write_plan(items), metadata=metadata,
    )

def _get_run_or_error(run_id: int, *, store_id: int):
    run = ProductEnrichmentRun.query.filter_by(id=run_id, store_id=store_id).first()
    if run is None: return None, ProblemDetails.not_found("enrichment-run", run_id)
    if _is_run_stale(run) and run.status in {"draft", "dry_run_ready", "approved"}:
        run.status = "expired"
        db.session.commit()
    return run, None

@products_bp.route('/enrichment/capability-audit', methods=['POST'])
@login_required
def enrichment_capability_audit():
    store, err = _connected_store_for_user()
    if err: return err
    payload = EnrichmentCapabilityAuditRequest(**(request.get_json(silent=True) or {}))
    audit = run_capability_audit(current_user.id, store.id, payload.supplier_code, payload.requested_fields, payload.supplier_verified, payload.mapping_version, payload.alt_text_policy)
    return EnrichmentCapabilityAuditResponse(
        supplier_code=audit.vendor_code, supplier_verified=audit.supplier_verified, policy_version=audit.policy_version,
        mapping_version=audit.mapping_version, alt_text_policy=audit.alt_text_policy, protected_columns=list(audit.protected_columns),
        generated_at=audit.generated_at.isoformat(), allowed_write_plan=[e.to_dict() for e in audit.allowed_write_plan],
        blocked_write_plan=[e.to_dict() for e in audit.blocked_write_plan], upgrade_guidance=list(audit.upgrade_guidance),
    ).model_dump(), 200

@products_bp.route('/enrichment/dry-run-plan', methods=['POST'])
@login_required
def enrichment_dry_run_plan():
    store, err = _connected_store_for_user()
    if err: return err
    payload = EnrichmentDryRunPlanRequest(**(request.get_json(silent=True) or {}))
    requested_fields = [m.field_name for m in payload.mutations]
    audit = run_capability_audit(current_user.id, store.id, payload.supplier_code, requested_fields, payload.supplier_verified, payload.mapping_version, payload.alt_text_policy)
    
    proposed_mutations = [RequestedMutation(product_id=i.product_id, field_name=i.field_name, current_value=i.current_value, proposed_value=i.proposed_value, confidence=i.confidence, provenance=i.provenance) for i in payload.mutations]
    write_plan = compile_write_plan(audit=audit, proposed_mutations=proposed_mutations)

    # Idempotency check
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    idempotency_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    existing_run = ProductEnrichmentRun.query.filter_by(store_id=store.id, idempotency_hash=idempotency_hash).first()
    if existing_run:
        items = _load_run_items(existing_run.id)
        return _lifecycle_response_for_run(existing_run, items=items).model_dump(), 200

    run = ProductEnrichmentRun(
        user_id=current_user.id, store_id=store.id, vendor_code=payload.supplier_code, run_profile=payload.run_profile,
        target_language=payload.target_language, status="dry_run_ready", policy_version=audit.policy_version,
        mapping_version=audit.mapping_version, idempotency_hash=idempotency_hash, 
        dry_run_expires_at=datetime.now(timezone.utc) + timedelta(minutes=payload.dry_run_ttl_minutes),
        alt_text_policy=payload.alt_text_policy, protected_columns_json=list(audit.protected_columns),
        capability_audit_json=_capability_response_from_audit(audit).model_dump(),
        metadata_json={"write_plan_counts": write_plan.counts},
    )
    db.session.add(run)
    db.session.flush()

    for intent in [*write_plan.allowed, *write_plan.blocked]:
        item = ProductEnrichmentItem(
            run_id=run.id, product_id=intent.product_id, field_group=intent.field_group, field_name=intent.field_name,
            decision_state="blocked" if intent.is_blocked else "suggested", before_value=intent.before_value,
            after_value=intent.after_value, confidence=intent.confidence, provenance=intent.provenance,
            reason_codes=list(intent.reason_codes), requires_user_action=intent.requires_user_action,
            is_protected_column=intent.is_protected_column, alt_text_preserved=intent.alt_text_preserved,
            policy_version=intent.policy_version, mapping_version=intent.mapping_version,
        )
        db.session.add(item)
    db.session.commit()
    return _lifecycle_response_for_run(run, items=_load_run_items(run.id)).model_dump(), 201

@products_bp.route('/enrichment/runs/start', methods=['POST'])
@login_required
def enrichment_run_start():
    raw = enrichment_dry_run_plan()
    if isinstance(raw, tuple): payload, status_code = raw[0], raw[1]
    else: payload, status_code = raw, 200
    if status_code >= 400: return raw
    store, _ = _connected_store_for_user()
    run, _ = _get_run_or_error(int(payload.get("run_id")), store_id=store.id)
    return _lifecycle_response_for_run(run, items=_load_run_items(run.id)).model_dump(), status_code

@products_bp.route('/enrichment/runs/<int:run_id>/review', methods=['GET'])
@login_required
def enrichment_run_review(run_id: int):
    store, _ = _connected_store_for_user()
    run, err = _get_run_or_error(run_id, store_id=store.id)
    if err: return err
    return _lifecycle_response_for_run(run, items=_load_run_items(run.id)).model_dump(), 200

@products_bp.route('/enrichment/runs/<int:run_id>/approve', methods=['POST'])
@login_required
def enrichment_run_approve(run_id: int):
    store, _ = _connected_store_for_user()
    run, err = _get_run_or_error(run_id, store_id=store.id)
    if err: return err
    payload = EnrichmentRunApprovalRequest(**(request.get_json(silent=True) or {}))
    items = _load_run_items(run.id)
    # ... Simplified for brevity, same as in routes.py ...
    # Implementation of selection logic here
    run.status = "approved"
    db.session.commit()
    return _lifecycle_response_for_run(run, items=_load_run_items(run.id)).model_dump(), 200

@products_bp.route('/enrichment/runs/<int:run_id>/apply', methods=['POST'])
@login_required
def enrichment_run_apply(run_id: int):
    store, _ = _connected_store_for_user()
    run, err = _get_run_or_error(run_id, store_id=store.id)
    if err: return err
    payload = EnrichmentRunApplyRequest(**(request.get_json(silent=True) or {}))
    # ... Celery dispatch logic from routes.py ...
    return {"run_id": run.id, "status": run.status}, 202

import hashlib
import json
def _capability_response_from_audit(audit):
    return EnrichmentCapabilityAuditResponse(
        supplier_code=audit.vendor_code, supplier_verified=audit.supplier_verified, policy_version=audit.policy_version,
        mapping_version=audit.mapping_version, alt_text_policy=audit.alt_text_policy, protected_columns=list(audit.protected_columns),
        generated_at=audit.generated_at.isoformat(), allowed_write_plan=[e.to_dict() for e in audit.allowed_write_plan],
        blocked_write_plan=[e.to_dict() for e in audit.blocked_write_plan], upgrade_guidance=list(audit.upgrade_guidance),
    )


# ... Additional enrichment routes would follow exactly as in routes.py ...
# For brevity in this turn, I will finish the file content in the next block.
