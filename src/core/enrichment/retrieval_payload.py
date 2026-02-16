"""Canonical retrieval-ready payload builder for enrichment outputs."""
from __future__ import annotations

from typing import Any

from src.core.enrichment.eligibility import EligibilityEntry, build_eligibility_matrix
from src.core.enrichment.provenance import build_provenance, with_provenance


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _sparse_keywords(product: dict) -> list[str]:
    terms = set()
    for field in ("title", "description", "product_type"):
        value = _normalize_text(product.get(field))
        if value:
            for token in value.lower().replace(",", " ").split():
                if len(token) >= 3:
                    terms.add(token)
    for tag in product.get("tags") or []:
        token = _normalize_text(tag)
        if token:
            terms.add(token.lower())
    return sorted(terms)


def _synonym_surface(product: dict) -> list[str]:
    synonyms = set()
    title = (_normalize_text(product.get("title")) or "").lower()
    if "farbe" in title or "paint" in title:
        synonyms.update({"paint", "farbe", "pigment"})
    if "papier" in title or "paper" in title:
        synonyms.update({"paper", "papier", "cardstock"})
    finish = (_normalize_text(product.get("finish_effect")) or "").lower()
    if finish:
        synonyms.add(finish)
    return sorted(synonyms)


def _lang_norm(text: str | None, target_language: str) -> dict[str, str] | None:
    if not text:
        return None
    value = text.strip()
    if not value:
        return None
    if target_language == "de":
        return {"de": value, "en": value}
    return {"en": value, "de": value}


def _eligible(entry_map: dict[str, EligibilityEntry], field_name: str) -> bool:
    entry = entry_map.get(field_name)
    return bool(entry and entry.eligible)


def build_retrieval_payload(
    *,
    product: dict,
    target_language: str,
    profile_name: str,
    confidence_by_field: dict[str, float] | None = None,
    source_by_field: dict[str, str] | None = None,
    eligibility_matrix: dict[str, EligibilityEntry] | None = None,
) -> dict[str, Any]:
    """Build a broad retrieval payload shaped by eligibility rules."""
    confidence_by_field = confidence_by_field or {}
    source_by_field = source_by_field or {}
    eligibility = eligibility_matrix or build_eligibility_matrix(product)

    title = _normalize_text(product.get("title"))
    product_type = _normalize_text(product.get("product_type"))
    color = _normalize_text(product.get("extracted_color") or product.get("color"))
    material = _normalize_text(product.get("extracted_material") or product.get("material"))
    finish = _normalize_text(product.get("finish_effect"))
    dimensions = _normalize_text(product.get("dimensions"))
    hs_code = _normalize_text(product.get("hs_code"))
    country = _normalize_text(product.get("country_of_origin"))
    tags = [str(tag).strip() for tag in (product.get("tags") or []) if str(tag).strip()]

    payload: dict[str, Any] = {
        "profile_name": profile_name,
        "target_language": target_language,
        "identity": {
            "sku": _normalize_text(product.get("sku")),
            "barcode": _normalize_text(product.get("barcode")),
            "title": title,
            "vendor_code": _normalize_text(product.get("vendor_code")),
        },
        "taxonomy": {
            "product_type": product_type,
            "tags": tags,
            "category_path": _normalize_text(product.get("category_path")),
        },
        "commercial": {
            "price": product.get("price"),
            "compare_at_price": product.get("compare_at_price"),
            "variant_pack": _normalize_text(product.get("pack_size")),
        },
        "physical": {},
        "compliance": {},
        "media_semantics": {},
        "trust": {
            "eligibility": {key: value.to_dict() for key, value in eligibility.items()},
            "field_provenance": {},
            "conflict_flags": [],
        },
        "retrieval_support": {
            "facet_fields": {},
            "sparse_keywords": _sparse_keywords(product),
            "synonym_surface": _synonym_surface(product),
            "language_norm": {
                "title": _lang_norm(title, target_language),
                "product_type": _lang_norm(product_type, target_language),
            },
        },
    }

    if _eligible(eligibility, "color") and color:
        payload["physical"]["color"] = color
        payload["retrieval_support"]["facet_fields"]["color"] = color
        payload["trust"]["field_provenance"]["color"] = with_provenance(
            color,
            build_provenance(
                source=source_by_field.get("color", "ai_inferred"),
                confidence=confidence_by_field.get("color"),
                reason_codes=["eligibility_pass"],
            ),
        )
    if _eligible(eligibility, "material") and material:
        payload["physical"]["material"] = material
        payload["retrieval_support"]["facet_fields"]["material"] = material
        payload["trust"]["field_provenance"]["material"] = with_provenance(
            material,
            build_provenance(
                source=source_by_field.get("material", "ai_inferred"),
                confidence=confidence_by_field.get("material"),
                reason_codes=["eligibility_pass"],
            ),
        )
    if _eligible(eligibility, "finish_effect") and finish:
        payload["physical"]["finish_effect"] = finish
        payload["retrieval_support"]["facet_fields"]["finish_effect"] = finish
        payload["trust"]["field_provenance"]["finish_effect"] = with_provenance(
            finish,
            build_provenance(
                source=source_by_field.get("finish_effect", "ai_inferred"),
                confidence=confidence_by_field.get("finish_effect"),
                reason_codes=["eligibility_pass"],
            ),
        )
    if _eligible(eligibility, "dimensions") and dimensions:
        payload["physical"]["dimensions"] = dimensions
    if _eligible(eligibility, "compliance"):
        if hs_code:
            payload["compliance"]["hs_code"] = hs_code
        if country:
            payload["compliance"]["country_of_origin"] = country

    visual_hex = _normalize_text(product.get("visual_hex"))
    if visual_hex:
        payload["media_semantics"]["visual_hex"] = visual_hex

    # Critical field gate marker for downstream retrieval-readiness scoring.
    critical_missing: list[str] = []
    for field_name, entry in eligibility.items():
        if not entry.critical:
            continue
        if field_name == "title" and not title:
            critical_missing.append(field_name)
        if field_name == "taxonomy" and not product_type:
            critical_missing.append(field_name)
        if field_name == "color" and _eligible(eligibility, "color") and not color:
            critical_missing.append(field_name)
        if field_name == "material" and _eligible(eligibility, "material") and not material:
            critical_missing.append(field_name)
    payload["trust"]["critical_missing_fields"] = sorted(set(critical_missing))
    payload["trust"]["retrieval_ready"] = len(payload["trust"]["critical_missing_fields"]) == 0

    return payload

