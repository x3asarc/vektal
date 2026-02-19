"""
Canonical Oracle decision contract for all adapters (enrichment + governance).

This is the unified contract used by:
- Enrichment oracles: content_oracle, visual_oracle, policy_oracle
- Governance oracles: graph_oracle_adapter

Decision type harmonization (Phase 13.2-06):
- pass: Clear automatic approval (was 'accept')
- review: Requires human review but not blocking (was 'suggest')
- hold: Pending more information (unchanged)
- fail: Clear rejection/blocking (was 'reject')
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OracleDecisionType = Literal["pass", "review", "hold", "fail"]

_GENERIC_MERCHANT_VALUES = {"", "n/a", "na", "none", "see title", "same as title"}


@dataclass(frozen=True)
class OracleDecision:
    """Unified Oracle output payload across content/visual/policy/graph adapters."""

    decision: OracleDecisionType
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    requires_user_action: bool
    source: str = 'enrichment'  # Track origin: 'enrichment' | 'graph' | etc

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "requires_user_action": self.requires_user_action,
            "source": self.source,
        }


def merchant_value_is_meaningful(value) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    if not text:
        return False
    return text not in _GENERIC_MERCHANT_VALUES


def normalize_legacy_decision(decision: str) -> str:
    """
    Normalize legacy decision vocabulary to unified contract.

    Backward-compatibility helper for external callers using old decision types.

    Mapping:
    - accept -> pass
    - suggest -> review
    - reject -> fail
    - pass/review/hold/fail -> unchanged
    """
    legacy_map = {
        "accept": "pass",
        "suggest": "review",
        "reject": "fail",
    }
    return legacy_map.get(decision, decision)


def merchant_first_arbitration(
    *,
    merchant_value,
    candidate_value,
    confidence: float,
    structural_conflict: bool = False,
    reason_code_prefix: str = "content",
) -> OracleDecision:
    """
    Apply merchant-first policy to enrichment candidate updates.

    Uses unified decision vocabulary: pass | review | hold | fail
    """
    if candidate_value is None:
        return OracleDecision(
            decision="hold",
            confidence=float(confidence),
            reason_codes=(f"{reason_code_prefix}_candidate_missing",),
            evidence_refs=(),
            requires_user_action=True,
        )

    if not merchant_value_is_meaningful(merchant_value):
        if confidence >= 0.7 and not structural_conflict:
            return OracleDecision(
                decision="pass",
                confidence=float(confidence),
                reason_codes=(f"{reason_code_prefix}_merchant_missing",),
                evidence_refs=(),
                requires_user_action=False,
            )
        return OracleDecision(
            decision="hold",
            confidence=float(confidence),
            reason_codes=(f"{reason_code_prefix}_merchant_missing_low_confidence",),
            evidence_refs=(),
            requires_user_action=True,
        )

    merchant_text = str(merchant_value).strip()
    candidate_text = str(candidate_value).strip()
    if merchant_text == candidate_text and confidence >= 0.7:
        return OracleDecision(
            decision="pass",
            confidence=float(confidence),
            reason_codes=(f"{reason_code_prefix}_matches_merchant",),
            evidence_refs=(),
            requires_user_action=False,
        )

    if structural_conflict or confidence < 0.7:
        return OracleDecision(
            decision="hold",
            confidence=float(confidence),
            reason_codes=(f"{reason_code_prefix}_conflict_or_low_confidence",),
            evidence_refs=(),
            requires_user_action=True,
        )

    return OracleDecision(
        decision="review",
        confidence=float(confidence),
        reason_codes=(f"{reason_code_prefix}_merchant_conflict_suggest",),
        evidence_refs=(),
        requires_user_action=True,
    )

