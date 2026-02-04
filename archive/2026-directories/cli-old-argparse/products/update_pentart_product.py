"""
Update a specific Pentart product with database data.
Based on working check_product.py authentication.
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
        try:
            response = requests.post(TOKEN_ENDPOINT, json=payload)
            response.raise_for_status()
            self.access_token = response.json().get("access_token")
            print("✓ Successfully authenticated with Shopify")
        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            raise

    def execute_graphql(self, query, variables=None):
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        return response.json()

    def search_product_by_title(self, search_term):
        """Search products by title."""
        query = """
        query getProductByTitle($query: String!) {
          products(first: 10, query: $query) {
            edges {
              node {
                id
                title
                vendor
                variants(first: 5) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                      weight
                      weightUnit
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.execute_graphql(query, {"query": f"title:*{search_term}*"})
        return result.get("data", {}).get("products", {}).get("edges", [])

    def update_variant(self, product_id, variant_id, sku, barcode, weight_grams):
        """Update a variant with new SKU, barcode, and weight."""
        mutation = """
        mutation updateVariant($productId: ID!, $variant: ProductVariantsBulkInput!) {
          productVariantsBulkUpdate(productId: $productId, variants: [$variant]) {
            userErrors {
              field
              message
            }
            productVariants {
              id
              sku
              barcode
              weight
              weightUnit
            }
          }
        }
        """

        variant_input = {
            "id": variant_id
        }

        if sku:
            variant_input["sku"] = str(sku)
        if barcode:
            variant_input["barcode"] = str(barcode)
        if weight_grams:
            variant_input["weight"] = float(weight_grams)
            variant_input["weightUnit"] = "GRAMS"

        variables = {
            "productId": product_id,
            "variant": variant_input
        }

        return self.execute_graphql(mutation, variables)


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_pentart_product.py <barcode>")
        print("Example: python update_pentart_product.py 5997412761382")
        sys.exit(1)

    target_barcode = sys.argv[1]

    print("=" * 70)
    print("Update Pentart Product from Database")
    print("=" * 70)
    print()

    # 1. Look up in database
    print(f"1. Looking up barcode {target_barcode} in Pentart database...")
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
    print("2. Authenticating with Shopify...")
    client = ShopifyClient()
    client.authenticate()
    print()

    # 3. Search for product by title keywords
    print("3. Searching for product in Shopify...")
    # Extract a search term from the description
    desc_words = db_product['description'].split()
    search_term = " ".join(desc_words[:3])  # First 3 words
    print(f"   Searching for: {search_term}")

    products = client.search_product_by_title(search_term)

    if not products:
        print("   ✗ No products found matching description")
        print("   Try searching manually in Shopify admin")
        sys.exit(1)

    print(f"   ✓ Found {len(products)} matching products:")
    print()

    # Show matches and ask user to select
    for idx, edge in enumerate(products, 1):
        product = edge["node"]
        variant = product["variants"]["edges"][0]["node"] if product["variants"]["edges"] else None

        print(f"   {idx}. {product['title']}")
        if variant:
            print(f"      Current SKU: {variant.get('sku') or 'MISSING'}")
            print(f"      Current Barcode: {variant.get('barcode') or 'MISSING'}")
            print(f"      Current Weight: {variant.get('weight')} {variant.get('weightUnit', '')}")
        print()

    # Let user choose
    if len(products) == 1:
        choice = 1
        print(f"   Auto-selecting the only match")
    else:
        choice_input = input(f"   Select product number (1-{len(products)}) or 'q' to quit: ").strip()
        if choice_input.lower() == 'q':
            print("   Cancelled")
            sys.exit(0)

        try:
            choice = int(choice_input)
            if choice < 1 or choice > len(products):
                print("   Invalid choice")
                sys.exit(1)
        except ValueError:
            print("   Invalid input")
            sys.exit(1)

    selected_product = products[choice - 1]["node"]
    selected_variant = selected_product["variants"]["edges"][0]["node"]

    print()
    print(f"4. Updating product: {selected_product['title']}")
    print()

    # Prepare updates
    new_sku = db_product.get('article_number')
    new_barcode = db_product.get('ean')
    new_weight = db_product.get('product_weight')

    print("   Updates to apply:")
    if new_sku:
        print(f"     SKU: {selected_variant.get('sku') or 'MISSING'} → {new_sku}")
    if new_barcode:
        print(f"     Barcode: {selected_variant.get('barcode') or 'MISSING'} → {new_barcode}")
    if new_weight:
        print(f"     Weight: {selected_variant.get('weight')} → {new_weight} g")
    print()

    confirm = input("   Proceed with update? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("   Cancelled")
        sys.exit(0)

    # 5. Apply update
    print()
    print("5. Applying updates...")
    result = client.update_variant(
        selected_product['id'],
        selected_variant['id'],
        new_sku,
        new_barcode,
        new_weight
    )

    if result:
        user_errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])

        if user_errors:
            print("   ✗ Update failed:")
            for error in user_errors:
                print(f"      - {error['message']}")
            sys.exit(1)
        else:
            updated = result["data"]["productVariantsBulkUpdate"]["productVariants"][0]
            print("   ✓ Successfully updated!")
            print(f"   SKU: {updated['sku']}")
            print(f"   Barcode: {updated['barcode']}")
            print(f"   Weight: {updated['weight']} {updated['weightUnit']}")
            print()
            print("=" * 70)
    else:
        print("   ✗ Update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
