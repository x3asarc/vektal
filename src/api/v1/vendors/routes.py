"""Vendors API routes."""
from flask import request
from flask_login import login_required, current_user
from sqlalchemy import func

from src.api.v1.vendors import vendors_bp
from src.api.v1.vendors.schemas import (
    VendorDetailResponse,
    VendorFieldMappingListResponse,
    VendorFieldMappingResponse,
    VendorListResponse,
    VendorResponse,
)
from src.api.core.errors import ProblemDetails
from src.models import Product, Vendor, VendorCatalogItem, VendorFieldMapping, db


def _vendor_product_count(vendor: Vendor) -> int:
    """Count products for vendor using vendor code reference."""
    store = getattr(current_user, "shopify_store", None)
    if store is None:
        return 0
    return Product.query.filter_by(store_id=store.id, vendor_code=vendor.code).count()


def _mapping_to_response(mapping: VendorFieldMapping) -> VendorFieldMappingResponse:
    return VendorFieldMappingResponse(
        id=mapping.id,
        store_id=mapping.store_id,
        vendor_code=mapping.vendor_code,
        field_group=mapping.field_group,
        mapping_version=mapping.mapping_version,
        coverage_status=mapping.coverage_status,
        required_fields=[str(value) for value in (mapping.required_fields or [])],
        canonical_mapping=mapping.canonical_mapping or {},
        is_active=bool(mapping.is_active),
        created_at=mapping.created_at.isoformat() if mapping.created_at else None,
        updated_at=mapping.updated_at.isoformat() if mapping.updated_at else None,
    )


@vendors_bp.route('', methods=['GET'])
@login_required
def list_vendors():
    """
    List all vendors with product counts.

    Returns all vendors in the system with counts of products
    and catalog items associated with each.
    """
    vendors = (
        Vendor.query.filter_by(user_id=current_user.id, is_active=True)
        .order_by(Vendor.name)
        .all()
    )

    vendor_responses = []
    for vendor in vendors:
        # Count products and catalog items
        product_count = _vendor_product_count(vendor)
        catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

        vendor_responses.append(VendorResponse(
            id=vendor.id,
            code=vendor.code,
            name=vendor.name,
            website_url=vendor.website_url,
            country=getattr(vendor, 'country', None),
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
    vendor = Vendor.query.filter_by(id=vendor_id, user_id=current_user.id).first()
    if not vendor:
        return ProblemDetails.not_found("vendor", vendor_id)

    product_count = _vendor_product_count(vendor)
    catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

    return VendorDetailResponse(
        id=vendor.id,
        code=vendor.code,
        name=vendor.name,
        website_url=vendor.website_url,
        country=getattr(vendor, 'country', None),
        is_active=vendor.is_active,
        scraping_config=getattr(vendor, 'scraping_config', None),
        product_count=product_count,
        catalog_item_count=catalog_count,
        created_at=vendor.created_at.isoformat() if vendor.created_at else None,
        updated_at=vendor.updated_at.isoformat() if vendor.updated_at else None
    ).model_dump(), 200

@vendors_bp.route('/<string:code>', methods=['GET'])
@login_required
def get_vendor_by_code(code: str):
    """Get vendor by code (e.g., 'PENTART')."""
    vendor = Vendor.query.filter(
        Vendor.user_id == current_user.id,
        func.lower(Vendor.code) == code.lower(),
    ).first()
    if not vendor:
        return ProblemDetails.not_found("vendor", code)

    product_count = _vendor_product_count(vendor)
    catalog_count = VendorCatalogItem.query.filter_by(vendor_id=vendor.id).count()

    return VendorDetailResponse(
        id=vendor.id,
        code=vendor.code,
        name=vendor.name,
        website_url=vendor.website_url,
        country=getattr(vendor, 'country', None),
        is_active=vendor.is_active,
        scraping_config=getattr(vendor, 'scraping_config', None),
        product_count=product_count,
        catalog_item_count=catalog_count,
        created_at=vendor.created_at.isoformat() if vendor.created_at else None,
        updated_at=vendor.updated_at.isoformat() if vendor.updated_at else None
    ).model_dump(), 200


@vendors_bp.route('/<int:vendor_id>/mappings', methods=['GET'])
@login_required
def list_vendor_mappings(vendor_id: int):
    """List versioned field mappings for a vendor (store-scoped governance)."""
    vendor = Vendor.query.filter_by(id=vendor_id, user_id=current_user.id).first()
    if vendor is None:
        return ProblemDetails.not_found("vendor", vendor_id)
    store = getattr(current_user, "shopify_store", None)
    if store is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before loading vendor mappings.",
            409,
        )

    field_group = request.args.get("field_group")
    query = VendorFieldMapping.query.filter(
        VendorFieldMapping.store_id == store.id,
        func.lower(VendorFieldMapping.vendor_code) == vendor.code.lower(),
    )
    if field_group:
        query = query.filter(VendorFieldMapping.field_group == field_group)

    rows = query.order_by(
        VendorFieldMapping.field_group.asc(),
        VendorFieldMapping.mapping_version.desc(),
    ).all()
    payload = VendorFieldMappingListResponse(
        mappings=[_mapping_to_response(row) for row in rows],
        total=len(rows),
    )
    return payload.model_dump(), 200


@vendors_bp.route('/<int:vendor_id>/mappings/versions', methods=['POST'])
@login_required
def create_vendor_mapping_version(vendor_id: int):
    """Create a new vendor mapping version."""
    vendor = Vendor.query.filter_by(id=vendor_id, user_id=current_user.id).first()
    if vendor is None:
        return ProblemDetails.not_found("vendor", vendor_id)
    store = getattr(current_user, "shopify_store", None)
    if store is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before creating vendor mappings.",
            409,
        )

    payload = request.get_json(silent=True) or {}
    field_group = payload.get("field_group")
    if field_group not in {"images", "text", "pricing", "ids"}:
        return ProblemDetails.business_error(
            "invalid-field-group",
            "Invalid Field Group",
            "field_group must be one of: images, text, pricing, ids",
            422,
        )

    requested_version = payload.get("mapping_version")
    if requested_version is None:
        last = (
            VendorFieldMapping.query.filter(
                VendorFieldMapping.store_id == store.id,
                func.lower(VendorFieldMapping.vendor_code) == vendor.code.lower(),
                VendorFieldMapping.field_group == field_group,
            )
            .order_by(VendorFieldMapping.mapping_version.desc())
            .first()
        )
        mapping_version = (last.mapping_version + 1) if last else 1
    else:
        try:
            mapping_version = int(requested_version)
        except (TypeError, ValueError):
            return ProblemDetails.business_error(
                "invalid-mapping-version",
                "Invalid Mapping Version",
                "mapping_version must be an integer.",
                422,
            )

    mapping = VendorFieldMapping(
        store_id=store.id,
        vendor_code=vendor.code,
        field_group=field_group,
        mapping_version=mapping_version,
        coverage_status=payload.get("coverage_status", "incomplete"),
        source_schema=payload.get("source_schema"),
        canonical_mapping=payload.get("canonical_mapping") or {},
        required_fields=payload.get("required_fields") or [],
        metadata_json=payload.get("metadata_json"),
        is_active=bool(payload.get("is_active", True)),
        created_by_user_id=current_user.id,
    )
    db.session.add(mapping)
    db.session.commit()
    return _mapping_to_response(mapping).model_dump(), 201
