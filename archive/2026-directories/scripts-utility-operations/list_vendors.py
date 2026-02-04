import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("API_VERSION", "2024-01")

TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"

def get_token():
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TOKEN_ENDPOINT, json=payload)
    return response.json().get("access_token")

def list_vendors():
    token = get_token()
    query = """
    {
      shop {
        productVendors(first: 100) {
          edges {
            node
          }
        }
      }
    }
    """
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    response = requests.post(GRAPHQL_ENDPOINT, json={"query": query}, headers=headers)
    vendors = [e["node"] for e in response.json()["data"]["shop"]["productVendors"]["edges"]]
    print("Available Vendors:")
    for v in vendors:
        print(f" - {v}")

if __name__ == "__main__":
    list_vendors()
