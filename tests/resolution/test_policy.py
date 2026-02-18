"""Policy evaluator tests for Phase 8 rule precedence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.models.resolution_rule import ResolutionRule
from src.resolution.contracts import RuleContext
from src.resolution.policy import evaluate_change_policy, web_source_allowed


def _ctx(**kwargs):
    base = dict(
        supplier_code="PENTART",
        field_group="pricing",
        now_utc=datetime.now(timezone.utc),
        has_consented_rules=True,
        user_id=1,
    )
    base.update(kwargs)
    return RuleContext(**base)


def test_exclusion_rule_precedence_over_auto_apply():
    now = datetime.now(timezone.utc)
    rules = [
        ResolutionRule(
            id=11,
            user_id=1,
            supplier_code="PENTART",
            field_group="pricing",
            rule_type="auto_apply",
            consented=True,
            enabled=True,
            action="auto_apply",
            expires_at=now + timedelta(days=1),
        ),
        ResolutionRule(
            id=22,
            user_id=1,
            supplier_code="PENTART",
            field_group="pricing",
            rule_type="exclude",
            consented=True,
            enabled=True,
            action="exclude",
            expires_at=now + timedelta(days=1),
        ),
    ]
    decision = evaluate_change_policy(ctx=_ctx(now_utc=now), rules=rules)
    assert decision.status == "blocked_exclusion"
    assert decision.blocked_by_rule_id == 22


def test_no_consented_rules_requires_explicit_approval():
    now = datetime.now(timezone.utc)
    decision = evaluate_change_policy(
        ctx=_ctx(now_utc=now, has_consented_rules=False),
        rules=[],
    )
    assert decision.status == "awaiting_approval"
    assert decision.requires_approval is True
    assert "explicit approval" in decision.reason.lower()


def test_web_source_requires_supplier_verification():
    assert web_source_allowed(supplier_verified=True) is True
    assert web_source_allowed(supplier_verified=False) is False

