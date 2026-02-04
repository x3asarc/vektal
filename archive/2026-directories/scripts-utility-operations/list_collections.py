import os
import requests
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
API_VERSION = os.getenv("API_VERSION", "2024-01")

TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token"
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"

def get_access_token():
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(TOKEN_ENDPOINT, json=payload)
    response.raise_for_status()
    return response.json().get("access_token")

def list_collections():
    token = get_access_token()
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token
    }
    
    query = """
    {
      collections(first: 250) {
        edges {
          node {
            id
            title
            handle
          }
        }
      }
    }
    """
    
    response = requests.post(GRAPHQL_ENDPOINT, json={"query": query}, headers=headers)
    response.raise_for_status()
    result = response.json()
    
    if "data" in result:
        for edge in result["data"]["collections"]["edges"]:
            node = edge["node"]
            if "rice" in node['title'].lower() or "rice" in node['handle'].lower() or "reis" in node['title'].lower() or "reis" in node['handle'].lower():
                print(f"Collection: {node['title']} (Handle: {node['handle']})")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    list_collections()
