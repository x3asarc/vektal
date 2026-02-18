"""Machine-readable apply progress contract for precision operations."""
from __future__ import annotations

from typing import Any

from src.models.recovery_log import RecoveryLog
from src.models.resolution_batch import ResolutionBatch


def build_apply_progress_payload(batch: ResolutionBatch) -> dict[str, Any]:
    total = batch.items.count()
    applied = batch.items.filter_by(status="applied").count()
    failed = batch.items.filter_by(status="failed").count()
    conflicted = batch.items.filter_by(status="structural_conflict").count()
    deferred = (
        RecoveryLog.query.filter_by(
            batch_id=batch.id,
            reason_code="critical_apply_failure",
        ).count()
    )
    processed = min(total, applied + failed + conflicted)
    retryable = deferred

    metadata = dict(batch.metadata_json or {})
    current_item_id = metadata.get("current_item_id")
    current_item_label = metadata.get("current_item_label")
    eta_seconds = metadata.get("eta_seconds")

    terminal_summary = metadata.get("terminal_summary") or {
        "success": applied,
        "failed": max(0, failed - deferred),
        "deferred": deferred,
        "retryable": retryable,
    }

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "processed": processed,
        "total": total,
        "eta_seconds": eta_seconds if eta_seconds is not None else (0 if batch.status in {"applied", "applied_with_conflicts", "failed", "cancelled"} else None),
        "current_item": {
            "id": current_item_id,
            "label": current_item_label,
        },
        "terminal_summary": terminal_summary,
    }
