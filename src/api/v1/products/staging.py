"""Semantic bulk staging orchestration for Phase 11."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from src.api.v1.products.schemas import BulkActionBlock, BulkStageRequest
from src.api.v1.resolution.routes import create_dry_run_batch_for_user
from src.models import Product, ProductChangeEvent, ResolutionBatch, VendorFieldMapping, db

PROTECTED_FIELDS = {
    "id",
    "store_id",
    "shopify_product_id",
    "shopify_variant_id",
    "created_at",
    "updated_at",
}

SUPPORTED_MUTATION_FIELDS = {
    "title",
    "description",
    "price",
    "sku",
    "barcode",
    "image_url",
    "product_type",
    "tags",
    "alt_text",
}

FIELD_GROUP_BY_FIELD = {
    "title": "text",
    "description": "text",
    "product_type": "text",
    "tags": "text",
    "price": "pricing",
    "sku": "ids",
    "barcode": "ids",
    "image_url": "images",
    "alt_text": "images",
}

REQUIRED_MAPPING_FIELDS = {
    "images": ["image_url"],
    "text": ["title"],
    "pricing": ["price"],
    "ids": ["sku"],
}


@dataclass
class StageAdmission:
    schema_ok: bool
    policy_ok: bool
    conflict_state: str
    eligible_to_apply: bool
    reasons: list[str]


def _product_to_stage_row(product: Product) -> dict[str, Any]:
    row = {
        "sku": product.sku,
        "barcode": product.barcode,
        "title": product.title,
        "description": product.description,
        "price": float(product.price) if product.price is not None else None,
        "image_url": product.images[0].src_url if product.images else None,
        "product_type": product.product_type,
        "tags": product.tags or [],
        "alt_text": product.images[0].alt_text if product.images else None,
    }
    return row


def _apply_block(row: dict[str, Any], block: BulkActionBlock) -> None:
    field = block.field_name
    operation = block.operation
    current = row.get(field)

    if operation in {"set", "replace"}:
        row[field] = block.value
        return
    if operation == "conditional_set":
        if current in (None, "", []):
            row[field] = block.value
        return
    if operation == "clear":
        row[field] = ""
        return
    if operation == "increase":
        row[field] = float(current or 0) + float(block.delta or 0)
        return
    if operation == "decrease":
        row[field] = float(current or 0) - float(block.delta or 0)
        return
    if operation in {"add", "remove"}:
        existing = current if isinstance(current, list) else ([current] if current else [])
        incoming = block.values if block.values is not None else ([block.value] if block.value is not None else [])
        normalized = [item for item in existing if item is not None]
        if operation == "add":
            for value in incoming:
                if value not in normalized:
                    normalized.append(value)
        else:
            normalized = [value for value in normalized if value not in incoming]
        row[field] = normalized


def _coerce_stage_rows(products: list[Product], blocks: list[BulkActionBlock]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for product in products:
        row = _product_to_stage_row(product)
        for block in blocks:
            _apply_block(row, block)
        # dry-run compiler expects at least one identity-ish value per row.
        if not any([row.get("sku"), row.get("barcode"), row.get("title")]):
            row["sku"] = product.sku or f"product-{product.id}"
        rows.append(row)
    return rows


def _evaluate_policy_guards(payload: BulkStageRequest) -> tuple[bool, list[str], str]:
    reasons: list[str] = []
    conflict_state = "none"

    for block in payload.action_blocks:
        if block.field_name in PROTECTED_FIELDS:
            reasons.append(f"Field '{block.field_name}' is protected and cannot be staged.")
            conflict_state = "blocked"
        if block.field_name not in SUPPORTED_MUTATION_FIELDS:
            reasons.append(f"Field '{block.field_name}' is not supported for staging.")
            conflict_state = "blocked"
        if block.field_name == "alt_text" and payload.alt_text_policy != "approved_overwrite":
            reasons.append("Alt-text overwrite requires alt_text_policy=approved_overwrite.")
            conflict_state = "blocked"

    policy_ok = len(reasons) == 0
    return policy_ok, reasons, conflict_state


def _mapping_gap_payload(
    *,
    store_id: int,
    supplier_code: str,
    field_groups: set[str],
    requested_mapping_version: int | None,
) -> tuple[list[dict[str, Any]], int | None]:
    mapping_gaps: list[dict[str, Any]] = []
    resolved_version: int | None = requested_mapping_version

    for field_group in field_groups:
        query = VendorFieldMapping.query.filter(
            VendorFieldMapping.store_id == store_id,
            func.lower(VendorFieldMapping.vendor_code) == supplier_code.lower(),
            VendorFieldMapping.field_group == field_group,
            VendorFieldMapping.is_active.is_(True),
        )
        if requested_mapping_version is not None:
            query = query.filter(VendorFieldMapping.mapping_version == requested_mapping_version)
        mapping = query.order_by(VendorFieldMapping.mapping_version.desc()).first()

        if mapping is None:
            mapping_gaps.append(
                {
                    "field_group": field_group,
                    "reason": "mapping_missing",
                    "required_fields": REQUIRED_MAPPING_FIELDS.get(field_group, []),
                }
            )
            continue

        if resolved_version is None:
            resolved_version = mapping.mapping_version

        if mapping.coverage_status != "ready":
            mapping_gaps.append(
                {
                    "field_group": field_group,
                    "reason": "mapping_not_ready",
                    "mapping_version": mapping.mapping_version,
                    "coverage_status": mapping.coverage_status,
                    "required_fields": mapping.required_fields or REQUIRED_MAPPING_FIELDS.get(field_group, []),
                }
            )

    return mapping_gaps, resolved_version


def _persist_stage_events(
    *,
    products: list[Product],
    staged_rows: list[dict[str, Any]],
    actor_user_id: int,
    store_id: int,
    batch_id: int,
) -> None:
    now = datetime.now(timezone.utc)
    for product, staged in zip(products, staged_rows):
        before_payload = _product_to_stage_row(product)
        changed_fields = [key for key in staged.keys() if before_payload.get(key) != staged.get(key)]
        if not changed_fields:
            continue

        diff_payload = {
            field: {
                "before": before_payload.get(field),
                "after": staged.get(field),
            }
            for field in changed_fields
        }
        event = ProductChangeEvent(
            product_id=product.id,
            store_id=store_id,
            actor_user_id=actor_user_id,
            source="workspace",
            event_type="bulk_stage",
            before_payload=before_payload,
            after_payload=staged,
            diff_payload=diff_payload,
            metadata_json={"changed_fields": changed_fields},
            resolution_batch_id=batch_id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(event)


def stage_bulk_actions(*, user_id: int, store_id: int, payload: BulkStageRequest) -> tuple[dict[str, Any], int]:
    """Compile semantic action blocks into a Phase-8 dry-run batch with admission metadata."""
    schema_ok = True
    policy_ok, policy_reasons, conflict_state = _evaluate_policy_guards(payload)

    field_groups = {FIELD_GROUP_BY_FIELD.get(block.field_name, "text") for block in payload.action_blocks}
    mapping_gaps, mapping_version = _mapping_gap_payload(
        store_id=store_id,
        supplier_code=payload.supplier_code,
        field_groups=field_groups,
        requested_mapping_version=payload.mapping_version,
    )

    if mapping_gaps:
        admission = StageAdmission(
            schema_ok=schema_ok,
            policy_ok=False,
            conflict_state="blocked",
            eligible_to_apply=False,
            reasons=policy_reasons + ["Vendor mapping gaps must be resolved before dry-run."],
        )
        return (
            {
                "type": "https://api.shopify-supplier.com/errors/vendor-mapping-incomplete",
                "title": "Vendor Mapping Incomplete",
                "status": 422,
                "detail": "Required vendor mappings are missing or not ready for this staging request.",
                "mapping_gaps": mapping_gaps,
                "admission": admission.__dict__,
                "remediation": {
                    "next_step": "Create or activate mapping versions for all listed field groups.",
                },
            },
            422,
        )

    if not policy_ok:
        admission = StageAdmission(
            schema_ok=schema_ok,
            policy_ok=False,
            conflict_state=conflict_state,
            eligible_to_apply=False,
            reasons=policy_reasons,
        )
        return (
            {
                "type": "https://api.shopify-supplier.com/errors/staging-policy-blocked",
                "title": "Staging Policy Blocked",
                "status": 422,
                "detail": "One or more action blocks violate staging policy.",
                "admission": admission.__dict__,
            },
            422,
        )

    selected_ids = payload.selection.selected_ids
    if not selected_ids:
        return (
            {
                "type": "https://api.shopify-supplier.com/errors/empty-selection",
                "title": "Empty Selection",
                "status": 422,
                "detail": "At least one selected product is required for staging.",
            },
            422,
        )

    products = (
        Product.query.filter(
            Product.store_id == store_id,
            Product.id.in_(selected_ids),
        )
        .order_by(Product.id.asc())
        .all()
    )
    if not products:
        return (
            {
                "type": "https://api.shopify-supplier.com/errors/selection-not-found",
                "title": "Selection Not Found",
                "status": 404,
                "detail": "No products were found for the provided selection snapshot.",
            },
            404,
        )

    staged_rows = _coerce_stage_rows(products, payload.action_blocks)
    batch = create_dry_run_batch_for_user(
        user_id=user_id,
        supplier_code=payload.supplier_code,
        supplier_verified=payload.supplier_verified,
        rows=staged_rows,
        apply_mode=payload.apply_mode,
        scheduled_for=payload.scheduled_for,
    )

    # Attach staging metadata on batch.
    batch.metadata_json = {
        **(batch.metadata_json or {}),
        "selection_snapshot": payload.selection.model_dump(),
        "action_blocks": [block.model_dump() for block in payload.action_blocks],
        "mapping_version": mapping_version or 1,
        "admission": {
            "schema_ok": True,
            "policy_ok": True,
            "conflict_state": "none",
            "eligible_to_apply": True,
        },
    }
    db.session.add(batch)

    _persist_stage_events(
        products=products,
        staged_rows=staged_rows,
        actor_user_id=user_id,
        store_id=store_id,
        batch_id=batch.id,
    )

    db.session.commit()

    response = {
        "batch_id": batch.id,
        "status": batch.status,
        "apply_mode": batch.apply_mode,
        "admission": {
            "schema_ok": True,
            "policy_ok": True,
            "conflict_state": "none",
            "eligible_to_apply": True,
            "reasons": [],
        },
        "mapping_version": mapping_version or 1,
        "action_blocks": [block.model_dump() for block in payload.action_blocks],
        "counts": {
            "selected_products": len(products),
            "staged_rows": len(staged_rows),
        },
    }
    return response, 201
