"""Shopify GraphQL adapters for Phase 8 apply and media workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from src.models.shopify import ShopifyStore
from src.resolution.throttle import ThrottleSignal, parse_throttle_signal


@dataclass(frozen=True)
class MutationResult:
    success: bool
    payload: dict[str, Any]
    throttle: ThrottleSignal | None
    user_errors: list[dict[str, Any]]


class ShopifyGraphQLClient:
    """Thin GraphQL wrapper with explicit mutation helpers."""

    def __init__(
        self,
        *,
        store: ShopifyStore | None = None,
        shop_domain: str | None = None,
        access_token: str | None = None,
        api_version: str = "2026-01",
        session: requests.Session | None = None,
    ):
        if store is None and (shop_domain is None or access_token is None):
            raise ValueError("Provide either store or explicit shop_domain + access_token.")

        self.store = store
        self.shop_domain = shop_domain or (store.shop_domain if store else None)
        if self.shop_domain is None:
            raise ValueError("Missing Shopify shop domain.")

        if access_token:
            self.access_token = access_token
        elif store is not None:
            self.access_token = store.get_access_token()
        else:
            raise ValueError("Missing Shopify access token.")

        self.api_version = api_version
        self.endpoint = f"https://{self.shop_domain}/admin/api/{api_version}/graphql.json"
        self.session = session or requests.Session()

    def execute(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> MutationResult:
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token,
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        response = self.session.post(
            self.endpoint,
            json={"query": query, "variables": variables or {}},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        throttle = parse_throttle_signal(
            graphql_payload=payload,
            response_headers=dict(response.headers),
        )
        user_errors = _collect_user_errors(payload)
        return MutationResult(
            success=len(user_errors) == 0 and "errors" not in payload,
            payload=payload,
            throttle=throttle,
            user_errors=user_errors,
        )

    def product_set(self, *, product_input: dict[str, Any], synchronous: bool = False, idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation productSet($input: ProductSetInput!, $synchronous: Boolean!) {
          productSet(input: $input, synchronous: $synchronous) {
            product { id }
            productSetOperation { id status }
            userErrors { field message }
          }
        }
        """
        return self.execute(
            mutation,
            {"input": product_input, "synchronous": synchronous},
            idempotency_key=idempotency_key,
        )

    def product_variants_bulk_create(self, *, product_id: str, variants: list[dict[str, Any]], idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkCreate(productId: $productId, variants: $variants) {
            product { id }
            userErrors { field message }
          }
        }
        """
        return self.execute(
            mutation,
            {"productId": product_id, "variants": variants},
            idempotency_key=idempotency_key,
        )

    def product_variants_bulk_update(self, *, product_id: str, variants: list[dict[str, Any]], idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            product { id }
            userErrors { field message }
          }
        }
        """
        return self.execute(
            mutation,
            {"productId": product_id, "variants": variants},
            idempotency_key=idempotency_key,
        )

    def inventory_set_quantities(self, *, input_data: dict[str, Any], idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation inventorySetQuantities($input: InventorySetQuantitiesInput!) {
          inventorySetQuantities(input: $input) {
            userErrors { field message }
          }
        }
        """
        return self.execute(
            mutation,
            {"input": input_data},
            idempotency_key=idempotency_key,
        )

    def product_operation(self, *, operation_id: str) -> MutationResult:
        query = """
        query productOperation($id: ID!) {
          productOperation(id: $id) {
            id
            status
            userErrors { field message }
          }
        }
        """
        return self.execute(query, {"id": operation_id})

    def staged_uploads_create(self, *, inputs: list[dict[str, Any]], idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters { name value }
            }
            userErrors { field message }
          }
        }
        """
        return self.execute(
            mutation,
            {"input": inputs},
            idempotency_key=idempotency_key,
        )

    def file_create(self, *, files: list[dict[str, Any]], idempotency_key: str | None = None) -> MutationResult:
        mutation = """
        mutation fileCreate($files: [FileCreateInput!]!) {
          fileCreate(files: $files) {
            files {
              id
              fileStatus
            }
            userErrors { field message }
          }
        }
        """
        return self.execute(mutation, {"files": files}, idempotency_key=idempotency_key)

    def file_status(self, *, file_id: str) -> MutationResult:
        query = """
        query fileStatus($id: ID!) {
          node(id: $id) {
            ... on File {
              id
              fileStatus
            }
          }
        }
        """
        return self.execute(query, {"id": file_id})

    def attach_media_to_product(
        self,
        *,
        product_id: str,
        file_reference: str,
        alt_text: str | None = None,
        idempotency_key: str | None = None,
    ) -> MutationResult:
        mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
          productCreateMedia(productId: $productId, media: $media) {
            media { id }
            userErrors { field message }
          }
        }
        """
        media_input: dict[str, Any] = {
            "mediaContentType": "IMAGE",
            "originalSource": file_reference,
        }
        if alt_text:
            media_input["alt"] = alt_text
        return self.execute(
            mutation,
            {"productId": product_id, "media": [media_input]},
            idempotency_key=idempotency_key,
        )


def resolve_publish_gate(
    *,
    publish_requested: bool,
    publish_policy: str | None = None,
) -> dict[str, Any]:
    """
    Resolve draft-first create semantics.

    Publish is never implicit. It is only allowed when explicitly requested and policy allows it.
    """
    policy = (publish_policy or "explicit").strip().lower()
    publish_allowed = publish_requested and policy in {"explicit_allow", "policy_allow"}
    return {
        "draft_first": True,
        "publish_policy": policy or "explicit",
        "publish_requested": bool(publish_requested),
        "publish_allowed": bool(publish_allowed),
    }


def resolve_variant_mutation_path(variant_count: int) -> str:
    """
    Route multi-variant operations to dedicated bulk variant mutation path.
    """
    if variant_count > 1:
        return "productVariantsBulkCreate"
    return "productCreate.initial_variant_only"


def _collect_user_errors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    user_errors: list[dict[str, Any]] = []
    for value in data.values():
        if not isinstance(value, dict):
            continue
        errors = value.get("userErrors")
        if isinstance(errors, list):
            user_errors.extend(error for error in errors if isinstance(error, dict))
    return user_errors
