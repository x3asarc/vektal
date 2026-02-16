"""Phase 13.1-02 eligibility and retrieval payload contracts."""
from __future__ import annotations

from src.core.enrichment.eligibility import (
    PRODUCT_CLASS_GENERIC,
    PRODUCT_CLASS_PAINT,
    build_eligibility_matrix,
    classify_product_class,
)
from src.core.enrichment.retrieval_payload import build_retrieval_payload


def test_product_classification_detects_paint_and_generic():
    paint = classify_product_class({"title": "Acrylfarbe Rot 20ml", "product_type": "Farbe"})
    generic = classify_product_class({"title": "Random Accessory", "product_type": "Accessory"})

    assert paint == PRODUCT_CLASS_PAINT
    assert generic == PRODUCT_CLASS_GENERIC


def test_eligibility_matrix_marks_critical_fields_by_class():
    matrix = build_eligibility_matrix({"title": "Acrylfarbe Rot 20ml", "product_type": "Farbe"})
    assert matrix["title"].critical is True
    assert matrix["taxonomy"].critical is True
    assert matrix["color"].critical is True
    assert matrix["finish_effect"].eligible is True


def test_retrieval_payload_is_broad_and_eligibility_driven():
    product = {
        "title": "Acrylfarbe Rot 20ml",
        "description": "Matte Farbe fuer Papier und Holz",
        "product_type": "Farbe",
        "tags": ["matte", "craft"],
        "vendor_code": "PENTART",
        "sku": "P-001",
        "barcode": "123",
        "extracted_color": "Red",
        "extracted_material": "Acryl",
        "finish_effect": "Matte",
        "hs_code": "32139000",
        "country_of_origin": "DE",
        "visual_hex": "#ff0000",
    }
    payload = build_retrieval_payload(
        product=product,
        target_language="de",
        profile_name="deep",
    )

    assert payload["identity"]["title"] == "Acrylfarbe Rot 20ml"
    assert payload["physical"]["color"] == "Red"
    assert payload["physical"]["material"] == "Acryl"
    assert payload["physical"]["finish_effect"] == "Matte"
    assert payload["compliance"]["hs_code"] == "32139000"
    assert "paint" in payload["retrieval_support"]["synonym_surface"]
    assert payload["trust"]["retrieval_ready"] is True
