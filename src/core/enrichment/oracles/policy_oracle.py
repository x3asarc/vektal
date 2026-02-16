"""Policy oracle adapter for threshold and immutable-field adjudication."""
from __future__ import annotations

from src.core.enrichment.oracle_contract import OracleDecision


def _price_change_percent(before_value, after_value) -> float:
    try:
        before = float(before_value)
        after = float(after_value)
    except (TypeError, ValueError):
        return 0.0
    if before == 0:
        return 100.0 if after != 0 else 0.0
    return abs((after - before) / before) * 100.0


def evaluate_policy_oracle(
    *,
    field_name: str,
    before_value,
    after_value,
    immutable_fields: list[str] | None = None,
    hitl_thresholds: dict | None = None,
) -> OracleDecision:
    immutable = set(immutable_fields or [])
    thresholds = hitl_thresholds or {}
    if field_name in immutable:
        return OracleDecision(
            decision="reject",
            confidence=1.0,
            reason_codes=("policy_immutable_field",),
            evidence_refs=(),
            requires_user_action=True,
        )

    if field_name == "price":
        threshold = float(thresholds.get("price_change_percent", 15.0))
        delta = _price_change_percent(before_value, after_value)
        if delta > threshold:
            return OracleDecision(
                decision="hold",
                confidence=0.95,
                reason_codes=("policy_threshold_hit", "policy_price_hitl_required"),
                evidence_refs=(),
                requires_user_action=True,
            )

    return OracleDecision(
        decision="accept",
        confidence=1.0,
        reason_codes=("policy_pass",),
        evidence_refs=(),
        requires_user_action=False,
    )

