"""Structural conflict detection for product and variant mismatches."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.resolution.contracts import Candidate


class StructuralConflictType(str, Enum):
    MISSING_PRODUCT = "missing_product"
    NEW_VARIANTS_DETECTED = "new_variants_detected"
    OPTION_SCHEMA_MISMATCH = "option_schema_mismatch"
    STRUCTURAL_REVIEW = "structural_review"


@dataclass(frozen=True)
class StructuralConflict:
    conflict_type: StructuralConflictType
    detail: str
    metadata: dict[str, Any] | None = None


def detect_structural_conflict(
    *,
    shopify_candidate: Candidate | None,
    supplier_candidate: Candidate | None,
    input_row: dict[str, Any],
) -> StructuralConflict | None:
    """Classify structural mismatches that must not be silently auto-applied."""
    if shopify_candidate is None and supplier_candidate is not None:
        return StructuralConflict(
            conflict_type=StructuralConflictType.MISSING_PRODUCT,
            detail="Supplier row not found in Shopify catalog; route to Draft New Product flow.",
            metadata={"resolution_path": "draft_new_product"},
        )

    if shopify_candidate is None:
        return StructuralConflict(
            conflict_type=StructuralConflictType.STRUCTURAL_REVIEW,
            detail="No Shopify match found; manual structural review required.",
            metadata={"resolution_path": "manual_review"},
        )

    shopify_variants = set(shopify_candidate.variant_options or [])
    incoming_variants_raw = input_row.get("variant_options") or []
    if isinstance(incoming_variants_raw, str):
        incoming_variants = {piece.strip() for piece in incoming_variants_raw.split(",") if piece.strip()}
    else:
        incoming_variants = {str(value).strip() for value in incoming_variants_raw if str(value).strip()}

    missing_variants = sorted(incoming_variants - shopify_variants)
    if missing_variants:
        return StructuralConflict(
            conflict_type=StructuralConflictType.NEW_VARIANTS_DETECTED,
            detail=(
                "Supplier includes variants not present in Shopify. "
                f"Explicit create approval required: {', '.join(missing_variants)}."
            ),
            metadata={
                "missing_variants": missing_variants,
                "safe_default": {"status": "draft", "inventory": 0},
            },
        )

    shopify_product_type = (shopify_candidate.payload or {}).get("product_type")
    incoming_product_type = input_row.get("product_type") or (supplier_candidate.payload or {}).get("product_type") if supplier_candidate else None
    if shopify_product_type and incoming_product_type and shopify_product_type != incoming_product_type:
        return StructuralConflict(
            conflict_type=StructuralConflictType.OPTION_SCHEMA_MISMATCH,
            detail=(
                "Product type/option schema mismatch detected; structural review required "
                "before apply."
            ),
            metadata={
                "shopify_product_type": shopify_product_type,
                "incoming_product_type": incoming_product_type,
            },
        )

    return None
