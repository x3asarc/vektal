"""Deterministic confidence scoring for resolution candidates."""
from __future__ import annotations

from dataclasses import replace

from src.resolution.contracts import Candidate, NormalizedQuery
from src.resolution.normalize import tokenize_title


_SOURCE_TRUST = {
    "shopify": 0.15,
    "supplier": 0.10,
    "web": 0.05,
}


def _badge(score: float) -> str:
    if score >= 0.80:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


def _title_overlap(left: str | None, right: str | None) -> float:
    left_tokens = set(tokenize_title(left))
    right_tokens = set(tokenize_title(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def score_candidate(query: NormalizedQuery, candidate: Candidate, *, source_rank: int = 0) -> Candidate:
    """Attach confidence + explainability metadata to one candidate."""
    sku_match = bool(query.sku and candidate.sku and query.sku == candidate.sku)
    barcode_match = bool(query.barcode and candidate.barcode and query.barcode == candidate.barcode)
    title_similarity = _title_overlap(query.title, candidate.title)
    source_trust = _SOURCE_TRUST.get(candidate.source, 0.0)

    raw_score = 0.0
    raw_score += 0.45 if sku_match else 0.0
    raw_score += 0.35 if barcode_match else 0.0
    raw_score += min(0.20, title_similarity * 0.20)
    raw_score += source_trust
    raw_score -= min(0.10, source_rank * 0.02)
    score = max(0.0, min(0.99, raw_score))

    factors = {
        "sku_match": sku_match,
        "barcode_match": barcode_match,
        "title_similarity": round(title_similarity, 4),
        "source": candidate.source,
        "source_trust": source_trust,
    }

    reason_bits = []
    if sku_match:
        reason_bits.append("SKU match")
    if barcode_match:
        reason_bits.append("barcode match")
    if title_similarity >= 0.5:
        reason_bits.append("strong title similarity")
    elif title_similarity > 0:
        reason_bits.append("partial title similarity")
    if not reason_bits:
        reason_bits.append("weak identifier overlap")

    reason_sentence = (
        f"Candidate from {candidate.source} selected because "
        f"{', '.join(reason_bits)}."
    )
    return replace(
        candidate,
        confidence_score=score,
        confidence_badge=_badge(score),
        reason_sentence=reason_sentence,
        reason_factors=factors,
    )
