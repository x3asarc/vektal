"""Resolution policy evaluator honoring locked Phase 8 decisions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from src.models.resolution_rule import ResolutionRule
from src.resolution.contracts import PolicyDecision, RuleContext


def web_source_allowed(*, supplier_verified: bool) -> bool:
    """Web source is eligible only after supplier verification."""
    return supplier_verified


def _is_rule_active(rule: ResolutionRule, now_utc: datetime) -> bool:
    if not rule.enabled:
        return False
    if rule.expires_at is None:
        return True
    expires_at = rule.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > now_utc


def _matches_scope(rule: ResolutionRule, ctx: RuleContext) -> bool:
    supplier_match = rule.supplier_code in ("*", ctx.supplier_code)
    field_match = rule.field_group == ctx.field_group
    return supplier_match and field_match


def evaluate_change_policy(
    *,
    ctx: RuleContext,
    rules: Iterable[ResolutionRule],
) -> PolicyDecision:
    """
    Evaluate one proposed field change.

    Precedence:
    1) exclusion rules (highest)
    2) consented auto-apply rules
    3) default explicit approval
    """
    scoped_rules = [
        rule
        for rule in rules
        if _matches_scope(rule, ctx) and _is_rule_active(rule, ctx.now_utc)
    ]

    for rule in scoped_rules:
        if rule.rule_type == "exclude":
            return PolicyDecision(
                status="blocked_exclusion",
                reason="Blocked by exclusion rule",
                requires_approval=False,
                blocked_by_rule_id=rule.id,
                metadata={"supplier_code": ctx.supplier_code, "field_group": ctx.field_group},
            )

    for rule in scoped_rules:
        if rule.rule_type == "auto_apply" and rule.consented:
            return PolicyDecision(
                status="auto_applied",
                reason="Applied by consented supplier rule",
                requires_approval=False,
                applied_rule_id=rule.id,
                metadata={"supplier_code": ctx.supplier_code, "field_group": ctx.field_group},
            )

    if not ctx.has_consented_rules:
        return PolicyDecision(
            status="awaiting_approval",
            reason="No consented rules available; explicit approval required",
            requires_approval=True,
            metadata={"supplier_code": ctx.supplier_code, "field_group": ctx.field_group},
        )

    return PolicyDecision(
        status="awaiting_approval",
        reason="Change requires explicit approval",
        requires_approval=True,
        metadata={"supplier_code": ctx.supplier_code, "field_group": ctx.field_group},
    )

