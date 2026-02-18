"""Dry-run compilation and persistence for Phase 8 resolution."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from src.models import db
from src.models.resolution_batch import ResolutionBatch, ResolutionChange, ResolutionItem
from src.models.resolution_rule import ResolutionRule
from src.resolution.adapters import (
    search_shopify_candidates,
    search_supplier_candidates,
    search_web_candidates,
)
from src.resolution.contracts import Candidate, RuleContext
from src.resolution.normalize import normalize_input_row
from src.resolution.policy import evaluate_change_policy, web_source_allowed
from src.resolution.scoring import score_candidate
from src.resolution.snapshot_lifecycle import capture_snapshot, ensure_store_baseline, stamp_batch_ttl
from src.resolution.structural import detect_structural_conflict


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _field_group(field_name: str) -> str:
    if field_name in {"image_url", "images"}:
        return "images"
    if field_name in {"price", "compare_at_price", "cost"}:
        return "pricing"
    if field_name in {"sku", "barcode", "ean"}:
        return "ids"
    return "text"


def _candidate_value(candidate: Candidate | None, field_name: str):
    if candidate is None:
        return None
    payload = candidate.payload or {}
    if field_name == "description":
        return payload.get("description")
    if field_name == "image_url":
        return payload.get("image_url")
    return getattr(candidate, field_name, None)


def _is_rule_active(rule: ResolutionRule, now_utc: datetime) -> bool:
    if not rule.enabled:
        return False
    if rule.expires_at is None:
        return True
    expires_at = rule.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > now_utc


def _resolve_source_candidates(
    *,
    user_id: int,
    query,
) -> tuple[str | None, list[Candidate], Candidate | None, Candidate | None]:
    shopify_candidates = [score_candidate(query, row, source_rank=idx) for idx, row in enumerate(search_shopify_candidates(query))]
    supplier_candidates = [
        score_candidate(query, row, source_rank=idx)
        for idx, row in enumerate(search_supplier_candidates(query, user_id=user_id))
    ]
    web_candidates: list[Candidate] = []
    if not shopify_candidates and not supplier_candidates and web_source_allowed(supplier_verified=query.supplier_verified):
        web_candidates = [
            score_candidate(query, row, source_rank=idx)
            for idx, row in enumerate(search_web_candidates(query))
        ]

    selected_source = None
    selected = []
    if shopify_candidates:
        selected_source = "shopify"
        selected = sorted(shopify_candidates, key=lambda row: row.confidence_score or 0.0, reverse=True)
    elif supplier_candidates:
        selected_source = "supplier"
        selected = sorted(supplier_candidates, key=lambda row: row.confidence_score or 0.0, reverse=True)
    elif web_candidates:
        selected_source = "web"
        selected = sorted(web_candidates, key=lambda row: row.confidence_score or 0.0, reverse=True)

    top_shopify = shopify_candidates[0] if shopify_candidates else None
    top_supplier = supplier_candidates[0] if supplier_candidates else None
    return selected_source, selected[:3], top_shopify, top_supplier


def _change_status_from_policy(decision_status: str) -> str:
    if decision_status == "blocked_exclusion":
        return "blocked_exclusion"
    if decision_status == "auto_applied":
        return "auto_applied"
    return "awaiting_approval"


def _build_changes_for_row(
    *,
    item: ResolutionItem,
    supplier_code: str,
    selected_candidate: Candidate | None,
    row: dict[str, Any],
    rules: list[ResolutionRule],
    now_utc: datetime,
) -> list[ResolutionChange]:
    changes: list[ResolutionChange] = []
    candidate_factors = (selected_candidate.reason_factors or {}) if selected_candidate else {}
    candidate_badge = selected_candidate.confidence_badge if selected_candidate else None

    for field_name in ("title", "description", "price", "sku", "barcode", "image_url"):
        after_value = row.get(field_name)
        if after_value in (None, ""):
            continue
        before_value = _candidate_value(selected_candidate, field_name)
        if before_value == after_value:
            continue

        field_group = _field_group(field_name)
        group_rules = [rule for rule in rules if _is_rule_active(rule, now_utc)]
        has_consented_rules = any(
            rule.rule_type == "auto_apply"
            and rule.consented
            and rule.field_group == field_group
            for rule in group_rules
        )

        decision = evaluate_change_policy(
            ctx=RuleContext(
                supplier_code=supplier_code,
                field_group=field_group,
                now_utc=now_utc,
                has_consented_rules=has_consented_rules,
                user_id=item.batch.user_id,
            ),
            rules=group_rules,
        )

        reasons = []
        if selected_candidate and selected_candidate.reason_sentence:
            reasons.append(selected_candidate.reason_sentence.rstrip("."))
        reasons.append(f"{field_name} changed from current value")

        reason_factors = {
            **candidate_factors,
            "confidence_badge": candidate_badge,
            "policy_status": decision.status,
        }
        change = ResolutionChange(
            item_id=item.id,
            field_group=field_group,
            field_name=field_name,
            before_value=before_value,
            after_value=after_value,
            reason_sentence=". ".join(reasons) + ".",
            reason_factors=reason_factors,
            confidence_score=_as_float(selected_candidate.confidence_score) if selected_candidate else None,
            status=_change_status_from_policy(decision.status),
            applied_rule_id=decision.applied_rule_id,
            blocked_by_rule_id=decision.blocked_by_rule_id,
        )
        changes.append(change)
    return changes


def compile_dry_run(
    *,
    user_id: int,
    store_id: int,
    supplier_code: str,
    supplier_verified: bool,
    rows: list[dict[str, Any]],
    apply_mode: str = "immediate",
    scheduled_for: datetime | None = None,
) -> ResolutionBatch:
    """Compile and persist one product-grouped dry-run batch."""
    if not rows:
        raise ValueError("At least one input row is required.")

    now_utc = datetime.now(timezone.utc)
    rules = ResolutionRule.query.filter(
        ResolutionRule.user_id == user_id,
        ResolutionRule.supplier_code.in_([supplier_code, "*"]),
    ).all()

    batch = ResolutionBatch(
        user_id=user_id,
        store_id=store_id,
        status="ready_for_review",
        apply_mode=apply_mode,
        scheduled_for=scheduled_for,
        created_by_user_id=user_id,
        metadata_json={"supplier_code": supplier_code, "supplier_verified": supplier_verified},
    )
    db.session.add(batch)
    db.session.flush()
    expires_at = stamp_batch_ttl(batch)
    baseline_snapshot, baseline_created = ensure_store_baseline(batch=batch)
    batch.metadata_json = {
        **(batch.metadata_json or {}),
        "baseline_snapshot_id": baseline_snapshot.id,
        "baseline_created_for_batch": baseline_created,
        "expires_at": expires_at.isoformat(),
    }

    summary = {
        "rows_total": len(rows),
        "items_structural_conflict": 0,
        "items_ready": 0,
        "source_counts": {"shopify": 0, "supplier": 0, "web": 0, "none": 0},
    }

    for row in rows:
        query = normalize_input_row(
            row=row,
            store_id=store_id,
            supplier_code=supplier_code,
            supplier_verified=supplier_verified,
        )
        selected_source, selected_candidates, shopify_candidate, supplier_candidate = _resolve_source_candidates(
            user_id=user_id,
            query=query,
        )
        summary["source_counts"][selected_source or "none"] += 1
        selected_candidate = selected_candidates[0] if selected_candidates else None

        conflict = detect_structural_conflict(
            shopify_candidate=shopify_candidate,
            supplier_candidate=supplier_candidate,
            input_row=row,
        )
        item_status = "awaiting_approval"
        structural_state = None
        conflict_reason = None
        if conflict is not None:
            item_status = "structural_conflict"
            structural_state = conflict.conflict_type.value
            conflict_reason = conflict.detail
            summary["items_structural_conflict"] += 1
        else:
            summary["items_ready"] += 1

        item = ResolutionItem(
            batch_id=batch.id,
            product_id=shopify_candidate.product_id if shopify_candidate else None,
            shopify_product_id=shopify_candidate.shopify_product_id if shopify_candidate else None,
            supplier_code=supplier_code,
            status=item_status,
            structural_state=structural_state,
            conflict_reason=conflict_reason,
            product_label=(selected_candidate.title if selected_candidate else row.get("title")),
        )
        db.session.add(item)
        db.session.flush()

        capture_snapshot(
            batch_id=batch.id,
            item_id=item.id,
            snapshot_type="product_pre_change",
            payload={
                "shopify_candidate": shopify_candidate.payload if shopify_candidate else None,
                "selected_candidate": selected_candidate.payload if selected_candidate else None,
                "input_row": row,
                "source_used": selected_source,
            },
            allow_dedupe=False,
        )

        changes = _build_changes_for_row(
            item=item,
            supplier_code=supplier_code,
            selected_candidate=selected_candidate,
            row=row,
            rules=rules,
            now_utc=now_utc,
        )
        if not changes and item.status != "structural_conflict":
            item.status = "ready"
        for change in changes:
            if conflict is not None:
                change.status = "structural_conflict"
            db.session.add(change)

    capture_snapshot(
        batch_id=batch.id,
        item_id=None,
        snapshot_type="batch_manifest",
        payload=summary,
        allow_dedupe=True,
    )
    db.session.commit()
    return batch
