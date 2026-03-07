"""Product lineage and rollback routes."""
from __future__ import annotations
from flask import jsonify, request
from flask_login import current_user, login_required
from pydantic import ValidationError

from src.api.core.errors import ProblemDetails
from src.api.v1.products import products_bp
from src.api.v1.products.schemas import (
    ProductHistoryQuery,
    ProductHistoryResponse,
    ProductDiffQuery,
    ProductDiffResponse,
)
from src.api.v1.products.mappers import (
    _iso,
    _event_to_response,
    _diff_keys,
    _base_query_for_current_user,
    _connected_store_for_user,
)
from src.models import (
    db,
    Product,
    ProductChangeEvent,
)

@products_bp.route('/<int:product_id>/history', methods=['GET'])
@login_required
def get_product_history(product_id: int):
    """Return product change timeline."""
    try:
        params = ProductHistoryQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    query = _base_query_for_current_user()
    if query is None: return ProblemDetails.not_found("product", product_id)
    product = query.filter_by(id=product_id).first()
    if product is None: return ProblemDetails.not_found("product", product_id)

    events_query = ProductChangeEvent.query.filter_by(product_id=product.id, store_id=product.store_id)
    if params.cursor is not None:
        events_query = events_query.filter(ProductChangeEvent.id < params.cursor)
    events = events_query.order_by(ProductChangeEvent.id.desc()).limit(params.limit + 1).all()
    has_next = len(events) > params.limit
    if has_next: events = events[: params.limit]

    return ProductHistoryResponse(
        product_id=product.id,
        events=[_event_to_response(event) for event in events],
        pagination={"limit": params.limit, "has_next": has_next, "next_cursor": events[-1].id if has_next and events else None},
    ).model_dump(), 200

@products_bp.route('/<int:product_id>/diff', methods=['GET'])
@login_required
def get_product_diff(product_id: int):
    """Compare two history events."""
    try:
        params = ProductDiffQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    query = _base_query_for_current_user()
    if query is None: return ProblemDetails.not_found("product", product_id)
    product = query.filter_by(id=product_id).first()
    if product is None: return ProblemDetails.not_found("product", product_id)

    events = ProductChangeEvent.query.filter_by(product_id=product.id, store_id=product.store_id).order_by(ProductChangeEvent.id.desc()).all()
    if len(events) < 2 and (params.from_event_id is None or params.to_event_id is None):
        return ProblemDetails.business_error("insufficient-history", "Insufficient History", "At least two events required", 409)

    event_by_id = {event.id: event for event in events}
    from_event = event_by_id.get(params.from_event_id) if params.from_event_id else events[1]
    to_event = event_by_id.get(params.to_event_id) if params.to_event_id else events[0]

    if not from_event or not to_event:
        return ProblemDetails.business_error("invalid-history-anchor", "Invalid Anchor", "Events not found", 404)

    changed_fields = _diff_keys(from_event.after_payload, to_event.after_payload)
    diff_payload = {k: {"before": (from_event.after_payload or {}).get(k), "after": (to_event.after_payload or {}).get(k)} for k in changed_fields}
    
    return ProductDiffResponse(
        product_id=product.id, from_event_id=from_event.id, to_event_id=to_event.id,
        before_payload=from_event.after_payload, after_payload=to_event.after_payload,
        changed_fields=changed_fields, diff_payload=diff_payload,
    ).model_dump(), 200

@products_bp.route('/<int:product_id>/rollback/<int:event_id>/preflight', methods=['GET'])
@login_required
def rollback_preflight(product_id: int, event_id: int):
    """Audit structural divergence before rollback."""
    store, err = _connected_store_for_user()
    if err: return err
    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    if not product: return ProblemDetails.not_found("product", product_id)
    target_event = ProductChangeEvent.query.filter_by(id=event_id, product_id=product_id).first()
    if not target_event: return ProblemDetails.not_found("history-event", event_id)

    from src.core.shopify_resolver import ShopifyResolver
    resolver = ShopifyResolver(shop_domain=store.shop_domain, access_token=store.get_access_token())
    live_shopify_data = resolver._rest_get_product_by_id(product.shopify_product_id)
    if not live_shopify_data: return jsonify({"status": "blocked", "reason": "deleted_in_shopify", "can_rollback": False}), 409

    live_variant_ids = {v['id'] for v in live_shopify_data.get('variants', [])}
    target_variant_id = product.shopify_variant_id
    structural_conflict = f"gid://shopify/ProductVariant/{target_variant_id}" not in live_variant_ids and str(target_variant_id) not in live_variant_ids
    
    return jsonify({
        "status": "warning" if structural_conflict else "safe", "can_rollback": True,
        "structural_conflict": structural_conflict, "warning_notes": ["ID divergence detected"] if structural_conflict else [],
        "diff": {"title": {"before": live_shopify_data.get('title'), "after": (target_event.after_payload or {}).get('title')}}
    }), 200

@products_bp.route('/<int:product_id>/rollback/<int:event_id>', methods=['POST'])
@login_required
def execute_rollback(product_id: int, event_id: int):
    """Apply historical state."""
    store, err = _connected_store_for_user()
    if err: return err
    product = Product.query.filter_by(id=product_id, store_id=store.id).first()
    target_event = ProductChangeEvent.query.filter_by(id=event_id, product_id=product_id).first()
    if not product or not target_event: return ProblemDetails.not_found("not-found", event_id)

    new_event = ProductChangeEvent(
        product_id=product.id, store_id=store.id, actor_user_id=current_user.id,
        source='workspace', event_type='rollback', before_payload={"title": product.title},
        after_payload=target_event.after_payload, note=f"Rolled back to #{event_id}"
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"status": "success", "event_id": new_event.id}), 200
