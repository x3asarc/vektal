"""Shopify source adapter for resolution candidates."""
from __future__ import annotations

from decimal import Decimal

from src.core.shopify_resolver import ShopifyResolver
from src.models.product import Product
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


def search_shopify_candidates(query: NormalizedQuery, *, limit: int = 5) -> list[Candidate]:
    """
    Search persisted Shopify products first.

    This intentionally reuses the existing Product model as primary source of truth.
    """
    base = Product.query.filter_by(store_id=query.store_id, is_active=True)
    rows: list[Product] = []

    if query.sku:
        rows = base.filter(Product.sku == query.sku).limit(limit).all()
    if not rows and query.barcode:
        rows = base.filter(Product.barcode == query.barcode).limit(limit).all()
    if not rows and query.title:
        rows = base.filter(Product.title.ilike(f"%{query.title}%")).limit(limit).all()

    candidates = [
        Candidate(
            source="shopify",
            product_id=row.id,
            shopify_product_id=row.shopify_product_id,
            sku=row.sku,
            barcode=row.barcode,
            title=row.title,
            price=_as_float(row.price),
            variant_options=[],
            payload={
                "product_type": row.product_type,
                "shopify_variant_id": row.shopify_variant_id,
                "description": row.description,
            },
        )
        for row in rows
    ]

    # Optional live fallback using existing resolver implementation.
    if candidates:
        return candidates
    live_ctx = (query.payload or {}).get("shopify_context") or {}
    if not live_ctx:
        return []
    return _search_live_catalog(query, live_ctx=live_ctx, limit=limit)


def _search_live_catalog(
    query: NormalizedQuery, *, live_ctx: dict[str, str], limit: int
) -> list[Candidate]:
    resolver = ShopifyResolver(
        shop_domain=live_ctx.get("shop_domain"),
        access_token=live_ctx.get("access_token"),
        api_version=live_ctx.get("api_version"),
    )

    if query.sku:
        identifier = {"kind": "sku", "value": query.sku}
    elif query.barcode:
        identifier = {"kind": "ean", "value": query.barcode}
    elif query.title:
        identifier = {"kind": "title", "value": query.title}
    else:
        return []

    resolved = resolver.resolve_identifier(identifier)
    matches = resolved.get("matches", [])[:limit]
    return [
        Candidate(
            source="shopify",
            product_id=None,
            shopify_product_id=None,
            sku=(match.get("primary_variant") or {}).get("sku"),
            barcode=(match.get("primary_variant") or {}).get("barcode"),
            title=match.get("title"),
            price=_as_float((match.get("primary_variant") or {}).get("price")),
            variant_options=[],
            payload=match,
        )
        for match in matches
    ]
