"""Vendors API routes."""
from flask import request
from flask_login import login_required, current_user

from src.api.v1.vendors import vendors_bp
from src.api.v1.vendors.schemas import (
    VendorResponse, VendorListResponse, VendorDetailResponse
)
from src.api.core.errors import ProblemDetails
from src.models import Vendor, Product, VendorCatalogItem, db

@vendors_bp.route('', methods=['GET'])
@login_required
def list_vendors():
    """
    List all vendors with product counts.

    Returns all vendors in the system with counts of products
    and catalog items associated with each.
    """
    vendors = Vendor.query.filter_by(is_active=True).order_by(Vendor.name).all()

    vendor_responses = []
    for vendor in vendors:
        # Count products and catalog items
        product_count = Product.query.filter_by(vendor_id=vendor.id).count()
        catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

        vendor_responses.append(VendorResponse(
            id=vendor.id,
            code=vendor.code,
            name=vendor.name,
            website_url=vendor.website_url,
            country=vendor.country,
            is_active=vendor.is_active,
            product_count=product_count,
            catalog_item_count=catalog_count,
            created_at=vendor.created_at.isoformat() if vendor.created_at else None
        ))

    return VendorListResponse(
        vendors=vendor_responses,
        total=len(vendor_responses)
    ).model_dump(), 200

@vendors_bp.route('/<int:vendor_id>', methods=['GET'])
@login_required
def get_vendor(vendor_id: int):
    """Get vendor details including scraping configuration."""
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return ProblemDetails.not_found("vendor", vendor_id)

    product_count = Product.query.filter_by(vendor_id=vendor.id).count()
    catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

    return VendorDetailResponse(
        id=vendor.id,
        code=vendor.code,
        name=vendor.name,
        website_url=vendor.website_url,
        country=vendor.country,
        is_active=vendor.is_active,
        scraping_config=vendor.scraping_config,
        product_count=product_count,
        catalog_item_count=catalog_count,
        created_at=vendor.created_at.isoformat() if vendor.created_at else None,
        updated_at=vendor.updated_at.isoformat() if vendor.updated_at else None
    ).model_dump(), 200

@vendors_bp.route('/<string:code>', methods=['GET'])
@login_required
def get_vendor_by_code(code: str):
    """Get vendor by code (e.g., 'PENTART')."""
    vendor = Vendor.query.filter_by(code=code.upper()).first()
    if not vendor:
        return ProblemDetails.not_found("vendor", code)

    product_count = Product.query.filter_by(vendor_id=vendor.id).count()
    catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

    return VendorDetailResponse(
        id=vendor.id,
        code=vendor.code,
        name=vendor.name,
        website_url=vendor.website_url,
        country=vendor.country,
        is_active=vendor.is_active,
        scraping_config=vendor.scraping_config,
        product_count=product_count,
        catalog_item_count=catalog_count,
        created_at=vendor.created_at.isoformat() if vendor.created_at else None,
        updated_at=vendor.updated_at.isoformat() if vendor.updated_at else None
    ).model_dump(), 200
