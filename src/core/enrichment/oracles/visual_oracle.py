"""Visual oracle adapter for text-vs-image consistency checks."""
from __future__ import annotations

from src.core.enrichment.oracle_contract import OracleDecision


_COLOR_HINTS = {
    "red": "ff",
    "rot": "ff",
    "blue": "00",
    "blau": "00",
    "green": "00",
    "grun": "00",
    "grün": "00",
}


def evaluate_visual_oracle(
    *,
    text_color: str | None,
    visual_hex: str | None,
    confidence: float,
    evidence_refs: list[str] | None = None,
) -> OracleDecision:
    normalized_hex = (visual_hex or "").strip().lower().lstrip("#")
    normalized_text = (text_color or "").strip().lower()
    reasons: list[str] = []

    if not normalized_hex:
        return OracleDecision(
            decision="hold",
            confidence=float(confidence),
            reason_codes=("visual_hex_missing",),
            evidence_refs=tuple(evidence_refs or ()),
            requires_user_action=True,
            source='enrichment',
        )

    expected_prefix = _COLOR_HINTS.get(normalized_text)
    if expected_prefix and not normalized_hex.startswith(expected_prefix):
        reasons.extend(["visual_text_conflict", "visual_second_opinion_required"])
        return OracleDecision(
            decision="hold",
            confidence=float(confidence),
            reason_codes=tuple(reasons),
            evidence_refs=tuple(evidence_refs or ()),
            requires_user_action=True,
            source='enrichment',
        )

    decision = "pass" if confidence >= 0.7 else "review"
    reasons.append("visual_consistent")
    if confidence < 0.7:
        reasons.append("visual_low_confidence")
    return OracleDecision(
        decision=decision,
        confidence=float(confidence),
        reason_codes=tuple(reasons),
        evidence_refs=tuple(evidence_refs or ()),
        requires_user_action=decision != "pass",
        source='enrichment',
    )

