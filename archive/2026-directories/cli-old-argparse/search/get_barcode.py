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

    def get_product_details(self, title):
        query = """
        query getProductByTitle($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                title
                handle
                variants(first: 1) {
                  edges {
                    node {
                      barcode
                      sku
                    }
                  }
                }
                media(first: 10) {
                  edges {
                    node {
                      id
                      ... on MediaImage {
                        image {
                          url
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.execute_graphql(query, {"query": f"title:{title}"})
        return result

def main():
    client = ShopifyClient()
    client.authenticate()
    
    search_term = "Pentart Mixed Media Tinte 20ml - Blau"
    print(f"Searching for: {search_term}")
    
    result = client.get_product_details(search_term)
    
    products = result.get("data", {}).get("products", {}).get("edges", [])
    if not products:
        print("No products found.")
    else:
        node = products[0]['node']
        print(f"Product ID: {node['id']}")
        variants = node.get('variants', {}).get('edges', [])
        if variants:
            print(f"Barcode: {variants[0]['node']['barcode']}")
        else:
            print("No variants/barcode found.")
            
        media = node.get('media', {}).get('edges', [])
        if media:
             print(f"First Media ID: {media[0]['node']['id']}")

if __name__ == "__main__":
    main()
