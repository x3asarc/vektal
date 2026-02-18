"""Tier-3 runtime helpers."""
from __future__ import annotations

from typing import Any


def build_tier3_payload(*, route_summary: dict[str, Any]) -> dict[str, Any]:
    """Return orchestration payload metadata for Tier-3 manager runtime."""
    return {
        "mode": "manager_worker_orchestration",
        "route_decision": route_summary.get("route_decision"),
        "delegation_allowed": route_summary.get("route_decision") == "tier_3",
        "fallback_stage": route_summary.get("fallback_stage"),
    }


def build_trace_summary(*, delegation_events: list[dict[str, Any]]) -> dict[str, Any]:
    """Build compact progressive-disclosure summary for delegated flows."""
    return {
        "delegation_count": len(delegation_events),
        "events": delegation_events,
    }

