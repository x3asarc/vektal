"""Core product catalog routes."""
from __future__ import annotations
from flask import request
from flask_login import login_required
from pydantic import ValidationError
from sqlalchemy import String, cast, func, or_

from src.api.core.errors import ProblemDetails
from src.api.core.pagination import build_cursor_response, decode_cursor
from src.api.v1.products import products_bp
from src.api.v1.products.schemas import (
    ProductQuery,
    ProductSearchPagination,
    ProductSearchQuery,
    ProductSearchResponse,
    ProductSearchScope,
)
from src.api.v1.products.mappers import (
    _product_to_response,
    _product_to_detail_response,
    _search_item,
    _base_query_for_current_user,
    _build_selection_token
)
from src.api.v1.products.search_query import (
    apply_keyset_cursor,
    apply_sort,
    decode_search_cursor,
    encode_search_cursor,
    extract_sort_value,
)
from src.models import Product

def _apply_status_filter(query, status: str | None):
    if status == "active":
        return query.filter(Product.is_active.is_(True), Product.is_published.is_(True))
    if status == "draft":
        return query.filter(Product.is_active.is_(True), Product.is_published.is_(False))
    if status == "inactive":
        return query.filter(Product.is_active.is_(False))
    return query

@products_bp.route('', methods=['GET'])
@login_required
def list_products():
    """List products with cursor pagination."""
    try:
        query_params = ProductQuery(**request.args.to_dict())
    except ValidationError as e:
        return ProblemDetails.validation_error(e)

    query = _base_query_for_current_user()
    if query is None:
        return build_cursor_response(items=[], has_next=False, limit=query_params.limit), 200

    if query_params.vendor:
        query = query.filter(func.lower(Product.vendor_code) == query_params.vendor.lower())
    query = _apply_status_filter(query, query_params.status)

    if query_params.cursor:
        try:
            last_id, last_ts = decode_cursor(query_params.cursor)
            query = query.filter(Product.created_at < last_ts, Product.id < last_id)
        except Exception:
            return ProblemDetails.business_error("invalid-cursor", "Invalid Cursor", "The pagination cursor is invalid", 400)

    products = query.order_by(Product.created_at.desc(), Product.id.desc()).limit(query_params.limit + 1).all()
    has_next = len(products) > query_params.limit
    if has_next:
        products = products[:query_params.limit]

    return build_cursor_response(
        items=[_product_to_response(product).model_dump() for product in products],
        has_next=has_next,
        limit=query_params.limit,
        last_item=products[-1] if products else None
    ), 200

@products_bp.route('/<int:product_id>', methods=['GET'])
@login_required
def get_product(product_id: int):
    """Get single product by ID."""
    query = _base_query_for_current_user()
    if query is None:
        return ProblemDetails.not_found("product", product_id)
    product = query.filter_by(id=product_id).first()
    if not product:
        return ProblemDetails.not_found("product", product_id)
    return _product_to_detail_response(product).model_dump(), 200

@products_bp.route('/search', methods=['GET'])
@login_required
def search_products():
    """Precision product search with deterministic cursor."""
    try:
        query_params = ProductSearchQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    query = _base_query_for_current_user()
    if query is None:
        return ProductSearchResponse(
            data=[],
            pagination=ProductSearchPagination(limit=query_params.limit, has_next=False, next_cursor=None),
            scope=ProductSearchScope(scope_mode=query_params.scope_mode, total_matching=0, selection_token=_build_selection_token(query_params, total_matching=0)),
        ).model_dump(), 200

    # Filtering logic
    if query_params.q:
        needle = f"%{query_params.q.strip()}%"
        query = query.filter(or_(
            Product.sku.ilike(needle), Product.barcode.ilike(needle), Product.title.ilike(needle),
            Product.product_type.ilike(needle), cast(Product.tags, String).ilike(needle),
        ))
    if query_params.vendor_code:
        query = query.filter(Product.vendor_code.ilike(f"%{query_params.vendor_code.strip()}%"))
    
    query = _apply_status_filter(query, query_params.status)

    if query_params.price_min is not None:
        query = query.filter(Product.price >= query_params.price_min)
    if query_params.price_max is not None:
        query = query.filter(Product.price <= query_params.price_max)
    if query_params.completeness_min is not None:
        query = query.filter(Product.completeness_score >= query_params.completeness_min)
    if query_params.completeness_max is not None:
        query = query.filter(Product.completeness_score <= query_params.completeness_max)

    total_matching = query.count()
    selection_token = _build_selection_token(query_params, total_matching=total_matching)

    if query_params.cursor:
        try:
            parsed_cursor = decode_search_cursor(query_params.cursor, expected_sort_by=query_params.sort_by, expected_sort_dir=query_params.sort_dir)
            query = apply_keyset_cursor(query, sort_by=query_params.sort_by, sort_dir=query_params.sort_dir, cursor=parsed_cursor)
        except ValueError:
            return ProblemDetails.business_error("invalid-cursor", "Invalid Cursor", "The cursor is invalid", 400)

    query = apply_sort(query, sort_by=query_params.sort_by, sort_dir=query_params.sort_dir)
    rows = query.limit(query_params.limit + 1).all()
    has_next = len(rows) > query_params.limit
    if has_next:
        rows = rows[: query_params.limit]

    next_cursor = encode_search_cursor(
        sort_by=query_params.sort_by, sort_dir=query_params.sort_dir,
        sort_value=extract_sort_value(rows[-1], sort_by=query_params.sort_by), last_id=rows[-1].id
    ) if has_next and rows else None

    return ProductSearchResponse(
        data=[_search_item(row) for row in rows],
        pagination=ProductSearchPagination(limit=query_params.limit, has_next=has_next, next_cursor=next_cursor),
        scope=ProductSearchScope(scope_mode=query_params.scope_mode, total_matching=total_matching, selection_token=selection_token),
    ).model_dump(), 200
