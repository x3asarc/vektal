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

    def find_product_by_barcode(self, barcode):
        query = """
        query findProductByBarcode($query: String!) {
          products(first: 5, query: $query) {
            edges {
              node {
                id
                title
                handle
                vendor
                variants(first: 10) {
                  edges {
                    node {
                      id
                      barcode
                      sku
                      title
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.execute_graphql(query, {"query": f"barcode:{barcode}"})
        return result

def main():
    client = ShopifyClient()
    client.authenticate()

    barcode = "5997412772012"
    print(f"Searching for product with barcode: {barcode}")

    result = client.find_product_by_barcode(barcode)

    print("\nRaw API Response:")
    print(json.dumps(result, indent=2))

    products = result.get("data", {}).get("products", {}).get("edges", [])
    if not products:
        print("\nNo products found with this barcode.")
    else:
        for p in products:
            node = p['node']
            print(f"\n{'='*60}")
            print(f"Product Title: {node['title']}")
            print(f"Product ID: {node['id']}")
            print(f"Vendor: {node.get('vendor', 'N/A')}")
            print(f"Handle: {node['handle']}")
            print(f"\nVariants:")
            for v in node['variants']['edges']:
                variant = v['node']
                print(f"  - Variant ID: {variant['id']}")
                print(f"    Title: {variant['title']}")
                print(f"    Barcode: {variant['barcode']}")
                print(f"    SKU: {variant['sku'] or '(empty)'}")

if __name__ == "__main__":
    main()
