"""Tier-3 delegation guardrails and worker scope helpers."""
from __future__ import annotations

from typing import Any


MAX_DELEGATION_DEPTH = 2
MAX_DELEGATION_FAN_OUT = 5
DEFAULT_BUDGET = {"max_steps": 20, "max_runtime_seconds": 120}


def validate_delegation_request(
    *,
    depth: int,
    fan_out: int,
    budget: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """Validate delegation constraints and return (allowed, reason)."""
    if depth < 1:
        return False, "Delegation depth must be >= 1."
    if depth > MAX_DELEGATION_DEPTH:
        return False, f"Delegation depth {depth} exceeds max {MAX_DELEGATION_DEPTH}."
    if fan_out < 1:
        return False, "Delegation fan-out must be >= 1."
    if fan_out > MAX_DELEGATION_FAN_OUT:
        return False, f"Delegation fan-out {fan_out} exceeds max {MAX_DELEGATION_FAN_OUT}."
    merged_budget = dict(DEFAULT_BUDGET)
    merged_budget.update(budget or {})
    if int(merged_budget.get("max_steps", 0)) <= 0:
        return False, "Delegation budget max_steps must be > 0."
    if int(merged_budget.get("max_runtime_seconds", 0)) <= 0:
        return False, "Delegation budget max_runtime_seconds must be > 0."
    return True, None


def select_worker_scope(
    *,
    effective_tool_ids: list[str],
    requested_tools: list[str] | None,
    max_tools: int = 6,
) -> tuple[list[str], list[str]]:
    """Return immutable worker tool scope plus blocked requested tools."""
    allowed = set(effective_tool_ids)
    req = [tool for tool in (requested_tools or []) if tool]
    if not req:
        ordered = sorted(allowed)
        return ordered[:max_tools], []
    selected: list[str] = []
    blocked: list[str] = []
    for tool in req:
        if tool in allowed and tool not in selected:
            selected.append(tool)
        elif tool not in allowed:
            blocked.append(tool)
    return selected[:max_tools], blocked

