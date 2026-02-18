"""Audit export helpers for resolution batches."""
from __future__ import annotations

import csv
import io
import json
from typing import Any

from src.models.resolution_batch import ResolutionBatch
from src.models.resolution_snapshot import ResolutionSnapshot


def _row_to_export_dict(batch_id: int, item, change) -> dict[str, Any]:
    return {
        "batch_id": batch_id,
        "item_id": item.id,
        "product_label": item.product_label,
        "item_status": item.status,
        "field_group": change.field_group,
        "field_name": change.field_name,
        "before_value": change.before_value,
        "after_value": change.after_value,
        "change_status": change.status,
        "reason_sentence": change.reason_sentence,
        "confidence_score": float(change.confidence_score) if change.confidence_score is not None else None,
        "applied_rule_id": change.applied_rule_id,
        "blocked_by_rule_id": change.blocked_by_rule_id,
        "approved_by_user_id": change.approved_by_user_id,
        "changed_at": change.updated_at.isoformat() if change.updated_at else None,
    }


def build_audit_payload(batch: ResolutionBatch) -> dict[str, Any]:
    manifest = (
        ResolutionSnapshot.query.filter_by(batch_id=batch.id, snapshot_type="batch_manifest")
        .order_by(ResolutionSnapshot.created_at.desc())
        .first()
    )
    rows: list[dict[str, Any]] = []
    for item in batch.items.order_by("id").all():
        for change in item.changes.order_by("id").all():
            rows.append(_row_to_export_dict(batch.id, item, change))

    return {
        "batch": {
            "id": batch.id,
            "status": batch.status,
            "apply_mode": batch.apply_mode,
            "store_id": batch.store_id,
            "user_id": batch.user_id,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "applied_at": batch.applied_at.isoformat() if batch.applied_at else None,
        },
        "manifest": manifest.payload if manifest else {},
        "rows": rows,
    }


def render_audit_export(batch: ResolutionBatch, *, fmt: str) -> tuple[str, str]:
    payload = build_audit_payload(batch)
    if fmt == "json":
        return json.dumps(payload, default=str), "application/json"

    if fmt == "csv":
        output = io.StringIO()
        fieldnames = [
            "batch_id",
            "item_id",
            "product_label",
            "item_status",
            "field_group",
            "field_name",
            "before_value",
            "after_value",
            "change_status",
            "reason_sentence",
            "confidence_score",
            "applied_rule_id",
            "blocked_by_rule_id",
            "approved_by_user_id",
            "changed_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row in payload["rows"]:
            writer.writerow(row)
        return output.getvalue(), "text/csv"

    raise ValueError(f"Unsupported export format: {fmt}")
