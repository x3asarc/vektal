"""Deterministic Oracle decision contract for enrichment arbitration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


OracleDecisionType = Literal["accept", "suggest", "hold", "reject"]

_GENERIC_MERCHANT_VALUES = {"", "n/a", "na", "none", "see title", "same as title"}


@dataclass(frozen=True)
class OracleDecision:
    """Unified Oracle output payload across content/visual/policy adapters."""

    decision: OracleDecisionType
    confidence: float
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    requires_user_action: bool

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "evidence_refs": list(self.evidence_refs),
            "requires_user_action": self.requires_user_action,
        }


def merchant_value_is_meaningful(value) -> bool:
    if value is None:
        return False
    text = str(value).strip().lower()
    if not text:
        return False
    return text not in _GENERIC_MERCHANT_VALUES


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
                decision="accept",
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
            decision="accept",
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
        decision="suggest",
        confidence=float(confidence),
        reason_codes=(f"{reason_code_prefix}_merchant_conflict_suggest",),
        evidence_refs=(),
        requires_user_action=True,
    )

