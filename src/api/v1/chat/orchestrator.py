"""Single-SKU chat orchestration helpers for dry-run-first workflows."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from src.api.v1.resolution.routes import create_dry_run_batch_for_user
from src.models.chat_session import ChatSession
from src.models.resolution_batch import ResolutionBatch
from src.resolution.shopify_graphql import resolve_publish_gate, resolve_variant_mutation_path


SKU_PATTERN = re.compile(r"\b([A-Z0-9][A-Z0-9-]{2,63})\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)
MUTATING_INTENTS = {"add_product", "update_product"}
SKU_STOPWORDS = {"ADD", "UPDATE", "PRODUCT", "SKU"}


class OrchestrationError(Exception):
    """Raised when orchestration constraints fail."""

    def __init__(
        self,
        *,
        error_type: str,
        title: str,
        detail: str,
        status: int,
        extensions: dict[str, Any] | None = None,
    ):
        super().__init__(detail)
        self.error_type = error_type
        self.title = title
        self.detail = detail
        self.status = status
        self.extensions = extensions or {}


@dataclass(frozen=True)
class PreparedSingleSkuAction:
    """Deterministic proposal result for one single-SKU mutating request."""

    action_type: str
    status: str
    payload_json: dict[str, Any]
    assistant_blocks: list[dict[str, Any]]


def is_mutating_intent(intent_type: str) -> bool:
    return intent_type in MUTATING_INTENTS


def _extract_sku(intent_entities: dict[str, Any], raw_message: str) -> str | None:
    entity_sku = intent_entities.get("sku")
    if entity_sku:
        candidate = str(entity_sku).upper().strip()
        if SKU_PATTERN.fullmatch(candidate) and candidate not in SKU_STOPWORDS and not candidate.startswith("-"):
            return candidate

    candidates = [
        match.group(1).upper()
        for match in SKU_PATTERN.finditer(raw_message or "")
    ]
    filtered = [
        token for token in candidates
        if token not in SKU_STOPWORDS and not token.startswith("-")
    ]
    if not filtered:
        return None
    return filtered[-1]


def _extract_url(raw_message: str) -> str | None:
    match = URL_PATTERN.search(raw_message or "")
    if not match:
        return None
    return match.group(1)


def extract_bulk_skus(*, action_hints: dict[str, Any] | None, raw_message: str) -> list[str]:
    """Extract deterministic multi-SKU candidates for bulk chat routing."""
    hints = action_hints or {}
    raw_skus = hints.get("skus")
    values: list[str] = []
    if isinstance(raw_skus, list):
        values.extend(str(item).upper().strip() for item in raw_skus)
    elif isinstance(raw_skus, str):
        values.extend(part.upper().strip() for part in raw_skus.split(","))
    else:
        values.extend(match.group(1).upper() for match in SKU_PATTERN.finditer(raw_message or ""))

    ordered: list[str] = []
    seen: set[str] = set()
    for candidate in values:
        if not candidate or candidate in seen:
            continue
        if not SKU_PATTERN.fullmatch(candidate):
            continue
        if candidate in SKU_STOPWORDS or candidate.startswith("-"):
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def _normalize_variants(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(raw, list):
        return [str(part).strip() for part in raw if str(part).strip()]
    return []


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_input_row(
    *,
    operation: str,
    sku: str,
    raw_message: str,
    action_hints: dict[str, Any],
    route_response: dict[str, Any],
) -> dict[str, Any]:
    title = (
        action_hints.get("title")
        or route_response.get("product", {}).get("title")
        or route_response.get("current_data", {}).get("title")
        or f"Chat {sku}"
    )
    row: dict[str, Any] = {
        "sku": sku,
        "title": title,
        "description": action_hints.get("description") or f"Chat proposal for {sku}.",
        "variant_options": _normalize_variants(action_hints.get("variant_options")),
    }
    if "price" in action_hints:
        row["price"] = _as_float(action_hints.get("price"))
    if operation == "create":
        row["product_type"] = action_hints.get("product_type") or "Draft"
    source_url = _extract_url(raw_message)
    if source_url:
        row["source_url"] = source_url
    return row


def _collect_batch_preview(batch: ResolutionBatch) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    conflict_item_ids: list[int] = []
    low_confidence_change_ids: list[int] = []

    for item in batch.items.order_by("id").all():
        if item.status == "structural_conflict":
            conflict_item_ids.append(item.id)
        group = {
            "item_id": item.id,
            "status": item.status,
            "product_label": item.product_label,
            "structural_state": item.structural_state,
            "conflict_reason": item.conflict_reason,
            "changes": [],
        }
        for change in item.changes.order_by("id").all():
            confidence = _as_float(change.confidence_score)
            if confidence is not None and confidence < 0.6:
                low_confidence_change_ids.append(change.id)
            group["changes"].append(
                {
                    "change_id": change.id,
                    "field_name": change.field_name,
                    "status": change.status,
                    "before_value": change.before_value,
                    "after_value": change.after_value,
                    "confidence_score": confidence,
                    "reason_sentence": change.reason_sentence,
                }
            )
        groups.append(group)

    return {
        "groups": groups,
        "conflict_item_ids": conflict_item_ids,
        "low_confidence_change_ids": low_confidence_change_ids,
    }


def prepare_single_sku_action(
    *,
    session: ChatSession,
    intent_type: str,
    intent_entities: dict[str, Any],
    route_response: dict[str, Any] | None,
    raw_message: str,
    action_hints: dict[str, Any] | None,
    actor_user_id: int,
) -> PreparedSingleSkuAction:
    """
    Build dry-run-first proposal for a single-SKU mutating action.
    """
    if not is_mutating_intent(intent_type):
        raise OrchestrationError(
            error_type="unsupported-intent",
            title="Unsupported Intent",
            detail="Only single-SKU mutating intents are supported by this orchestrator.",
            status=422,
        )

    if session.store_id is None:
        raise OrchestrationError(
            error_type="store-not-connected",
            title="Store Not Connected",
            detail="Connect a Shopify store before preparing mutating chat actions.",
            status=409,
        )

    sku = _extract_sku(intent_entities, raw_message)
    if not sku:
        raise OrchestrationError(
            error_type="missing-sku",
            title="Missing SKU",
            detail="A SKU is required for single-SKU mutating chat actions.",
            status=422,
        )

    hints = action_hints or {}
    operation = "create" if intent_type == "add_product" else "update"
    variant_strategy = str(hints.get("variant_strategy") or "ask")
    publish_semantics = resolve_publish_gate(
        publish_requested=bool(hints.get("publish_requested", False)),
        publish_policy=str(hints.get("publish_policy") or "explicit"),
    )

    row = _build_input_row(
        operation=operation,
        sku=sku,
        raw_message=raw_message,
        action_hints=hints,
        route_response=route_response or {},
    )
    batch = create_dry_run_batch_for_user(
        user_id=actor_user_id,
        supplier_code=str(hints.get("supplier_code") or "CHAT"),
        supplier_verified=bool(hints.get("supplier_verified", False)),
        rows=[row],
        apply_mode="immediate",
        scheduled_for=None,
    )
    preview = _collect_batch_preview(batch)
    variant_options = _normalize_variants(hints.get("variant_options"))
    variant_mutation_path = resolve_variant_mutation_path(max(len(variant_options), 1))
    source_url = _extract_url(raw_message)

    requires_user_decision = bool(preview["conflict_item_ids"] or preview["low_confidence_change_ids"])
    payload_json = {
        "dry_run_required": True,
        "dry_run_id": batch.id,
        "operation": operation,
        "sku": sku,
        "source_url": source_url,
        "approval_scope": "product",
        "requires_product_approval": True,
        "variant_strategy": variant_strategy,
        "variant_mutation_path": variant_mutation_path,
        "create_defaults": {
            **publish_semantics,
            "default_status": "draft",
        },
        "preview": preview,
        "requires_user_decision": requires_user_decision,
        "decision_reasons": {
            "conflict_item_ids": preview["conflict_item_ids"],
            "low_confidence_change_ids": preview["low_confidence_change_ids"],
        },
    }

    assistant_blocks = [
        {
            "type": "diff",
            "title": "dry_run_preview",
            "data": {
                "dry_run_id": batch.id,
                "operation": operation,
                "groups": preview["groups"],
            },
        },
        {
            "type": "action",
            "title": "product_scope_approval",
            "data": {
                "approval_scope": "product",
                "dry_run_required": True,
                "requires_user_decision": requires_user_decision,
                "next": ["approve", "apply"],
            },
        },
    ]
    if operation == "create":
        assistant_blocks.append(
            {
                "type": "text",
                "text": "Create flow defaults to draft-first. Publishing remains explicit/policy-gated.",
            }
        )
    if variant_mutation_path == "productVariantsBulkCreate":
        assistant_blocks.append(
            {
                "type": "text",
                "text": "Additional variants will use productVariantsBulkCreate.",
            }
        )

    return PreparedSingleSkuAction(
        action_type=intent_type,
        status="dry_run_ready",
        payload_json=payload_json,
        assistant_blocks=assistant_blocks,
    )
