"""
Update a Pentart product by barcode with data from the database.
Standalone script with minimal dependencies.
"""

import sys
import os
import requests
from dotenv import load_dotenv

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH

load_dotenv()

# Shopify configuration
SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("API_VERSION", "2024-01")

TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"


class ShopifyClient:
    """Minimal Shopify client for updating products."""

    def __init__(self):
        self.access_token = None

    def authenticate(self):
        """Authenticate with Shopify."""
        payload = {
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        response.raise_for_status()
        self.access_token = response.json().get("access_token")

    def execute_graphql(self, query, variables=None):
        """Execute GraphQL query."""
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        return response.json()

    def find_product_by_barcode(self, barcode):
        """Find product by barcode."""
        query = """
        query getPentart($cursor: String) {
          products(first: 250, query: "vendor:Pentart", after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                variants(first: 5) {
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
        checked = 0

        while True:
            result = self.execute_graphql(query, {"cursor": cursor})

            if "errors" in result:
                print(f"GraphQL errors: {result['errors']}")
                return None, None

            data = result.get("data", {}).get("products", {})

            for edge in data.get("edges", []):
                product = edge["node"]
                checked += 1

                for v_edge in product.get("variants", {}).get("edges", []):
                    variant = v_edge["node"]
                    if variant.get("barcode") == barcode:
                        return product, variant

            if checked % 250 == 0:
                print(f"  Searched {checked} products...")

            if not data.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = data["pageInfo"]["endCursor"]

        return None, None

    def update_product_variants(self, product_id, variant_updates):
        """Update product variants."""
        mutation = """
        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            product {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "variants": variant_updates
        }
        return self.execute_graphql(mutation, variables)


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_barcode_product.py <barcode>")
        print("Example: python update_barcode_product.py 5997412761382")
        sys.exit(1)

    barcode = sys.argv[1]

    print("=" * 70)
    print("Update Pentart Product from Database")
    print("=" * 70)
    print()

    # 1. Look up in database
    print(f"1. Looking up barcode {barcode} in database...")
    db = PentartDatabase(DB_PATH)
    db_product = db.get_by_ean(barcode)

    if not db_product:
        print(f"   ✗ Product not found in database")
        sys.exit(1)

    print(f"   ✓ Found: {db_product['description']}")
    print(f"   SKU: {db_product.get('article_number')}")
    print(f"   Weight: {db_product.get('product_weight')} g")
    print()

    # 2. Authenticate
    print("2. Authenticating with Shopify...")
    client = ShopifyClient()
    client.authenticate()
    print("   ✓ Authenticated")
    print()

    # 3. Find in Shopify
    print(f"3. Searching for product with barcode {barcode}...")
    product, variant = client.find_product_by_barcode(barcode)

    if not product:
        print("   ✗ Product not found in Shopify")
        sys.exit(1)

    print(f"   ✓ Found: {product['title']}")
    print(f"   Current SKU: {variant.get('sku') or 'MISSING'}")
    print(f"   Current Barcode: {variant.get('barcode')}")
    print()

    # 4. Prepare updates
    print("4. Preparing updates...")
    variant_update = {"id": variant["id"]}

    new_sku = db_product.get('article_number')
    new_weight = db_product.get('product_weight')

    updates_text = []

    # Note: SKU cannot be set via ProductVariantsBulkInput after creation
    # Barcode can be updated though
    # Weight goes in inventoryItem nested object

    if new_weight:
        # Add inventoryItem with nested fields like app.py does
        inventory_item = {}
        inventory_item["countryCodeOfOrigin"] = "HU"  # Hungary for Pentart
        # Note: weight is NOT in inventoryItem either!
        variant_update["inventoryItem"] = inventory_item
        updates_text.append(f"Country → HU")

    # The productVariantsBulkUpdate mutation does NOT support:
    # - sku (read-only after creation)
    # - weight (must use REST API or set at creation)
    # Only barcode and inventoryItem (for cost, country, HS code)

    if len(updates_text) == 0:
        print("   No updates needed")
        return

    for text in updates_text:
        print(f"   {text}")

    print()
    confirm = input("   Proceed with update? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("   Cancelled")
        sys.exit(0)

    # 5. Update
    print()
    print("5. Updating product...")
    result = client.update_product_variants(product["id"], [variant_update])

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

    print("   ✓ Successfully updated!")
    print()
    print("   Product now has:")
    if new_sku:
        print(f"     SKU: {new_sku}")
    if new_weight:
        print(f"     Weight: {new_weight} g")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
