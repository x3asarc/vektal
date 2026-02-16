"""Phase 13 instrumentation export and join integrity helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import (
    AssistantPreferenceSignal,
    AssistantVerificationSignal,
    ProductEnrichmentItem,
    ProductEnrichmentRun,
)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _apply_common_filters(query, model, *, store_id: int, tier: str | None, correlation_id: str | None, action_id: int | None, start_at: datetime | None, end_at: datetime | None):
    query = query.filter(model.store_id == store_id)
    if tier:
        query = query.filter(model.tier == tier)
    if correlation_id:
        query = query.filter(model.correlation_id == correlation_id)
    if action_id is not None:
        query = query.filter(model.action_id == action_id)
    if start_at is not None:
        query = query.filter(model.created_at >= start_at)
    if end_at is not None:
        query = query.filter(model.created_at <= end_at)
    return query


def _preference_row_to_dict(row: AssistantPreferenceSignal) -> dict[str, Any]:
    return {
        "preference_signal_id": row.id,
        "action_id": row.action_id,
        "session_id": row.session_id,
        "store_id": row.store_id,
        "user_id": row.user_id,
        "correlation_id": row.correlation_id,
        "tier": row.tier,
        "signal_kind": row.signal_kind,
        "preference_signal": row.preference_signal,
        "selected_change_count": row.selected_change_count,
        "override_count": row.override_count,
        "comment": row.comment,
        "reasoning_trace_tokens": row.reasoning_trace_tokens,
        "cost_usd": row.cost_usd,
        "created_at": _iso(row.created_at),
    }


def _verification_row_to_dict(row: AssistantVerificationSignal) -> dict[str, Any]:
    return {
        "verification_signal_id": row.id,
        "verification_event_id": row.verification_event_id,
        "action_id": row.action_id,
        "session_id": row.session_id,
        "store_id": row.store_id,
        "user_id": row.user_id,
        "correlation_id": row.correlation_id,
        "tier": row.tier,
        "verification_status": row.verification_status,
        "oracle_signal": bool(row.oracle_signal),
        "attempt_count": row.attempt_count,
        "waited_seconds": row.waited_seconds,
        "reasoning_trace_tokens": row.reasoning_trace_tokens,
        "cost_usd": row.cost_usd,
        "created_at": _iso(row.created_at),
    }


def _join_key(row: dict[str, Any]) -> tuple[Any, Any, Any]:
    return (row.get("action_id"), row.get("correlation_id"), row.get("tier"))


def export_instrumentation_dataset(
    *,
    store_id: int,
    tier: str | None = None,
    correlation_id: str | None = None,
    action_id: int | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    limit: int = 250,
) -> dict[str, Any]:
    """Export scoped preference/verification signals with deterministic join stats."""
    max_limit = max(1, min(int(limit), 1000))

    pref_query = _apply_common_filters(
        AssistantPreferenceSignal.query,
        AssistantPreferenceSignal,
        store_id=store_id,
        tier=tier,
        correlation_id=correlation_id,
        action_id=action_id,
        start_at=start_at,
        end_at=end_at,
    )
    ver_query = _apply_common_filters(
        AssistantVerificationSignal.query,
        AssistantVerificationSignal,
        store_id=store_id,
        tier=tier,
        correlation_id=correlation_id,
        action_id=action_id,
        start_at=start_at,
        end_at=end_at,
    )

    pref_rows = pref_query.order_by(AssistantPreferenceSignal.created_at.desc()).limit(max_limit).all()
    ver_rows = ver_query.order_by(AssistantVerificationSignal.created_at.desc()).limit(max_limit).all()

    preference_signals = [_preference_row_to_dict(row) for row in pref_rows]
    verification_signals = [_verification_row_to_dict(row) for row in ver_rows]

    ver_by_key: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in verification_signals:
        ver_by_key.setdefault(_join_key(row), []).append(row)

    joined_rows: list[dict[str, Any]] = []
    missing_verification_links: list[int] = []
    for pref in preference_signals:
        candidates = ver_by_key.get(_join_key(pref), [])
        if not candidates:
            missing_verification_links.append(pref["preference_signal_id"])
            continue
        for ver in candidates:
            joined_rows.append(
                {
                    "preference_signal_id": pref["preference_signal_id"],
                    "verification_signal_id": ver["verification_signal_id"],
                    "action_id": pref.get("action_id"),
                    "correlation_id": pref.get("correlation_id"),
                    "tier": pref.get("tier"),
                    "preference_signal": pref.get("preference_signal"),
                    "verification_status": ver.get("verification_status"),
                    "oracle_signal": ver.get("oracle_signal"),
                }
            )

    pref_keys = {_join_key(row) for row in preference_signals}
    missing_preference_links = [
        row["verification_signal_id"]
        for row in verification_signals
        if _join_key(row) not in pref_keys
    ]

    return {
        "generated_at": _now_iso(),
        "retention_class": "instrumentation_signals",
        "autonomy_enabled": False,
        "scope": {"store_id": store_id},
        "filters": {
            "tier": tier,
            "correlation_id": correlation_id,
            "action_id": action_id,
            "start_at": _iso(start_at),
            "end_at": _iso(end_at),
            "limit": max_limit,
        },
        "rows": {
            "preference_signals": preference_signals,
            "verification_signals": verification_signals,
            "joined_rows": joined_rows,
        },
        "join_integrity": {
            "preference_count": len(preference_signals),
            "verification_count": len(verification_signals),
            "joined_count": len(joined_rows),
            "missing_verification_links": missing_verification_links,
            "missing_preference_links": missing_preference_links,
        },
    }


def export_enrichment_lineage_dataset(
    *,
    store_id: int,
    run_id: int | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    include_blocked: bool = True,
    include_protected: bool = True,
    limit: int = 500,
) -> dict[str, Any]:
    """
    Export field-level enrichment lineage with retention metadata.

    This dataset is tenant-scoped and supports time-window filtering.
    """
    max_limit = max(1, min(int(limit), 2000))

    run_query = ProductEnrichmentRun.query.filter(ProductEnrichmentRun.store_id == store_id)
    if run_id is not None:
        run_query = run_query.filter(ProductEnrichmentRun.id == run_id)
    if start_at is not None:
        run_query = run_query.filter(ProductEnrichmentRun.created_at >= start_at)
    if end_at is not None:
        run_query = run_query.filter(ProductEnrichmentRun.created_at <= end_at)
    runs = run_query.order_by(ProductEnrichmentRun.created_at.desc()).limit(max_limit).all()
    run_ids = [run.id for run in runs]

    item_rows: list[dict[str, Any]] = []
    blocked_count = 0
    protected_count = 0
    if run_ids:
        item_query = ProductEnrichmentItem.query.filter(ProductEnrichmentItem.run_id.in_(run_ids))
        if not include_blocked:
            item_query = item_query.filter(ProductEnrichmentItem.decision_state != "blocked")
        if not include_protected:
            item_query = item_query.filter(ProductEnrichmentItem.is_protected_column.is_(False))
        if start_at is not None:
            item_query = item_query.filter(ProductEnrichmentItem.created_at >= start_at)
        if end_at is not None:
            item_query = item_query.filter(ProductEnrichmentItem.created_at <= end_at)
        items = item_query.order_by(ProductEnrichmentItem.created_at.desc()).limit(max_limit).all()

        run_by_id = {run.id: run for run in runs}
        for item in items:
            run = run_by_id.get(item.run_id)
            metadata = dict(item.metadata_json or {})
            run_metadata = dict(run.metadata_json or {}) if run is not None else {}
            oracle_decision = metadata.get("oracle_decision") or run_metadata.get("oracle_decision") or "pending"
            user_override = bool(metadata.get("user_override")) or item.decision_state == "rejected"
            if item.decision_state == "blocked":
                blocked_count += 1
            if bool(item.is_protected_column):
                protected_count += 1
            item_rows.append(
                {
                    "run_id": item.run_id,
                    "item_id": item.id,
                    "product_id": item.product_id,
                    "field_group": item.field_group,
                    "field_name": item.field_name,
                    "decision_state": item.decision_state,
                    "before_value": item.before_value,
                    "after_value": item.after_value,
                    "confidence": float(item.confidence) if item.confidence is not None else None,
                    "reason_codes": list(item.reason_codes or []),
                    "provenance": item.provenance,
                    "oracle_decision": str(oracle_decision),
                    "requires_user_action": bool(item.requires_user_action),
                    "is_blocked": item.decision_state == "blocked",
                    "is_protected_column": bool(item.is_protected_column),
                    "alt_text_preserved": bool(item.alt_text_preserved),
                    "user_override": user_override,
                    "policy_version": item.policy_version,
                    "mapping_version": item.mapping_version,
                    "run_status": run.status if run is not None else None,
                    "run_profile": run.run_profile if run is not None else None,
                    "target_language": run.target_language if run is not None else None,
                    "run_created_at": _iso(run.created_at) if run is not None else None,
                    "run_updated_at": _iso(run.updated_at) if run is not None else None,
                    "dry_run_expires_at": _iso(run.dry_run_expires_at) if run is not None else None,
                    "created_at": _iso(item.created_at),
                }
            )

    run_rows = [
        {
            "run_id": run.id,
            "status": run.status,
            "run_profile": run.run_profile,
            "target_language": run.target_language,
            "vendor_code": run.vendor_code,
            "policy_version": run.policy_version,
            "mapping_version": run.mapping_version,
            "alt_text_policy": run.alt_text_policy,
            "dry_run_expires_at": _iso(run.dry_run_expires_at),
            "created_at": _iso(run.created_at),
            "updated_at": _iso(run.updated_at),
        }
        for run in runs
    ]

    return {
        "generated_at": _now_iso(),
        "retention_class": "enrichment_lineage",
        "retention_policy": {
            "audit_export_days": 365,
            "trace_days": 14,
        },
        "scope": {
            "store_id": store_id,
            "run_id": run_id,
        },
        "filters": {
            "start_at": _iso(start_at),
            "end_at": _iso(end_at),
            "include_blocked": include_blocked,
            "include_protected": include_protected,
            "limit": max_limit,
        },
        "rows": {
            "runs": run_rows,
            "lineage": item_rows,
        },
        "counts": {
            "run_count": len(run_rows),
            "lineage_count": len(item_rows),
            "blocked_count": blocked_count,
            "protected_count": protected_count,
        },
    }
