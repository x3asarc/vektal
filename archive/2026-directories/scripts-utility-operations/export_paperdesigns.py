import os
import sys
import requests
import pandas as pd
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

    def get_products_by_vendor(self, vendor):
        all_products = []
        cursor = None
        
        query = """
        query getProducts($query: String!, $after: String) {
          products(first: 50, query: $query, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                handle
                title
                vendor
                media(first: 1) {
                  edges {
                    node {
                      id
                    }
                  }
                }
                variants(first: 1) {
                  edges {
                    node {
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
        
        while True:
            variables = {"query": f"vendor:'{vendor}'", "after": cursor}
            result = self.execute_graphql(query, variables)
            
            if not result or "data" not in result:
                break
                
            products = result["data"]["products"]["edges"]
            for p in products:
                node = p["node"]
                # Only include products with no images
                if not node["media"]["edges"]:
                    sku = node["variants"]["edges"][0]["node"]["sku"] if node["variants"]["edges"] else ""
                    all_products.append({
                        "Handle": node["handle"],
                        "SKU": sku,
                        "Title": node["title"],
                        "Vendor": node["vendor"]
                    })
            
            page_info = result["data"]["products"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]
            print(f"  Fetched {len(all_products)} products...")
            
        return all_products

def main():
    client = ShopifyClient()
    client.authenticate()
    
    vendor = "Paperdesigns"
    print(f"Fetching all products for vendor: {vendor}")
    products = client.get_products_by_vendor(vendor)
    
    if products:
        df = pd.DataFrame(products)
        out_file = "paperdesigns_inventory.csv"
        df.to_csv(out_file, index=False)
        print(f"\nSaved {len(products)} products to {out_file}")
    else:
        print("No products found for this vendor.")

if __name__ == "__main__":
    main()
