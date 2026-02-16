"""Product API routes."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from flask import request
from flask_login import current_user, login_required
from pydantic import ValidationError
from sqlalchemy import String, cast, func, or_

from src.api.core.errors import ProblemDetails
from src.api.core.pagination import build_cursor_response, decode_cursor
from src.api.v1.products import products_bp
from src.api.v1.products.schemas import (
    BulkStageRequest,
    EnrichmentCapabilityAuditRequest,
    EnrichmentCapabilityAuditResponse,
    EnrichmentDryRunPlanRequest,
    EnrichmentDryRunPlanResponse,
    ProductDetailResponse,
    ProductDiffQuery,
    ProductDiffResponse,
    ProductHistoryQuery,
    ProductHistoryResponse,
    ProductQuery,
    ProductChangeEventResponse,
    ProductResponse,
    ProductSearchItemResponse,
    ProductSearchPagination,
    ProductSearchQuery,
    ProductSearchResponse,
    ProductSearchScope,
)
from src.core.enrichment.capability_audit import run_capability_audit
from src.core.enrichment.contracts import RequestedMutation
from src.core.enrichment.write_plan import compile_write_plan
from src.api.v1.products.staging import stage_bulk_actions
from src.api.v1.products.search_query import (
    apply_keyset_cursor,
    apply_sort,
    decode_search_cursor,
    encode_search_cursor,
    extract_sort_value,
)
from src.models import Product, ProductChangeEvent, ProductEnrichmentItem, ProductEnrichmentRun, ShopifyStore, db

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


def _search_item(product: Product) -> ProductSearchItemResponse:
    base = _product_to_response(product).model_dump()
    return ProductSearchItemResponse(
        **base,
        inventory_total=None,
        protected_columns=list(PROTECTED_COLUMNS),
    )


def _apply_status_filter(query, status: str | None):
    if status == "active":
        return query.filter(Product.is_active.is_(True), Product.is_published.is_(True))
    if status == "draft":
        return query.filter(Product.is_active.is_(True), Product.is_published.is_(False))
    if status == "inactive":
        return query.filter(Product.is_active.is_(False))
    return query


def _base_query_for_current_user():
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return None
    return Product.query.filter_by(store_id=store.id)


def _build_selection_token(query_params: ProductSearchQuery, *, total_matching: int) -> str:
    signature = query_params.model_dump(exclude={"cursor", "limit"})
    signature["total_matching"] = total_matching
    canonical = json.dumps(signature, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def _enrichment_hash_from_payload(payload: EnrichmentDryRunPlanRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _capability_response_from_audit(audit) -> EnrichmentCapabilityAuditResponse:
    return EnrichmentCapabilityAuditResponse(
        supplier_code=audit.vendor_code,
        supplier_verified=audit.supplier_verified,
        policy_version=audit.policy_version,
        mapping_version=audit.mapping_version,
        alt_text_policy=audit.alt_text_policy,
        protected_columns=list(audit.protected_columns),
        generated_at=audit.generated_at.isoformat(),
        allowed_write_plan=[entry.to_dict() for entry in audit.allowed_write_plan],
        blocked_write_plan=[entry.to_dict() for entry in audit.blocked_write_plan],
        upgrade_guidance=list(audit.upgrade_guidance),
    )


def _coerce_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

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

    query = _base_query_for_current_user()
    if query is None:
        return build_cursor_response(items=[], has_next=False, limit=query_params.limit), 200

    # Apply vendor filter
    if query_params.vendor:
        query = query.filter(func.lower(Product.vendor_code) == query_params.vendor.lower())
    query = _apply_status_filter(query, query_params.status)

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
        items=[_product_to_response(product).model_dump() for product in products],
        has_next=has_next,
        limit=query_params.limit,
        last_item=products[-1] if products else None
    )

    return response_data, 200

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


@products_bp.route('/enrichment/capability-audit', methods=['POST'])
@login_required
def enrichment_capability_audit():
    """Return deterministic allowed/blocked write plan for enrichment preflight."""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before running enrichment capability audit.",
            409,
        )

    try:
        payload = EnrichmentCapabilityAuditRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc, status=422)

    audit = run_capability_audit(
        user_id=current_user.id,
        store_id=store.id,
        vendor_code=payload.supplier_code,
        requested_fields=payload.requested_fields,
        supplier_verified=payload.supplier_verified,
        requested_mapping_version=payload.mapping_version,
        alt_text_policy=payload.alt_text_policy,
    )
    response = _capability_response_from_audit(audit)
    return response.model_dump(), 200


@products_bp.route('/enrichment/dry-run-plan', methods=['POST'])
@login_required
def enrichment_dry_run_plan():
    """Compile and persist an enrichment dry-run write plan with policy lineage."""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before staging enrichment dry-runs.",
            409,
        )

    try:
        payload = EnrichmentDryRunPlanRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc, status=422)

    requested_fields = [mutation.field_name for mutation in payload.mutations]
    audit = run_capability_audit(
        user_id=current_user.id,
        store_id=store.id,
        vendor_code=payload.supplier_code,
        requested_fields=requested_fields,
        supplier_verified=payload.supplier_verified,
        requested_mapping_version=payload.mapping_version,
        alt_text_policy=payload.alt_text_policy,
    )

    proposed_mutations = [
        RequestedMutation(
            product_id=item.product_id,
            field_name=item.field_name,
            current_value=item.current_value,
            proposed_value=item.proposed_value,
            confidence=item.confidence,
            provenance=item.provenance,
        )
        for item in payload.mutations
    ]
    write_plan = compile_write_plan(audit=audit, proposed_mutations=proposed_mutations)

    idempotency_hash = _enrichment_hash_from_payload(payload)
    existing_run = ProductEnrichmentRun.query.filter_by(
        store_id=store.id,
        idempotency_hash=idempotency_hash,
    ).first()
    if existing_run is not None:
        persisted_items = (
            ProductEnrichmentItem.query.filter_by(run_id=existing_run.id)
            .order_by(ProductEnrichmentItem.id.asc())
            .all()
        )
        persisted_allowed = [row for row in persisted_items if row.decision_state != "blocked"]
        persisted_blocked = [row for row in persisted_items if row.decision_state == "blocked"]
        response = EnrichmentDryRunPlanResponse(
            run_id=existing_run.id,
            status=existing_run.status,
            run_profile=existing_run.run_profile,
            target_language=existing_run.target_language,
            policy_version=existing_run.policy_version,
            mapping_version=existing_run.mapping_version,
            alt_text_policy=existing_run.alt_text_policy,
            protected_columns=list(existing_run.protected_columns_json or []),
            dry_run_expires_at=_iso(existing_run.dry_run_expires_at),
            capability_audit=_capability_response_from_audit(audit),
            write_plan={
                "allowed": [
                    {
                        "product_id": row.product_id,
                        "field_name": row.field_name,
                        "field_group": row.field_group,
                        "before_value": row.before_value,
                        "after_value": row.after_value,
                        "policy_version": row.policy_version,
                        "mapping_version": row.mapping_version,
                        "reason_codes": list(row.reason_codes or []),
                        "requires_user_action": bool(row.requires_user_action),
                        "is_blocked": row.decision_state == "blocked",
                        "is_protected_column": bool(row.is_protected_column),
                        "alt_text_preserved": bool(row.alt_text_preserved),
                        "confidence": _coerce_float(row.confidence),
                        "provenance": row.provenance,
                    }
                    for row in persisted_allowed
                ],
                "blocked": [
                    {
                        "product_id": row.product_id,
                        "field_name": row.field_name,
                        "field_group": row.field_group,
                        "before_value": row.before_value,
                        "after_value": row.after_value,
                        "policy_version": row.policy_version,
                        "mapping_version": row.mapping_version,
                        "reason_codes": list(row.reason_codes or []),
                        "requires_user_action": bool(row.requires_user_action),
                        "is_blocked": True,
                        "is_protected_column": bool(row.is_protected_column),
                        "alt_text_preserved": bool(row.alt_text_preserved),
                        "confidence": _coerce_float(row.confidence),
                        "provenance": row.provenance,
                    }
                    for row in persisted_blocked
                ],
                "counts": {
                    "allowed": len(persisted_allowed),
                    "blocked": len(persisted_blocked),
                    "total": len(persisted_items),
                },
            },
        )
        return response.model_dump(), 200

    dry_run_expires_at = datetime.now(timezone.utc) + timedelta(minutes=payload.dry_run_ttl_minutes)
    capability_payload = _capability_response_from_audit(audit).model_dump()
    run = ProductEnrichmentRun(
        user_id=current_user.id,
        store_id=store.id,
        vendor_code=payload.supplier_code,
        run_profile=payload.run_profile,
        target_language=payload.target_language,
        status="dry_run_ready",
        policy_version=audit.policy_version,
        mapping_version=audit.mapping_version,
        idempotency_hash=idempotency_hash,
        dry_run_expires_at=dry_run_expires_at,
        alt_text_policy=payload.alt_text_policy,
        protected_columns_json=list(audit.protected_columns),
        capability_audit_json=capability_payload,
        metadata_json={
            "write_plan_counts": write_plan.counts,
        },
    )
    db.session.add(run)
    db.session.flush()

    for intent in [*write_plan.allowed, *write_plan.blocked]:
        item = ProductEnrichmentItem(
            run_id=run.id,
            product_id=intent.product_id,
            field_group=intent.field_group,
            field_name=intent.field_name,
            decision_state="blocked" if intent.is_blocked else "suggested",
            before_value=intent.before_value,
            after_value=intent.after_value,
            confidence=intent.confidence,
            provenance=intent.provenance,
            reason_codes=list(intent.reason_codes),
            evidence_refs=[],
            requires_user_action=intent.requires_user_action,
            is_protected_column=intent.is_protected_column,
            alt_text_preserved=intent.alt_text_preserved,
            policy_version=intent.policy_version,
            mapping_version=intent.mapping_version,
        )
        db.session.add(item)
    db.session.commit()

    response = EnrichmentDryRunPlanResponse(
        run_id=run.id,
        status=run.status,
        run_profile=run.run_profile,
        target_language=run.target_language,
        policy_version=run.policy_version,
        mapping_version=run.mapping_version,
        alt_text_policy=run.alt_text_policy,
        protected_columns=list(run.protected_columns_json or []),
        dry_run_expires_at=_iso(run.dry_run_expires_at),
        capability_audit=_capability_response_from_audit(audit),
        write_plan=write_plan.to_dict(),
    )
    return response.model_dump(), 201


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


@products_bp.route('/<int:product_id>/history', methods=['GET'])
@login_required
def get_product_history(product_id: int):
    """Return product change timeline for precision lineage panel."""
    try:
        params = ProductHistoryQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    query = _base_query_for_current_user()
    if query is None:
        return ProblemDetails.not_found("product", product_id)
    product = query.filter_by(id=product_id).first()
    if product is None:
        return ProblemDetails.not_found("product", product_id)

    events_query = ProductChangeEvent.query.filter_by(product_id=product.id, store_id=product.store_id)
    if params.cursor is not None:
        events_query = events_query.filter(ProductChangeEvent.id < params.cursor)
    events = (
        events_query.order_by(ProductChangeEvent.id.desc())
        .limit(params.limit + 1)
        .all()
    )
    has_next = len(events) > params.limit
    if has_next:
        events = events[: params.limit]

    next_cursor = events[-1].id if has_next and events else None
    response = ProductHistoryResponse(
        product_id=product.id,
        events=[_event_to_response(event) for event in events],
        pagination={
            "limit": params.limit,
            "has_next": has_next,
            "next_cursor": next_cursor,
        },
    )
    return response.model_dump(), 200


@products_bp.route('/<int:product_id>/diff', methods=['GET'])
@login_required
def get_product_diff(product_id: int):
    """Compare two history events for a product and return before/after diff payload."""
    try:
        params = ProductDiffQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    query = _base_query_for_current_user()
    if query is None:
        return ProblemDetails.not_found("product", product_id)
    product = query.filter_by(id=product_id).first()
    if product is None:
        return ProblemDetails.not_found("product", product_id)

    events = (
        ProductChangeEvent.query.filter_by(product_id=product.id, store_id=product.store_id)
        .order_by(ProductChangeEvent.id.desc())
        .all()
    )
    if len(events) < 2 and (params.from_event_id is None or params.to_event_id is None):
        return ProblemDetails.business_error(
            "insufficient-history",
            "Insufficient History",
            "At least two change events are required to compute a diff.",
            409,
        )

    event_by_id = {event.id: event for event in events}
    if params.from_event_id is not None:
        from_event = event_by_id.get(params.from_event_id)
    else:
        from_event = events[1]
    if params.to_event_id is not None:
        to_event = event_by_id.get(params.to_event_id)
    else:
        to_event = events[0]

    if from_event is None or to_event is None:
        return ProblemDetails.business_error(
            "invalid-history-anchor",
            "Invalid History Anchor",
            "Specified history event ids were not found for this product.",
            404,
        )

    changed_fields = _diff_keys(from_event.after_payload, to_event.after_payload)
    diff_payload = {
        key: {
            "before": (from_event.after_payload or {}).get(key),
            "after": (to_event.after_payload or {}).get(key),
        }
        for key in changed_fields
    }
    response = ProductDiffResponse(
        product_id=product.id,
        from_event_id=from_event.id,
        to_event_id=to_event.id,
        before_payload=from_event.after_payload,
        after_payload=to_event.after_payload,
        changed_fields=changed_fields,
        diff_payload=diff_payload,
    )
    return response.model_dump(), 200


@products_bp.route('/bulk/stage', methods=['POST'])
@login_required
def stage_product_bulk_actions():
    """Stage semantic action blocks into a dry-run batch with admission output."""
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    if store is None:
        return ProblemDetails.business_error(
            "store-not-connected",
            "Store Not Connected",
            "Connect a Shopify store before staging bulk actions.",
            409,
        )

    try:
        payload = BulkStageRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc, status=422)

    body, status_code = stage_bulk_actions(
        user_id=current_user.id,
        store_id=store.id,
        payload=payload,
    )
    return body, status_code


@products_bp.route('/search', methods=['GET'])
@login_required
def search_products():
    """Precision product search with deterministic cursor + scope metadata."""
    try:
        query_params = ProductSearchQuery(**request.args.to_dict())
    except ValidationError as exc:
        return ProblemDetails.validation_error(exc)

    if query_params.inventory_total_min is not None or query_params.inventory_total_max is not None:
        return ProblemDetails.business_error(
            "unsupported-filter",
            "Unsupported Filter",
            "inventory_total filtering is not available for this dataset yet.",
            400,
            unsupported_fields=["inventory_total"],
        )

    query = _base_query_for_current_user()
    if query is None:
        empty_response = ProductSearchResponse(
            data=[],
            pagination=ProductSearchPagination(limit=query_params.limit, has_next=False, next_cursor=None),
            scope=ProductSearchScope(
                scope_mode=query_params.scope_mode,
                total_matching=0,
                selection_token=_build_selection_token(query_params, total_matching=0),
            ),
        )
        return empty_response.model_dump(), 200

    # Identifier / text filters
    if query_params.q:
        needle = f"%{query_params.q.strip()}%"
        query = query.filter(
            or_(
                Product.sku.ilike(needle),
                Product.barcode.ilike(needle),
                Product.hs_code.ilike(needle),
                Product.vendor_code.ilike(needle),
                Product.title.ilike(needle),
                Product.product_type.ilike(needle),
                cast(Product.tags, String).ilike(needle),
            )
        )
    if query_params.sku:
        query = query.filter(Product.sku.ilike(f"%{query_params.sku.strip()}%"))
    if query_params.barcode:
        query = query.filter(Product.barcode.ilike(f"%{query_params.barcode.strip()}%"))
    if query_params.hs_code:
        query = query.filter(Product.hs_code.ilike(f"%{query_params.hs_code.strip()}%"))
    if query_params.vendor_code:
        query = query.filter(Product.vendor_code.ilike(f"%{query_params.vendor_code.strip()}%"))
    if query_params.title:
        query = query.filter(Product.title.ilike(f"%{query_params.title.strip()}%"))
    if query_params.product_type:
        query = query.filter(Product.product_type.ilike(f"%{query_params.product_type.strip()}%"))
    if query_params.tags:
        tags = [tag.strip().lower() for tag in query_params.tags.split(",") if tag.strip()]
        for tag in tags:
            query = query.filter(cast(Product.tags, String).ilike(f"%{tag}%"))

    query = _apply_status_filter(query, query_params.status)

    if query_params.price_min is not None:
        query = query.filter(Product.price >= query_params.price_min)
    if query_params.price_max is not None:
        query = query.filter(Product.price <= query_params.price_max)

    total_matching = query.count()
    selection_token = _build_selection_token(query_params, total_matching=total_matching)

    # Keyset cursor (sort contract must match)
    if query_params.cursor:
        try:
            parsed_cursor = decode_search_cursor(
                query_params.cursor,
                expected_sort_by=query_params.sort_by,
                expected_sort_dir=query_params.sort_dir,
            )
        except ValueError:
            return ProblemDetails.business_error(
                "invalid-cursor",
                "Invalid Cursor",
                "The pagination cursor is invalid for the current sort contract.",
                400,
            )
        query = apply_keyset_cursor(
            query,
            sort_by=query_params.sort_by,
            sort_dir=query_params.sort_dir,
            cursor=parsed_cursor,
        )

    query = apply_sort(query, sort_by=query_params.sort_by, sort_dir=query_params.sort_dir)
    rows = query.limit(query_params.limit + 1).all()
    has_next = len(rows) > query_params.limit
    if has_next:
        rows = rows[: query_params.limit]

    next_cursor = None
    if has_next and rows:
        last_row = rows[-1]
        next_cursor = encode_search_cursor(
            sort_by=query_params.sort_by,
            sort_dir=query_params.sort_dir,
            sort_value=extract_sort_value(last_row, sort_by=query_params.sort_by),
            last_id=last_row.id,
        )

    response = ProductSearchResponse(
        data=[_search_item(row) for row in rows],
        pagination=ProductSearchPagination(
            limit=query_params.limit,
            has_next=has_next,
            next_cursor=next_cursor,
        ),
        scope=ProductSearchScope(
            scope_mode=query_params.scope_mode,
            total_matching=total_matching,
            selection_token=selection_token,
        ),
    )
    return response.model_dump(), 200
