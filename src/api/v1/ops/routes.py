"""Operational observability and deployment guard endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import request
from flask_login import current_user, login_required
from pydantic import BaseModel, Field, ValidationError

from src.api.core.errors import ProblemDetails
from src.api.v1.ops import ops_bp
from src.assistant.deployment import (
    compute_availability_sli,
    evaluate_canary_rollback,
    redact_structured,
    redact_unstructured,
    retention_contract_snapshot,
    resolve_correlation_id,
)
from src.assistant.instrumentation import export_instrumentation_dataset
from src.assistant.instrumentation.export import export_enrichment_lineage_dataset
from src.core.sentry_metrics import count as sentry_count
from src.core.sentry_metrics import gauge as sentry_gauge


class SLIRequest(BaseModel):
    successful_requests: int = Field(ge=0)
    total_requests: int = Field(ge=0)
    user_errors: int = Field(ge=0)
    downtime_seconds_30d: int = Field(ge=0, default=0)


class CanaryRequest(BaseModel):
    baseline_availability: float = Field(ge=0.0, le=1.0)
    canary_availability: float = Field(ge=0.0, le=1.0)
    sample_size: int = Field(ge=0)
    scope_match: bool = True
    threshold_drop: float = Field(ge=0.0, default=0.05)
    sample_floor: int = Field(ge=1, default=100)


class RedactionPreviewRequest(BaseModel):
    payload: dict[str, Any] | list[Any] | str
    trace_text: str | None = None


class InstrumentationExportRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)
    tier: str | None = Field(default=None, pattern=r"^tier_[123]$")
    correlation_id: str | None = Field(default=None, max_length=96)
    action_id: int | None = Field(default=None, ge=1)
    start_at: datetime | None = None
    end_at: datetime | None = None
    limit: int = Field(default=250, ge=1, le=1000)


class EnrichmentAuditExportRequest(BaseModel):
    store_id: int | None = Field(default=None, ge=1)
    run_id: int | None = Field(default=None, ge=1)
    start_at: datetime | None = None
    end_at: datetime | None = None
    include_blocked: bool = True
    include_protected: bool = True
    limit: int = Field(default=500, ge=1, le=2000)


class SentryMetricsSmokeRequest(BaseModel):
    source: str = Field(default="ops_api", min_length=1, max_length=64)
    queue: str = Field(default="control", pattern=r"^[a-z0-9._-]+$")


def _resolve_store_scope(requested_store_id: int | None) -> int | None:
    user_store = getattr(current_user, "shopify_store", None)
    if requested_store_id is not None:
        if user_store is None or user_store.id != requested_store_id:
            return None
        return requested_store_id
    if user_store is None:
        return None
    return user_store.id


@ops_bp.route("/observability/sli", methods=["POST"])
@login_required
def compute_sli_snapshot():
    try:
        body = SLIRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)
    correlation_id = resolve_correlation_id(provided=request.headers.get("X-Correlation-Id"))
    computation = compute_availability_sli(
        successful_requests=body.successful_requests,
        total_requests=body.total_requests,
        user_errors=body.user_errors,
        downtime_seconds_30d=body.downtime_seconds_30d,
    )
    return {
        "correlation_id": correlation_id,
        "tenant_id": getattr(getattr(current_user, "shopify_store", None), "id", None),
        "sli": computation.to_dict(),
    }, 200


@ops_bp.route("/canary/evaluate", methods=["POST"])
@login_required
def evaluate_canary():
    try:
        body = CanaryRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)
    decision = evaluate_canary_rollback(
        baseline_availability=body.baseline_availability,
        canary_availability=body.canary_availability,
        sample_size=body.sample_size,
        scope_match=body.scope_match,
        threshold_drop=body.threshold_drop,
        sample_floor=body.sample_floor,
    )
    return {"decision": decision.to_dict()}, 200


@ops_bp.route("/redaction/preview", methods=["POST"])
@login_required
def preview_redaction():
    try:
        body = RedactionPreviewRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)
    structured = redact_structured(body.payload)
    text = redact_unstructured(body.trace_text or "")
    return {
        "structured_redacted": structured,
        "trace_redacted": text,
    }, 200


@ops_bp.route("/retention/policy", methods=["GET"])
@login_required
def retention_policy():
    return retention_contract_snapshot(), 200


@ops_bp.route("/instrumentation/export", methods=["POST"])
@login_required
def export_instrumentation():
    try:
        body = InstrumentationExportRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    scoped_store_id = _resolve_store_scope(body.store_id)
    if scoped_store_id is None:
        return ProblemDetails.business_error(
            "store-scope-required",
            "Store Scope Required",
            "Connect a Shopify store or provide a store_id belonging to the authenticated user.",
            status=409,
        )

    payload = export_instrumentation_dataset(
        store_id=scoped_store_id,
        tier=body.tier,
        correlation_id=body.correlation_id,
        action_id=body.action_id,
        start_at=body.start_at,
        end_at=body.end_at,
        limit=body.limit,
    )
    return payload, 200


@ops_bp.route("/enrichment/audit-export", methods=["POST"])
@login_required
def export_enrichment_audit():
    try:
        body = EnrichmentAuditExportRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    scoped_store_id = _resolve_store_scope(body.store_id)
    if scoped_store_id is None:
        return ProblemDetails.business_error(
            "store-scope-required",
            "Store Scope Required",
            "Connect a Shopify store or provide a store_id belonging to the authenticated user.",
            status=409,
        )
    payload = export_enrichment_lineage_dataset(
        store_id=scoped_store_id,
        run_id=body.run_id,
        start_at=body.start_at,
        end_at=body.end_at,
        include_blocked=body.include_blocked,
        include_protected=body.include_protected,
        limit=body.limit,
    )
    return payload, 200


@ops_bp.route("/sentry-metrics-smoke", methods=["POST"])
@login_required
def trigger_sentry_metrics_smoke():
    try:
        body = SentryMetricsSmokeRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    correlation_id = resolve_correlation_id(provided=request.headers.get("X-Correlation-Id"))
    sentry_count("api.sentry.smoke.request", 1, tags={"source": body.source})
    sentry_gauge("api.sentry.smoke.request_status", 1, tags={"source": body.source})

    from src.celery_app import app as celery_app

    task = celery_app.send_task(
        "src.tasks.control.sentry_metrics_smoke",
        kwargs={
            "source": body.source,
            "correlation_id": correlation_id,
        },
        queue=body.queue,
    )
    return {
        "status": "queued",
        "task_id": task.id,
        "queue": body.queue,
        "correlation_id": correlation_id,
    }, 202
