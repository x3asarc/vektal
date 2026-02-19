"""Content oracle adapter for enrichment second-opinion arbitration."""
from __future__ import annotations

from src.core.enrichment.oracle_contract import OracleDecision, merchant_first_arbitration


def evaluate_content_oracle(
    *,
    merchant_value,
    candidate_value,
    confidence: float,
    structural_conflict: bool = False,
    evidence_refs: list[str] | None = None,
) -> OracleDecision:
    base = merchant_first_arbitration(
        merchant_value=merchant_value,
        candidate_value=candidate_value,
        confidence=confidence,
        structural_conflict=structural_conflict,
        reason_code_prefix="content",
    )
    reason_codes = list(base.reason_codes)
    if confidence < 0.7 and "content_low_confidence" not in reason_codes:
        reason_codes.append("content_low_confidence")
    if structural_conflict and "content_structural_conflict" not in reason_codes:
        reason_codes.append("content_structural_conflict")
    return OracleDecision(
        decision=base.decision,
        confidence=base.confidence,
        reason_codes=tuple(reason_codes),
        evidence_refs=tuple(evidence_refs or ()),
        requires_user_action=base.requires_user_action,
        source='enrichment',
    )

