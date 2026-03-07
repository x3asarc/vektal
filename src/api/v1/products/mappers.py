"""Shared mappers and helpers for Product API."""
from __future__ import annotations
import hashlib
import json
from datetime import timezone
from src.models import Product, ShopifyStore, ProductChangeEvent
from flask_login import current_user
from src.api.v1.products.schemas import (
    ProductResponse, 
    ProductDetailResponse,
    ProductSearchItemResponse,
    ProductChangeEventResponse
)

PROTECTED_COLUMNS = (
    "id",
    "store_id",
    "shopify_product_id",
    "shopify_variant_id",
    "created_at",
    "updated_at",
)

def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

def _product_status(product: Product) -> str:
    if not product.is_active:
        return "inactive"
    if product.is_published:
        return "active"
    return "draft"

def _product_to_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        barcode=product.barcode,
        title=product.title,
        vendor_code=product.vendor_code,
        shopify_product_id=str(product.shopify_product_id) if product.shopify_product_id is not None else None,
        price=float(product.price) if product.price is not None else None,
        compare_at_price=float(product.compare_at_price) if product.compare_at_price is not None else None,
        weight_grams=float(product.weight_kg) * 1000 if product.weight_kg is not None else None,
        status=_product_status(product),
        completeness_score=float(product.completeness_score) if product.completeness_score is not None else None,
        created_at=_iso(product.created_at),
        updated_at=_iso(product.updated_at),
    )

def _product_to_detail_response(product: Product) -> ProductDetailResponse:
    return ProductDetailResponse(
        id=product.id,
        store_id=product.store_id,
        shopify_product_id=str(product.shopify_product_id) if product.shopify_product_id is not None else None,
        shopify_variant_id=str(product.shopify_variant_id) if product.shopify_variant_id is not None else None,
        title=product.title,
        sku=product.sku,
        barcode=product.barcode,
        vendor_code=product.vendor_code,
        description=product.description,
        product_type=product.product_type,
        tags=list(product.tags or []),
        price=float(product.price) if product.price is not None else None,
        compare_at_price=float(product.compare_at_price) if product.compare_at_price is not None else None,
        cost=float(product.cost) if product.cost is not None else None,
        currency=product.currency,
        weight_kg=float(product.weight_kg) if product.weight_kg is not None else None,
        weight_unit=product.weight_unit,
        hs_code=product.hs_code,
        country_of_origin=product.country_of_origin,
        sync_status=product.sync_status,
        sync_error=product.sync_error,
        completeness_score=float(product.completeness_score) if product.completeness_score is not None else None,
        collections_json=product.collections_json,
        metafields_json=product.metafields_json,
        price_per_unit_value=float(product.price_per_unit_value) if product.price_per_unit_value is not None else None,
        price_per_unit_unit=product.price_per_unit_unit,
        is_active=bool(product.is_active),
        is_published=bool(product.is_published),
        created_at=_iso(product.created_at),
        updated_at=_iso(product.updated_at),
        images=[
            {
                "id": image.id,
                "src_url": image.src_url,
                "alt_text": image.alt_text,
                "position": image.position,
            }
            for image in product.images
        ],
    )

def _base_query_for_current_user():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return None
    return Product.query.filter_by(store_id=store.id)

def _connected_store_for_user():
    from src.api.core.errors import ProblemDetails
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return None, ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before running enrichment actions.",
            409,
        )
    return store, None

def _search_item(product: Product) -> ProductSearchItemResponse:
    base = _product_to_response(product).model_dump()
    return ProductSearchItemResponse(
        **base,
        inventory_total=None,
        protected_columns=list(PROTECTED_COLUMNS),
    )

def _event_to_response(event: ProductChangeEvent) -> ProductChangeEventResponse:
    return ProductChangeEventResponse(
        id=event.id,
        product_id=event.product_id,
        actor_user_id=event.actor_user_id,
        source=event.source,
        event_type=event.event_type,
        before_payload=event.before_payload,
        after_payload=event.after_payload,
        diff_payload=event.diff_payload,
        metadata_json=event.metadata_json,
        note=event.note,
        resolution_batch_id=event.resolution_batch_id,
        resolution_rule_id=event.resolution_rule_id,
        created_at=_iso(event.created_at),
    )

def _diff_keys(before_payload: dict | None, after_payload: dict | None) -> list[str]:
    before = before_payload or {}
    after = after_payload or {}
    keys = sorted(set(before.keys()) | set(after.keys()))
    return [key for key in keys if before.get(key) != after.get(key)]

def _build_selection_token(query_params, *, total_matching: int) -> str:
    signature = query_params.model_dump(exclude={"cursor", "limit"})
    signature["total_matching"] = total_matching
    canonical = json.dumps(signature, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

def _enrichment_hash_from_payload(payload) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
