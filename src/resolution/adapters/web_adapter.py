"""Web adapter for supplemental resolution candidates."""
from __future__ import annotations

from src.core.scrape_engine import scrape_missing_fields
from src.resolution.contracts import Candidate, NormalizedQuery


def search_web_candidates(
    query: NormalizedQuery,
    *,
    product_hint: dict | None = None,
) -> list[Candidate]:
    """
    Resolve one candidate using existing scrape engine.

    Caller is responsible for policy gating (supplier verification).
    """
    if query.sku:
        identifier = {"kind": "sku", "value": query.sku}
    elif query.barcode:
        identifier = {"kind": "ean", "value": query.barcode}
    elif query.title:
        identifier = {"kind": "title", "value": query.title}
    else:
        return []

    scraped = scrape_missing_fields(
        identifier=identifier,
        product=product_hint,
        vendor=query.supplier_code,
        corrections=[],
    )
    if not scraped:
        return []

    candidate = Candidate(
        source="web",
        product_id=None,
        shopify_product_id=None,
        sku=(scraped.get("sku") or query.sku),
        barcode=(scraped.get("scraped_sku") or query.barcode),
        title=(scraped.get("title") or query.title),
        price=None,
        variant_options=[],
        payload=scraped,
    )
    return [candidate]
