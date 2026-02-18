"""Tool projection service for tier and tenant capability filtering."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.models import (
    AssistantProfile,
    AssistantTenantToolPolicy,
    AssistantToolRegistry,
    User,
)


@dataclass(frozen=True)
class ToolView:
    tool_id: str
    risk_class: str
    mutates_data: bool
    requires_integration: str | None
    required_role: str | None


_DEFAULT_TOOLS: list[dict[str, Any]] = [
    {
        "tool_id": "chat.respond",
        "display_name": "Respond",
        "risk_class": "low",
        "mutates_data": False,
        "requires_integration": None,
        "allowed_tiers": ["tier_1", "tier_2", "tier_3"],
        "required_role": None,
        "enabled": True,
    },
    {
        "tool_id": "products.read",
        "display_name": "Read Products",
        "risk_class": "low",
        "mutates_data": False,
        "requires_integration": "shopify",
        "allowed_tiers": ["tier_1", "tier_2", "tier_3"],
        "required_role": None,
        "enabled": True,
    },
    {
        "tool_id": "products.search",
        "display_name": "Search Products",
        "risk_class": "low",
        "mutates_data": False,
        "requires_integration": "shopify",
        "allowed_tiers": ["tier_1", "tier_2", "tier_3"],
        "required_role": None,
        "enabled": True,
    },
    {
        "tool_id": "resolution.dry_run",
        "display_name": "Compile Dry Run",
        "risk_class": "medium",
        "mutates_data": False,
        "requires_integration": "shopify",
        "allowed_tiers": ["tier_2", "tier_3"],
        "required_role": "member",
        "enabled": True,
    },
    {
        "tool_id": "resolution.apply",
        "display_name": "Apply Approved Dry Run",
        "risk_class": "high",
        "mutates_data": True,
        "requires_integration": "shopify",
        "allowed_tiers": ["tier_2", "tier_3"],
        "required_role": "manager",
        "enabled": True,
    },
    {
        "tool_id": "agent.spawn_sub_agent",
        "display_name": "Spawn Sub-Agent",
        "risk_class": "medium",
        "mutates_data": False,
        "requires_integration": None,
        "allowed_tiers": ["tier_3"],
        "required_role": "manager",
        "enabled": True,
    },
]


def _tier_value(user: User) -> str:
    tier = getattr(getattr(user, "tier", None), "value", None) or str(getattr(user, "tier", "tier_1"))
    return str(tier).lower()


def _normalize_allowed_tiers(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).lower() for item in raw if item]
    if isinstance(raw, str) and raw.strip():
        return [part.strip().lower() for part in raw.split(",") if part.strip()]
    return ["tier_1", "tier_2", "tier_3"]


def _resolve_enabled_skill_set(*, user_id: int, store_id: int | None) -> set[str] | None:
    user_profile = (
        AssistantProfile.query.filter_by(user_id=user_id, profile_scope="user", is_active=True)
        .order_by(AssistantProfile.priority.desc(), AssistantProfile.updated_at.desc())
        .first()
    )
    if user_profile and isinstance(user_profile.enabled_skill_set, list) and user_profile.enabled_skill_set:
        return {str(item) for item in user_profile.enabled_skill_set if item}

    if store_id is None:
        return None

    team_profile = (
        AssistantProfile.query.filter_by(store_id=store_id, profile_scope="team", is_active=True)
        .order_by(AssistantProfile.priority.desc(), AssistantProfile.updated_at.desc())
        .first()
    )
    if team_profile and isinstance(team_profile.enabled_skill_set, list) and team_profile.enabled_skill_set:
        return {str(item) for item in team_profile.enabled_skill_set if item}
    return None


def _load_registry() -> list[dict[str, Any]]:
    rows = AssistantToolRegistry.query.filter_by(enabled=True).order_by(AssistantToolRegistry.tool_id.asc()).all()
    if not rows:
        return list(_DEFAULT_TOOLS)
    payloads: list[dict[str, Any]] = []
    for row in rows:
        payloads.append(
            {
                "tool_id": row.tool_id,
                "display_name": row.display_name,
                "risk_class": row.risk_class,
                "mutates_data": bool(row.mutates_data),
                "requires_integration": row.requires_integration,
                "allowed_tiers": _normalize_allowed_tiers(row.allowed_tiers),
                "required_role": row.required_role,
                "enabled": bool(row.enabled),
            }
        )
    return payloads


def project_effective_toolset(
    *,
    user: User,
    store_id: int | None,
    rbac_role: str = "member",
    active_integrations: dict[str, bool] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Return effective toolset and projection notes for this user request.

    Policy order:
    1) tier allowlist
    2) profile enabled skill set
    3) integration readiness
    4) tenant allow/deny policy (deny precedence)
    """
    tier = _tier_value(user)
    integrations = dict(active_integrations or {})
    enabled_skill_set = _resolve_enabled_skill_set(user_id=user.id, store_id=store_id)
    notes: list[str] = []

    deny_tools: set[str] = set()
    allow_tools: set[str] = set()
    if store_id is not None:
        policies = AssistantTenantToolPolicy.query.filter_by(store_id=store_id, is_active=True).all()
        for policy in policies:
            if policy.role_scope and policy.role_scope not in {"*", rbac_role}:
                continue
            if policy.policy_action == "deny":
                deny_tools.add(policy.tool_id)
            elif policy.policy_action == "allow":
                allow_tools.add(policy.tool_id)

    output: list[dict[str, Any]] = []
    for tool in _load_registry():
        tool_id = str(tool["tool_id"])
        if tier not in _normalize_allowed_tiers(tool.get("allowed_tiers")):
            continue

        if enabled_skill_set is not None and tool_id not in enabled_skill_set:
            notes.append(f"{tool_id}: disabled by profile enabled-skill set")
            continue

        required_integration = tool.get("requires_integration")
        if required_integration and not bool(integrations.get(str(required_integration), False)):
            notes.append(f"{tool_id}: hidden because integration '{required_integration}' is not active")
            continue

        required_role = tool.get("required_role")
        if required_role and rbac_role not in {required_role, "admin"}:
            notes.append(f"{tool_id}: hidden because role '{rbac_role}' lacks '{required_role}'")
            continue

        if tool_id in deny_tools:
            notes.append(f"{tool_id}: denied by tenant tool policy")
            continue
        if allow_tools and tool_id not in allow_tools:
            notes.append(f"{tool_id}: excluded by tenant allowlist policy")
            continue

        output.append(
            {
                "tool_id": tool_id,
                "risk_class": str(tool.get("risk_class") or "low"),
                "mutates_data": bool(tool.get("mutates_data", False)),
                "requires_integration": required_integration,
                "required_role": required_role,
            }
        )

    output.sort(key=lambda item: item["tool_id"])
    return output, notes

