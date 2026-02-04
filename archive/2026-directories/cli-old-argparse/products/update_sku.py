import os
import requests
from dotenv import load_dotenv
import json

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
            print("Successfully authenticated with Shopify.")
        except Exception as e:
            print(f"Authentication failed: {e}")
            raise

    def execute_graphql(self, query, variables=None):
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        return response.json()

    def update_variant_sku(self, variant_id, new_sku):
        mutation = """
        mutation updateVariant($input: ProductVariantInput!) {
          productVariantsBulkUpdate(variants: [{id: $id, sku: $sku}]) {
            productVariants {
              id
              sku
              barcode
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        # Try a different approach using inventoryItem
        mutation2 = """
        mutation productVariantUpdate($id: ID!, $sku: String) {
          productVariantUpdate(input: {id: $id, sku: $sku}) {
            productVariant {
              id
              sku
              barcode
              title
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {
            "id": variant_id,
            "sku": new_sku
        }

        # Try the simpler mutation first
        try:
            result = self.execute_graphql(mutation2, variables)
            return result
        except Exception as e:
            print(f"First mutation failed: {e}")
            # If that fails, try REST API instead
            return None

def main():
    client = ShopifyClient()
    client.authenticate()

    # Product details from the search
    variant_id = "gid://shopify/ProductVariant/52561711595858"
    barcode = "5997412772012"
    new_sku = "21047"

    print(f"\nUpdating product variant:")
    print(f"  Variant ID: {variant_id}")
    print(f"  Barcode: {barcode}")
    print(f"  New SKU: {new_sku}")
    print()

    result = client.update_variant_sku(variant_id, new_sku)

    print("API Response:")
    print(json.dumps(result, indent=2))

    # Check for errors
    if result.get("data", {}).get("productVariantUpdate", {}).get("userErrors"):
        errors = result["data"]["productVariantUpdate"]["userErrors"]
        print("\nErrors occurred:")
        for error in errors:
            print(f"  - {error['field']}: {error['message']}")
    else:
        updated_variant = result.get("data", {}).get("productVariantUpdate", {}).get("productVariant")
        if updated_variant:
            print("\nSuccessfully updated!")
            print(f"  Variant ID: {updated_variant['id']}")
            print(f"  Title: {updated_variant['title']}")
            print(f"  SKU: {updated_variant['sku']}")
            print(f"  Barcode: {updated_variant['barcode']}")

if __name__ == "__main__":
    main()
