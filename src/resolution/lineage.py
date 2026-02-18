"""Lineage helpers for explainability drill-down endpoints."""
from __future__ import annotations

from src.models.resolution_batch import ResolutionBatch


def build_batch_lineage(batch: ResolutionBatch) -> list[dict]:
    """Materialize change lineage rows for API responses."""
    lineage: list[dict] = []
    for item in batch.items.order_by("id").all():
        for change in item.changes.order_by("id").all():
            reason_factors = change.reason_factors or {}
            lineage.append(
                {
                    "batch_id": batch.id,
                    "item_id": item.id,
                    "change_id": change.id,
                    "field_name": change.field_name,
                    "status": change.status,
                    "reason_sentence": change.reason_sentence,
                    "confidence_score": float(change.confidence_score) if change.confidence_score is not None else None,
                    "confidence_badge": reason_factors.get("confidence_badge"),
                    "reason_factors": reason_factors,
                    "applied_rule_id": change.applied_rule_id,
                    "blocked_by_rule_id": change.blocked_by_rule_id,
                    "approved_by_user_id": change.approved_by_user_id,
                    "updated_at": change.updated_at.isoformat() if change.updated_at else None,
                }
            )
    return lineage
