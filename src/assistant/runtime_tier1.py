"""Tier-1 runtime helpers."""
from __future__ import annotations

from typing import Any


def build_tier1_payload(*, route_summary: dict[str, Any]) -> dict[str, Any]:
    """Return read-safe runtime payload for Tier-1 responses."""
    return {
        "mode": "read_safe",
        "route_decision": route_summary.get("route_decision"),
        "fallback_stage": route_summary.get("fallback_stage"),
        "approval_mode": route_summary.get("approval_mode", "none"),
        "message": "Tier 1 read-safe mode active.",
    }

