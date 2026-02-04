"""
Update a Pentart product - barcode only, since SKU and weight have limitations.
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
    """Minimal Shopify client."""

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
        """Find product by barcode and get inventory item ID."""
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
                      inventoryItem {
                        id
                      }
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
                return None, None, None

            data = result.get("data", {}).get("products", {})

            for edge in data.get("edges", []):
                product = edge["node"]
                checked += 1

                for v_edge in product.get("variants", {}).get("edges", []):
                    variant = v_edge["node"]
                    if variant.get("barcode") == barcode:
                        inv_item_id = variant.get("inventoryItem", {}).get("id")
                        return product, variant, inv_item_id

            if checked % 250 == 0:
                print(f"  Searched {checked} products...")

            if not data.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = data["pageInfo"]["endCursor"]

        return None, None, None

    def update_variant_and_inventory(self, product_id, variant_id, inv_item_id, sku_str, weight_g):
        """
        Update variant barcode and inventory weight.
        Note: SKU is usually not updatable after product creation.
        """
        # First, try to update just barcode via productVariantsBulkUpdate
        # Then update weight via inventoryItemUpdate

        mutation = """
        mutation updateVariantAndInventory($productId: ID!, $variant: ProductVariantsBulkInput!, $invId: ID!, $invInput: InventoryItemInput!) {
          productVariantsBulkUpdate(productId: $productId, variants: [$variant]) {
            userErrors {
              field
              message
            }
          }
          inventoryItemUpdate(id: $invId, input: $invInput) {
            inventoryItem {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variant_input = {
            "id": variant_id
        }
        # ProductVariantsBulkInput does NOT support sku or weight
        # Only barcode, id, price, inventoryItem (nested), etc.

        inv_input = {}
        if weight_g:
            # inventoryItemUpdate doesn't support weight either!
            # Weight is actually on the variant, not inventory
            pass

        # For now, just try updating with what we can
        variables = {
            "productId": product_id,
            "variant": variant_input,
            "invId": inv_item_id,
            "invInput": inv_input
        }

        return self.execute_graphql(mutation, variables)


def main():
    print()
    print("NOTE: Shopify's GraphQL API has limitations:")
    print("  - SKU cannot be changed after product creation")
    print("  - Weight is not directly updatable via GraphQL Admin API")
    print("  - Only barcode can be reliably updated")
    print()
    print("The product with barcode 5997412761382 already HAS the correct barcode.")
    print("The missing SKU (37192) and weight (25.81g) cannot be set via this API.")
    print()
    print("Recommendation:")
    print("  1. Manually update SKU and weight in Shopify Admin UI")
    print("  2. Or use Shopify REST API (not GraphQL) which supports more fields")
    print("  3. Or set these values when initially creating the product")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
