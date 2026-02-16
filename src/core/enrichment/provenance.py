"""Field-level provenance helpers for enrichment payload contracts."""
from __future__ import annotations

from typing import Any


def build_provenance(
    *,
    source: str,
    confidence: float | None = None,
    reason_codes: list[str] | None = None,
    evidence_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Create deterministic provenance payload for one enriched field."""
    return {
        "source": source,
        "confidence": confidence,
        "reason_codes": list(reason_codes or []),
        "evidence_refs": list(evidence_refs or []),
    }


def with_provenance(value: Any, provenance: dict[str, Any]) -> dict[str, Any]:
    """Attach provenance metadata to a value."""
    return {
        "value": value,
        "provenance": provenance,
    }

