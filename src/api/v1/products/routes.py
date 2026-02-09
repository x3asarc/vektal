"""Product API routes."""
from flask import request
from flask_login import login_required, current_user
from pydantic import ValidationError

from src.api.v1.products import products_bp
from src.api.v1.products.schemas import (
    ProductQuery, ProductResponse, ProductListResponse
)
from src.api.core.pagination import encode_cursor, decode_cursor, build_cursor_response
from src.api.core.errors import ProblemDetails
from src.models import Product, Vendor, db

@products_bp.route('', methods=['GET'])
@login_required
def list_products():
    """
    List products with cursor pagination.

    Query params:
        cursor: Pagination cursor (optional)
        limit: Items per page (1-100, default 50)
        vendor: Filter by vendor code (optional)
    """
    try:
        query_params = ProductQuery(**request.args.to_dict())
    except ValidationError as e:
        return ProblemDetails.validation_error(e)

    # Build query
    query = Product.query.filter_by(user_id=current_user.id)

    # Apply vendor filter
    if query_params.vendor:
        vendor = Vendor.query.filter_by(code=query_params.vendor).first()
        if vendor:
            query = query.filter_by(vendor_id=vendor.id)

    # Apply cursor pagination
    if query_params.cursor:
        try:
            last_id, last_ts = decode_cursor(query_params.cursor)
            query = query.filter(
                Product.created_at < last_ts,
                Product.id < last_id
            )
        except Exception:
            return ProblemDetails.business_error(
                "invalid-cursor", "Invalid Cursor",
                "The pagination cursor is invalid or expired", 400
            )

    # Order and limit
    products = query.order_by(
        Product.created_at.desc(),
        Product.id.desc()
    ).limit(query_params.limit + 1).all()

    # Check for next page
    has_next = len(products) > query_params.limit
    if has_next:
        products = products[:query_params.limit]

    # Build response
    response_data = build_cursor_response(
        items=[ProductResponse.model_validate(p).model_dump() for p in products],
        has_next=has_next,
        limit=query_params.limit,
        last_item=products[-1] if products else None
    )

    return response_data, 200

@products_bp.route('/<int:product_id>', methods=['GET'])
@login_required
def get_product(product_id: int):
    """Get single product by ID."""
    product = Product.query.filter_by(
        id=product_id, user_id=current_user.id
    ).first()

    if not product:
        return ProblemDetails.not_found("product", product_id)

    return ProductResponse.model_validate(product).model_dump(), 200
