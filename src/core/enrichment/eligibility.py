"""Eligibility matrix for retrieval-oriented enrichment fields."""
from __future__ import annotations

from dataclasses import dataclass


PRODUCT_CLASS_PAINT = "paint_or_pigment"
PRODUCT_CLASS_PAPER = "paper_or_stationery"
PRODUCT_CLASS_GENERIC = "generic"

_CLASS_CRITICAL_FIELDS: dict[str, tuple[str, ...]] = {
    PRODUCT_CLASS_PAINT: ("title", "taxonomy", "color", "material"),
    PRODUCT_CLASS_PAPER: ("title", "taxonomy", "material", "dimensions"),
    PRODUCT_CLASS_GENERIC: ("title", "taxonomy"),
}

_CLASS_OPTIONAL_FIELDS: dict[str, tuple[str, ...]] = {
    PRODUCT_CLASS_PAINT: ("finish_effect", "compliance", "variant_pack", "media_semantics"),
    PRODUCT_CLASS_PAPER: ("finish_effect", "variant_pack", "media_semantics"),
    PRODUCT_CLASS_GENERIC: ("variant_pack", "media_semantics"),
}


@dataclass(frozen=True)
class EligibilityEntry:
    field_name: str
    eligible: bool
    critical: bool
    reason: str

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "eligible": self.eligible,
            "critical": self.critical,
            "reason": self.reason,
        }


def classify_product_class(product: dict) -> str:
    """Infer product class from product_type/title/tags."""
    haystack = " ".join(
        [
            str(product.get("product_type") or ""),
            str(product.get("title") or ""),
            " ".join(str(tag) for tag in (product.get("tags") or [])),
        ]
    ).lower()
    if any(token in haystack for token in ("farbe", "paint", "pigment", "acryl", "ink")):
        return PRODUCT_CLASS_PAINT
    if any(token in haystack for token in ("papier", "paper", "card", "stationery", "karton")):
        return PRODUCT_CLASS_PAPER
    return PRODUCT_CLASS_GENERIC


def build_eligibility_matrix(product: dict) -> dict[str, EligibilityEntry]:
    """Build category-aware matrix for critical and optional enrichment fields."""
    product_class = classify_product_class(product)
    critical_fields = set(_CLASS_CRITICAL_FIELDS[product_class])
    optional_fields = set(_CLASS_OPTIONAL_FIELDS[product_class])
    known_fields = critical_fields.union(optional_fields).union(
        {"compliance", "dimensions", "material", "color", "finish_effect"}
    )

    matrix: dict[str, EligibilityEntry] = {}
    for field_name in sorted(known_fields):
        is_critical = field_name in critical_fields
        eligible = field_name in critical_fields or field_name in optional_fields
        reason = "critical_for_class" if is_critical else ("optional_for_class" if eligible else "not_applicable")
        matrix[field_name] = EligibilityEntry(
            field_name=field_name,
            eligible=eligible,
            critical=is_critical,
            reason=reason,
        )
    return matrix

