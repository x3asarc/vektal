"""
Bulk update Pentart products in Shopify with SKU, barcode, and weight from database.

This script:
1. Queries all Pentart products from Shopify
2. Checks database for matching products
3. Updates missing SKUs, barcodes, and weights
4. Generates a report of updates

Usage:
    python scripts/bulk_update_pentart_shopify.py [--dry-run]
"""

import os
import sys
import time
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# Shopify credentials
SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("API_VERSION", "2024-01")

TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"


class ShopifyPentartUpdater:
    """Client for updating Pentart products in Shopify."""

    def __init__(self):
        self.access_token = None
        self.pentart_db = PentartDatabase(DB_PATH)

    def authenticate(self):
        """Authenticate with Shopify."""
        payload = {
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        try:
            response = requests.post(TOKEN_ENDPOINT, json=payload)
            response.raise_for_status()
            self.access_token = response.json().get("access_token")
            print("Successfully authenticated with Shopify.")
        except Exception as e:
            print(f"Authentication failed: {e}")
            raise

    def execute_graphql(self, query, variables=None):
        """Execute a GraphQL query."""
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        try:
            response = requests.post(
                GRAPHQL_ENDPOINT,
                json={"query": query, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  GraphQL Request Failed: {e}")
            return None

    def get_pentart_products(self):
        """Query all Pentart products from Shopify."""
        query = """
        query getPentartProducts($cursor: String) {
          products(first: 50, query: "vendor:Pentart", after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                vendor
                variants(first: 10) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                      weight
                      weightUnit
                      inventoryItem { id }
                    }
                  }
                }
              }
            }
          }
        }
        """

        all_products = []
        cursor = None
        has_next_page = True

        print("Fetching Pentart products from Shopify...")

        while has_next_page:
            result = self.execute_graphql(query, {"cursor": cursor})

            if not result or "data" not in result:
                print("Error fetching products")
                break

            products_data = result["data"]["products"]
            edges = products_data.get("edges", [])

            for edge in edges:
                product = edge["node"]
                all_products.append(product)

            page_info = products_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            print(f"  Fetched {len(all_products)} products so far...")

        print(f"Total Pentart products found: {len(all_products)}")
        return all_products

    def update_variant(self, product_id, variant_id, inv_item_id, updates):
        """Update a product variant with new data."""
        mutation = """
        mutation updateVariant($productId: ID!, $variant: ProductVariantsBulkInput!) {
          productVariantsBulkUpdate(productId: $productId, variants: [$variant]) {
            userErrors {
              field
              message
            }
            productVariants {
              id
            }
          }
        }
        """

        variant_input = {"id": variant_id}

        # Add SKU if provided
        if "sku" in updates:
            variant_input["sku"] = str(updates["sku"])

        # Add barcode if provided
        if "barcode" in updates:
            variant_input["barcode"] = str(updates["barcode"])

        # Add weight if provided
        if "weight" in updates:
            variant_input["weight"] = float(updates["weight"])
            variant_input["weightUnit"] = "GRAMS"

        variables = {
            "productId": product_id,
            "variant": variant_input
        }

        return self.execute_graphql(mutation, variables)

    def process_product(self, product, dry_run=False):
        """
        Process a single product - check database and update if needed.

        Returns: dict with update statistics
        """
        product_id = product["id"]
        product_title = product["title"]
        variants = product.get("variants", {}).get("edges", [])

        if not variants:
            return {"status": "no_variants", "message": "No variants found"}

        # Process first variant (most Pentart products have single variant)
        variant_node = variants[0]["node"]
        variant_id = variant_node["id"]
        current_sku = variant_node.get("sku")
        current_barcode = variant_node.get("barcode")
        current_weight = variant_node.get("weight")
        inv_item_id = variant_node.get("inventoryItem", {}).get("id")

        # Check what's missing
        missing_items = []
        if not current_barcode:
            missing_items.append("barcode")
        if not current_weight or current_weight == 0:
            missing_items.append("weight")

        if not missing_items:
            return {"status": "complete", "message": "All data present"}

        # Try to find product in database
        db_product = None

        # First try by SKU (article number)
        if current_sku:
            db_product = self.pentart_db.get_by_article_number(current_sku)

        # If not found, try by barcode
        if not db_product and current_barcode:
            db_product = self.pentart_db.get_by_ean(current_barcode)

        # If not found, try by title search
        if not db_product:
            results = self.pentart_db.search_by_description(product_title[:50])
            if results:
                db_product = results[0]  # Take first match

        if not db_product:
            return {
                "status": "not_found",
                "message": "Product not found in database",
                "missing": missing_items
            }

        # Prepare updates
        updates = {}

        if not current_barcode and db_product.get("ean"):
            updates["barcode"] = db_product["ean"]

        if (not current_weight or current_weight == 0) and db_product.get("product_weight"):
            updates["weight"] = db_product["product_weight"]

        if not updates:
            return {
                "status": "no_updates",
                "message": "Database has no additional data",
                "missing": missing_items
            }

        # Apply updates
        if dry_run:
            return {
                "status": "dry_run",
                "message": "Would update: " + ", ".join(updates.keys()),
                "updates": updates
            }

        result = self.update_variant(product_id, variant_id, inv_item_id, updates)

        if result and "data" in result:
            user_errors = result["data"]["productVariantsBulkUpdate"].get("userErrors", [])
            if user_errors:
                return {
                    "status": "error",
                    "message": "; ".join([e["message"] for e in user_errors]),
                    "updates": updates
                }
            else:
                return {
                    "status": "success",
                    "message": "Updated: " + ", ".join(updates.keys()),
                    "updates": updates
                }
        else:
            return {
                "status": "error",
                "message": "GraphQL request failed",
                "updates": updates
            }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bulk update Pentart products in Shopify with database data"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("Pentart Product Bulk Update Tool")
    print("=" * 70)

    if args.dry_run:
        print("MODE: DRY RUN (no changes will be made)")
        print()

    # Initialize
    updater = ShopifyPentartUpdater()
    updater.authenticate()

    # Get all Pentart products
    products = updater.get_pentart_products()

    if not products:
        print("No Pentart products found in Shopify.")
        return

    # Statistics
    stats = {
        "total": len(products),
        "complete": 0,
        "success": 0,
        "not_found": 0,
        "no_updates": 0,
        "error": 0,
        "no_variants": 0,
        "dry_run": 0
    }

    # Process each product
    print("\nProcessing products...")
    print("-" * 70)

    for idx, product in enumerate(products, 1):
        title = product["title"][:50]
        print(f"\n[{idx}/{len(products)}] {title}")

        result = updater.process_product(product, dry_run=args.dry_run)
        status = result["status"]
        message = result["message"]

        stats[status] = stats.get(status, 0) + 1

        # Status symbols
        symbol = "✓" if status == "success" else "•"
        if status == "error":
            symbol = "✗"
        elif status == "dry_run":
            symbol = "○"

        print(f"  {symbol} {message}")

        if "updates" in result:
            for key, value in result["updates"].items():
                print(f"    - {key}: {value}")

        # Rate limiting
        if not args.dry_run and status in ["success", "error"]:
            time.sleep(0.5)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total products:           {stats['total']}")
    print(f"Already complete:         {stats['complete']}")
    print(f"Successfully updated:     {stats['success']}")
    print(f"Not found in database:    {stats['not_found']}")
    print(f"No additional data:       {stats['no_updates']}")
    print(f"Errors:                   {stats['error']}")
    print(f"No variants:              {stats['no_variants']}")

    if args.dry_run:
        print(f"Would update:             {stats['dry_run']}")
        print("\nRun without --dry-run to apply changes.")

    print("=" * 70)


if __name__ == "__main__":
    main()
