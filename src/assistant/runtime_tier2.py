"""Tier-2 runtime helpers."""
from __future__ import annotations

from typing import Any


def build_tier2_payload(*, route_summary: dict[str, Any], mutating: bool) -> dict[str, Any]:
    """Return governed runtime payload for Tier-2 execution."""
    return {
        "mode": "governed_skill_runtime",
        "mutating": bool(mutating),
        "requires_dry_run": bool(mutating),
        "requires_product_approval": bool(mutating),
        "route_decision": route_summary.get("route_decision"),
        "approval_mode": route_summary.get("approval_mode"),
    }

