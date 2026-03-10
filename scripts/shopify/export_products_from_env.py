"""Export all Shopify products using API credentials from .env."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


GRAPHQL_QUERY = """
query FetchProducts($first: Int!, $after: String, $query: String) {
  products(first: $first, after: $after, query: $query) {
    nodes {
      id
      handle
      title
      status
      vendor
      productType
      tags
      createdAt
      updatedAt
      totalInventory
      variants(first: 100) {
        nodes {
          id
          sku
          barcode
          price
          inventoryQuantity
          title
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""


def _resolve_token_from_env() -> tuple[str | None, str | None]:
    # Canonical token env names.
    primary_token_keys = [
        "SHOPIFY_ACCESS_TOKEN",
        "SHOPIFY_ADMIN_API_ACCESS_TOKEN",
        "SHOPIFY_API_TOKEN",
        "SHOPIFY_TOKEN",
    ]
    for key in primary_token_keys:
        value = os.getenv(key)
        if value:
            return key, value

    # Legacy fallback names, but skip known app-secret format (shpss_*) to avoid false positives.
    legacy_keys = [
        "SHOPIFY_API_SECRET",
        "SHOPIFY_CLIENT_SECRET",
        "PREV_SHOPIFY_API_SECRET",
        "PREV_SHOPIFY_CLIENT_SECRET",
    ]
    for key in legacy_keys:
        value = os.getenv(key)
        if value and not value.startswith("shpss_"):
            return key, value
    return None, None


def _resolve_token_from_db() -> tuple[str | None, str | None, str | None]:
    """
    Return (source_key, access_token, shop_domain) from latest active shopify_stores row.
    """
    try:
        from sqlalchemy import inspect

        from src.database import create_app
        from src.models import db
        from src.models.shopify import ShopifyStore
    except Exception:
        return None, None, None

    try:
        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            if "shopify_stores" not in inspector.get_table_names():
                return None, None, None

            store = (
                ShopifyStore.query.filter_by(is_active=True)
                .order_by(ShopifyStore.id.desc())
                .first()
            )
            if not store:
                return None, None, None
            return "DB_SHOPIFY_STORE_TOKEN", store.get_access_token(), store.shop_domain
    except Exception:
        return None, None, None


def _fetch_all_products(
    *,
    shop_domain: str,
    api_version: str,
    access_token: str,
    page_size: int,
    query: str | None,
) -> list[dict]:
    endpoint = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }

    all_products: list[dict] = []
    after: str | None = None
    page = 0

    while True:
        variables = {"first": page_size, "after": after, "query": query}
        response = requests.post(
            endpoint,
            json={"query": GRAPHQL_QUERY, "variables": variables},
            headers=headers,
            timeout=30,
        )

        if response.status_code >= 400:
            snippet = response.text.replace("\n", " ").strip()[:220]
            raise RuntimeError(f"Shopify request failed ({response.status_code}): {snippet}")

        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL errors: {json.dumps(payload['errors'])[:220]}")

        products_node = ((payload.get("data") or {}).get("products") or {})
        nodes = products_node.get("nodes") or []
        page_info = products_node.get("pageInfo") or {}

        all_products.extend(nodes)
        page += 1
        print(f"Fetched page {page}: +{len(nodes)} products (total {len(all_products)})")

        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not after:
            break

    return all_products


def main() -> int:
    parser = argparse.ArgumentParser(description="Export all Shopify products to JSON using .env credentials.")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON file path.")
    parser.add_argument("--page-size", type=int, default=250, help="Products per page (max 250).")
    parser.add_argument("--query", type=str, default=None, help="Optional Shopify product search query.")
    parser.add_argument(
        "--token-source",
        choices=["auto", "env", "db"],
        default="auto",
        help="Where to get Shopify access token from (default: auto).",
    )
    args = parser.parse_args()

    load_dotenv(".env")

    shop_domain = os.getenv("SHOP_DOMAIN")
    api_version = os.getenv("API_VERSION", "2024-01")

    token_source: str | None = None
    access_token: str | None = None

    if args.token_source in {"auto", "env"}:
        token_source, access_token = _resolve_token_from_env()

    if not access_token and args.token_source in {"auto", "db"}:
        db_source, db_token, db_domain = _resolve_token_from_db()
        if db_token:
            token_source = db_source
            access_token = db_token
            if not shop_domain and db_domain:
                shop_domain = db_domain

    if not shop_domain:
        print("Missing SHOP_DOMAIN in .env", file=sys.stderr)
        return 1
    if not access_token:
        print(
            "Missing Shopify access token. Set SHOPIFY_ACCESS_TOKEN in .env or ensure shopify_stores has a token.",
            file=sys.stderr,
        )
        return 1

    page_size = max(1, min(250, int(args.page_size)))

    try:
        products = _fetch_all_products(
            shop_domain=shop_domain,
            api_version=api_version,
            access_token=access_token,
            page_size=page_size,
            query=args.query,
        )
    except Exception as exc:
        print(f"Failed to export Shopify products: {exc}", file=sys.stderr)
        if token_source and token_source not in {
            "SHOPIFY_ACCESS_TOKEN",
            "SHOPIFY_ADMIN_API_ACCESS_TOKEN",
            "SHOPIFY_API_TOKEN",
            "SHOPIFY_TOKEN",
            "DB_SHOPIFY_STORE_TOKEN",
        }:
            print(
                "Current token source is not a dedicated access token variable. "
                "Use SHOPIFY_ACCESS_TOKEN if available.",
                file=sys.stderr,
            )
        return 2

    if args.output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = Path("results") / f"shopify_products_{stamp}.json"
    else:
        output_path = args.output

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "shop_domain": shop_domain,
        "api_version": api_version,
        "query": args.query,
        "count": len(products),
        "products": products,
    }
    output_path.write_text(json.dumps(output_payload, indent=2), encoding="utf-8")

    print(f"Exported {len(products)} products to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
