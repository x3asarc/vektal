"""
Find a Pentart product by barcode and update it with database data.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("API_VERSION", "2024-01")

TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"


class ShopifyClient:
    def __init__(self):
        self.access_token = None

    def authenticate(self):
        payload = {
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        response.raise_for_status()
        self.access_token = response.json().get("access_token")
        print("✓ Authenticated with Shopify")

    def execute_graphql(self, query, variables=None):
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        return response.json()

    def find_product_by_barcode(self, target_barcode):
        """Search all Pentart products for a specific barcode."""
        query = """
        query getPentart($cursor: String) {
          products(first: 50, query: "vendor:Pentart", after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                variants(first: 10) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """

        cursor = None
        products_checked = 0

        while True:
            result = self.execute_graphql(query, {"cursor": cursor})
            data = result.get("data", {}).get("products", {})

            for edge in data.get("edges", []):
                product = edge["node"]
                products_checked += 1

                for v_edge in product.get("variants", {}).get("edges", []):
                    variant = v_edge["node"]
                    if variant.get("barcode") == target_barcode:
                        return product, variant

            if products_checked % 100 == 0:
                print(f"  Searched {products_checked} products...")

            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info["endCursor"]

        return None, None

    def update_variant(self, product_id, variant_id, sku=None):
        """Update a variant. Note: weight must be set via inventoryItem, which requires different API."""
        mutation = """
        mutation updateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            userErrors {
              field
              message
            }
            productVariants {
              id
              sku
            }
          }
        }
        """

        # ProductVariantsBulkInput only supports limited fields
        # SKU cannot be updated after creation in many Shopify setups
        # Weight is part of inventoryItem, not variant directly
        variant_input = {"id": variant_id}

        # Try setting SKU using the ProductVariantsBulkInput
        # Note: This may fail if SKU is read-only
        if sku:
            variant_input["sku"] = str(sku)

        variables = {
            "productId": product_id,
            "variants": [variant_input]
        }

        return self.execute_graphql(mutation, variables)


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_and_update_by_barcode.py <barcode>")
        print("Example: python find_and_update_by_barcode.py 5997412761382")
        sys.exit(1)

    target_barcode = sys.argv[1]

    print("=" * 70)
    print("Find and Update Pentart Product by Barcode")
    print("=" * 70)
    print()

    # 1. Look up in database
    print(f"1. Looking up barcode {target_barcode} in database...")
    db = PentartDatabase(DB_PATH)
    db_product = db.get_by_ean(target_barcode)

    if not db_product:
        print(f"   ✗ Product not found in database")
        sys.exit(1)

    print(f"   ✓ Found: {db_product['description']}")
    print(f"   Article Number (SKU): {db_product.get('article_number')}")
    print(f"   Product Weight: {db_product.get('product_weight')} g")
    print()

    # 2. Authenticate
    print("2. Authenticating...")
    client = ShopifyClient()
    client.authenticate()
    print()

    # 3. Find in Shopify
    print(f"3. Searching all Pentart products for barcode {target_barcode}...")
    product, variant = client.find_product_by_barcode(target_barcode)

    if not product:
        print(f"   ✗ Product not found in Shopify")
        print(f"   The product may not exist or may have a different barcode")
        sys.exit(1)

    print(f"   ✓ Found: {product['title']}")
    print(f"   Current SKU: {variant.get('sku') or 'MISSING'}")
    print(f"   Current Barcode: {variant.get('barcode')}")
    print()

    # 4. Prepare updates
    print("4. Preparing updates...")

    new_sku = db_product.get('article_number')
    new_weight = db_product.get('product_weight')

    has_updates = False

    if new_sku and new_sku != variant.get('sku'):
        print(f"   SKU: {variant.get('sku') or 'MISSING'} → {new_sku}")
        has_updates = True

    if new_weight:
        print(f"   Weight: {new_weight} g (note: weight update requires separate API call)")
        # Note: Weight is stored in inventoryItem, not variant directly
        # This requires a different mutation (inventoryItemUpdate)

    if not has_updates:
        print("   No SKU update needed")
        return

    print()
    confirm = input("   Proceed with SKU update? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("   Cancelled")
        sys.exit(0)

    # 5. Apply update
    print()
    print("5. Updating product SKU...")
    result = client.update_variant(product['id'], variant['id'], sku=new_sku)

    if result:
        # Check for GraphQL errors first
        if "errors" in result:
            print("   ✗ GraphQL errors:")
            for error in result["errors"]:
                print(f"      - {error.get('message', str(error))}")
            sys.exit(1)

        user_errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])

        if user_errors:
            print("   ✗ Update failed:")
            for error in user_errors:
                print(f"      - {error['message']}")
            sys.exit(1)
        else:
            updated_variants = result["data"]["productVariantsBulkUpdate"]["productVariants"]
            if updated_variants:
                updated = updated_variants[0]
                print("   ✓ Successfully updated SKU!")
                print(f"   New SKU: {updated.get('sku')}")
                if new_weight:
                    print(f"\n   Note: Weight ({new_weight}g) must be updated separately via inventory API")

                # Trigger quality check after SKU update
                try:
                    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                    from orchestrator.trigger_quality_check import after_barcode_found
                    if updated.get('sku'):
                        after_barcode_found(updated.get('sku'))
                except Exception as e:
                    print(f"   [WARNING] Quality check trigger failed: {e}")

                print()
                print("=" * 70)
            else:
                print("   ✗ No variants were updated")
                sys.exit(1)
    else:
        print("   ✗ Update failed - no response")
        sys.exit(1)


if __name__ == "__main__":
    main()
