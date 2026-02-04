"""
Update Pentart product using Shopify REST API (not GraphQL).
REST API supports updating SKU and weight that GraphQL doesn't.
"""

import sys
import os
import requests
from dotenv import load_dotenv
import re

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
REST_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}"


def authenticate():
    """Get access token."""
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TOKEN_ENDPOINT, json=payload)
    response.raise_for_status()
    return response.json().get("access_token")


def graphql_find_by_barcode(access_token, barcode):
    """Find product using GraphQL."""
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

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    cursor = None
    checked = 0

    while True:
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": {"cursor": cursor}}, headers=headers)
        result = response.json()

        if "errors" in result:
            return None, None

        data = result.get("data", {}).get("products", {})

        for edge in data.get("edges", []):
            product = edge["node"]
            checked += 1

            for v_edge in product.get("variants", {}).get("edges", []):
                variant = v_edge["node"]
                if variant.get("barcode") == barcode:
                    # Extract numeric IDs from GIDs
                    product_id = product["id"].split("/")[-1]
                    variant_id = variant["id"].split("/")[-1]
                    return product_id, variant_id

        if checked % 250 == 0:
            print(f"  Searched {checked} products...")

        if not data.get("pageInfo", {}).get("hasNextPage"):
            break
        cursor = data["pageInfo"]["endCursor"]

    return None, None


def rest_update_variant(access_token, variant_id, sku=None, weight_grams=None):
    """Update variant using REST API."""
    url = f"{REST_ENDPOINT}/variants/{variant_id}.json"

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token
    }

    variant_data = {}

    if sku:
        variant_data["sku"] = str(sku)

    if weight_grams:
        variant_data["weight"] = float(weight_grams)
        variant_data["weight_unit"] = "g"

    payload = {"variant": variant_data}

    response = requests.put(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.json(), None
    else:
        return None, f"HTTP {response.status_code}: {response.text}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_via_rest.py <barcode>")
        print("Example: python update_via_rest.py 5997412761382")
        sys.exit(1)

    barcode = sys.argv[1]

    print("=" * 70)
    print("Update Pentart Product via REST API")
    print("=" * 70)
    print()

    # 1. Database lookup
    print(f"1. Looking up barcode {barcode} in database...")
    db = PentartDatabase(DB_PATH)
    db_product = db.get_by_ean(barcode)

    if not db_product:
        print("   ✗ Not found in database")
        sys.exit(1)

    print(f"   ✓ Found: {db_product['description']}")
    print(f"   SKU: {db_product.get('article_number')}")
    print(f"   Weight: {db_product.get('product_weight')} g")
    print()

    # 2. Authenticate
    print("2. Authenticating...")
    access_token = authenticate()
    print("   ✓ Authenticated")
    print()

    # 3. Find product
    print(f"3. Finding product with barcode {barcode}...")
    product_id, variant_id = graphql_find_by_barcode(access_token, barcode)

    if not product_id:
        print("   ✗ Not found in Shopify")
        sys.exit(1)

    print(f"   ✓ Found product")
    print(f"   Product ID: {product_id}")
    print(f"   Variant ID: {variant_id}")
    print()

    # 4. Prepare update
    print("4. Preparing update via REST API...")
    new_sku = db_product.get('article_number')
    new_weight = db_product.get('product_weight')

    updates = []
    if new_sku:
        updates.append(f"SKU: {new_sku}")
    if new_weight:
        updates.append(f"Weight: {new_weight} g")

    for update in updates:
        print(f"   {update}")

    print()
    confirm = input("   Proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("   Cancelled")
        sys.exit(0)

    # 5. Update
    print()
    print("5. Updating via REST API...")
    result, error = rest_update_variant(access_token, variant_id, sku=new_sku, weight_grams=new_weight)

    if error:
        print(f"   ✗ Failed: {error}")
        sys.exit(1)

    variant = result.get("variant", {})
    print("   ✓ Successfully updated!")
    print(f"   SKU: {variant.get('sku')}")
    print(f"   Weight: {variant.get('weight')} {variant.get('weight_unit')}")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
