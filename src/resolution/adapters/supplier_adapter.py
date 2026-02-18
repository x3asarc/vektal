"""Supplier catalog adapter for resolution candidates."""
from __future__ import annotations

from decimal import Decimal

from src.models.vendor import Vendor, VendorCatalogItem
from src.resolution.contracts import Candidate, NormalizedQuery


def _as_float(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def search_supplier_candidates(
    query: NormalizedQuery,
    *,
    user_id: int,
    limit: int = 5,
) -> list[Candidate]:
    """Search verified supplier catalog rows for this user."""
    vendor = Vendor.query.filter_by(
        user_id=user_id,
        code=query.supplier_code,
        is_active=True,
    ).first()
    if vendor is None:
        return []

    rows_query = VendorCatalogItem.query.filter_by(vendor_id=vendor.id, is_active=True)
    rows: list[VendorCatalogItem] = []
    if query.sku:
        rows = rows_query.filter(VendorCatalogItem.sku == query.sku).limit(limit).all()
    if not rows and query.barcode:
        rows = rows_query.filter(VendorCatalogItem.barcode == query.barcode).limit(limit).all()
    if not rows and query.title:
        rows = rows_query.filter(VendorCatalogItem.name.ilike(f"%{query.title}%")).limit(limit).all()

    candidates: list[Candidate] = []
    for row in rows:
        payload = row.raw_data or {}
        variant_options = payload.get("variant_options") or payload.get("options") or []
        if isinstance(variant_options, str):
            variant_options = [part.strip() for part in variant_options.split(",") if part.strip()]
        candidates.append(
            Candidate(
                source="supplier",
                product_id=None,
                shopify_product_id=None,
                sku=row.sku,
                barcode=row.barcode,
                title=row.name,
                price=_as_float(row.price),
                variant_options=variant_options,
                payload={
                    "vendor_item_id": row.id,
                    "vendor_id": vendor.id,
                    "product_type": payload.get("product_type"),
                    "raw_data": payload,
                    "description": row.description,
                    "image_url": row.image_url,
                },
            )
        )
    return candidates
