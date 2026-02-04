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

    def update_variant_sku_rest(self, variant_id_numeric, new_sku):
        """Update variant SKU using REST API"""
        url = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/variants/{variant_id_numeric}.json"

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        payload = {
            "variant": {
                "id": variant_id_numeric,
                "sku": new_sku
            }
        }

        response = requests.put(url, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: Status code {response.status_code}")
            print(f"Response: {response.text}")
            return None

def main():
    client = ShopifyClient()
    client.authenticate()

    # Extract numeric ID from GID
    variant_gid = "gid://shopify/ProductVariant/52561711595858"
    variant_id = variant_gid.split("/")[-1]  # Extract: 52561711595858

    barcode = "5997412772012"
    new_sku = "21047"

    print(f"\nUpdating product variant:")
    print(f"  Variant GID: {variant_gid}")
    print(f"  Variant ID: {variant_id}")
    print(f"  Barcode: {barcode}")
    print(f"  New SKU: {new_sku}")
    print()

    result = client.update_variant_sku_rest(variant_id, new_sku)

    if result:
        print("API Response:")
        print(json.dumps(result, indent=2))

        variant = result.get("variant", {})
        if variant:
            print("\n" + "="*60)
            print("Successfully updated!")
            print(f"  Variant ID: {variant.get('id')}")
            print(f"  Title: {variant.get('title')}")
            print(f"  SKU: {variant.get('sku')}")
            print(f"  Barcode: {variant.get('barcode')}")
            print("="*60)
    else:
        print("\nFailed to update variant.")

if __name__ == "__main__":
    main()
