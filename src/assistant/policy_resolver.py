"""Deterministic tier routing and explainability contract resolver."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from src.assistant.tool_projection import project_effective_toolset
from src.models import User

_WORD_RE = re.compile(r"[a-z0-9_-]+", re.IGNORECASE)
_MUTATION_KEYWORDS = {
    "add",
    "create",
    "update",
    "change",
    "set",
    "replace",
    "import",
    "publish",
    "price",
    "inventory",
    "variant",
}


def _hash_payload(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _classify(content: str) -> tuple[str, float, str]:
    text = (content or "").strip().lower()
    if not text:
        return "unknown", 0.0, "heuristic"
    if text in {"help", "?", "commands"}:
        return "help", 0.98, "heuristic"
    words = set(_WORD_RE.findall(text))
    if words & _MUTATION_KEYWORDS:
        return "mutating_request", 0.84, "heuristic"
    if len(words) <= 1 and len(text) <= 8:
        return "lookup_request", 0.55, "heuristic"
    return "read_request", 0.72, "heuristic"


def _tier_value(user: User) -> str:
    return str(getattr(getattr(user, "tier", None), "value", "tier_1")).lower()


def _base_route_for_intent(*, tier: str, intent_type: str, confidence: float) -> tuple[str, str, str | None]:
    if confidence < 0.60:
        return "tier_1", "none", "safe_tier_fallback"
    if intent_type == "mutating_request":
        if tier == "tier_3":
            return "tier_3", "product_scope_required_before_apply", None
        if tier == "tier_2":
            return "tier_2", "product_scope_required_before_apply", None
        return "tier_1", "blocked_write", "tier_upgrade_required"
    if tier == "tier_3":
        return "tier_2", "none", None
    return "tier_1", "none", None


def resolve_route_decision(
    *,
    user: User,
    content: str,
    store_id: int | None,
    session_id: int | None = None,
    rbac_role: str = "member",
    active_integrations: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Resolve deterministic route decision and effective toolset for one request."""
    tier = _tier_value(user)
    intent_type, confidence, classifier_method = _classify(content)
    route_decision, approval_mode, fallback_stage = _base_route_for_intent(
        tier=tier,
        intent_type=intent_type,
        confidence=confidence,
    )
    integrations = dict(active_integrations or {})
    effective_toolset, projection_notes = project_effective_toolset(
        user=user,
        store_id=store_id,
        rbac_role=rbac_role,
        active_integrations=integrations,
    )
    reasons = [
        f"tier={tier}",
        f"intent={intent_type}",
        f"confidence={confidence:.2f}",
    ]
    reasons.extend(projection_notes)
    if fallback_stage:
        reasons.append(f"fallback_stage={fallback_stage}")

    suggested_escalation: str | None = None
    if fallback_stage == "safe_tier_fallback" and tier in {"tier_2", "tier_3"}:
        suggested_escalation = "tier_2" if tier == "tier_2" else "tier_3"
    elif fallback_stage == "tier_upgrade_required":
        suggested_escalation = "tier_2"

    policy_snapshot = {
        "user_id": user.id,
        "store_id": store_id,
        "session_id": session_id,
        "tier": tier,
        "intent_type": intent_type,
        "approval_mode": approval_mode,
        "route_decision": route_decision,
        "rbac_role": rbac_role,
        "integrations": integrations,
    }
    tool_ids = [item["tool_id"] for item in effective_toolset]

    return {
        "route_decision": route_decision,
        "confidence": confidence,
        "intent_type": intent_type,
        "classifier_method": classifier_method,
        "approval_mode": approval_mode,
        "fallback_stage": fallback_stage,
        "suggested_escalation": suggested_escalation,
        "effective_toolset": effective_toolset,
        "reasons": reasons,
        "policy_snapshot_hash": _hash_payload(policy_snapshot),
        "effective_toolset_hash": _hash_payload(tool_ids),
        "explainability_payload": {
            "summary": f"Routed to {route_decision} for intent {intent_type}.",
            "notes": reasons,
        },
    }

