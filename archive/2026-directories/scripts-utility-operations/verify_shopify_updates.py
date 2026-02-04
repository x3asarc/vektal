import os
import sys
import requests
import pandas as pd
from dotenv import load_dotenv
import time

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

# Global access token
ACCESS_TOKEN = None

def authenticate():
    """Exchange Client ID/Secret for an access_token."""
    global ACCESS_TOKEN
    payload = {
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        response = requests.post(TOKEN_ENDPOINT, json=payload)
        response.raise_for_status()
        data = response.json()
        ACCESS_TOKEN = data.get("access_token")
        print(f"Successfully authenticated with Shopify.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False

def execute_graphql(query, variables=None):
    """Execute a GraphQL query."""
    if not ACCESS_TOKEN:
        raise Exception("Not authenticated. Call authenticate() first.")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": ACCESS_TOKEN
    }

    response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
    response.raise_for_status()
    result = response.json()

    if "errors" in result:
        print(f"GraphQL Errors: {result['errors']}")
        return None
    return result

def get_all_products_by_vendor(vendor_name):
    """Get all products for a specific vendor with their image status."""
    products = []
    has_next_page = True
    cursor = None

    print(f"Fetching all products with vendor: {vendor_name}...")

    while has_next_page:
        query = """
        query getProducts($vendor: String!, $cursor: String) {
          products(first: 50, query: $vendor, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                handle
                vendor
                createdAt
                updatedAt
                images(first: 5) {
                  edges {
                    node {
                      id
                      url
                      altText
                    }
                  }
                }
                variants(first: 1) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                      inventoryItem {
                        countryCodeOfOrigin
                        harmonizedSystemCode
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """

        variables = {
            "vendor": f"vendor:{vendor_name}",
            "cursor": cursor
        }

        result = execute_graphql(query, variables)
        if not result:
            break

        page_info = result["data"]["products"]["pageInfo"]
        edges = result["data"]["products"]["edges"]

        for edge in edges:
            node = edge["node"]

            # Get variant info
            variant = node["variants"]["edges"][0]["node"] if node["variants"]["edges"] else {}
            inventory_item = variant.get("inventoryItem", {}) if variant else {}

            # Get image info
            images = node["images"]["edges"]
            image_count = len(images)
            first_image_url = images[0]["node"]["url"] if images else ""
            first_image_alt = images[0]["node"]["altText"] if images else ""

            products.append({
                "Handle": node["handle"],
                "Title": node["title"],
                "SKU": variant.get("sku", ""),
                "Barcode": variant.get("barcode", ""),
                "ImageCount": image_count,
                "FirstImageURL": first_image_url,
                "ImageAltText": first_image_alt,
                "CountryOfOrigin": inventory_item.get("countryCodeOfOrigin", ""),
                "HSCode": inventory_item.get("harmonizedSystemCode", ""),
                "CreatedAt": node["createdAt"],
                "UpdatedAt": node["updatedAt"],
                "Vendor": node["vendor"]
            })

        has_next_page = page_info["hasNextPage"]
        cursor = page_info["endCursor"]

        print(f"  Fetched {len(products)} products so far...")
        time.sleep(0.5)  # Rate limiting

    return products

def main():
    print("Connecting to Shopify...")
    print(f"Shop: {SHOP_DOMAIN}")

    # Authenticate first
    if not authenticate():
        print("Failed to authenticate with Shopify. Exiting.")
        return

    # Get all ITD Collection products
    itd_products = get_all_products_by_vendor("ITD Collection")

    print(f"\nTotal ITD Collection products found: {len(itd_products)}")

    # Create DataFrame
    df = pd.DataFrame(itd_products)

    # Save to CSV
    df.to_csv("shopify_itd_products.csv", index=False)
    print(f"Saved to shopify_itd_products.csv")

    # Analysis
    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)

    with_images = df[df['ImageCount'] > 0]
    without_images = df[df['ImageCount'] == 0]

    print(f"\nProducts WITH images: {len(with_images)} ({len(with_images)/len(df)*100:.1f}%)")
    print(f"Products WITHOUT images: {len(without_images)} ({len(without_images)/len(df)*100:.1f}%)")

    with_hs_code = df[df['HSCode'].notna() & (df['HSCode'] != '')]
    without_hs_code = df[~df.index.isin(with_hs_code.index)]

    print(f"\nProducts WITH HS Code: {len(with_hs_code)} ({len(with_hs_code)/len(df)*100:.1f}%)")
    print(f"Products WITHOUT HS Code: {len(without_hs_code)} ({len(without_hs_code)/len(df)*100:.1f}%)")

    with_barcode = df[df['Barcode'].notna() & (df['Barcode'] != '')]
    without_barcode = df[~df.index.isin(with_barcode.index)]

    print(f"\nProducts WITH Barcode: {len(with_barcode)} ({len(with_barcode)/len(df)*100:.1f}%)")
    print(f"Products WITHOUT Barcode: {len(without_barcode)} ({len(without_barcode)/len(df)*100:.1f}%)")

    # Compare with push_proof.csv
    if os.path.exists("push_proof.csv"):
        print("\n" + "="*60)
        print("COMPARISON WITH push_proof.csv")
        print("="*60)

        proof_df = pd.read_csv("push_proof.csv")
        proof_skus = set(proof_df['SKU'].astype(str))
        shopify_skus = set(df['SKU'].astype(str))

        print(f"\nSKUs in push_proof.csv: {len(proof_skus)}")
        print(f"SKUs in Shopify (ITD Collection): {len(shopify_skus)}")

        in_proof_not_shopify = proof_skus - shopify_skus
        if in_proof_not_shopify:
            print(f"\nWARNING: {len(in_proof_not_shopify)} SKUs in push_proof but NOT in Shopify ITD products:")
            for sku in list(in_proof_not_shopify)[:10]:
                print(f"  - {sku}")

        # Check if products in push_proof actually have images in Shopify
        verified_with_images = 0
        verified_without_images = 0

        for sku in proof_skus:
            matching = df[df['SKU'] == sku]
            if not matching.empty:
                if matching.iloc[0]['ImageCount'] > 0:
                    verified_with_images += 1
                else:
                    verified_without_images += 1

        print(f"\nVerification of push_proof.csv entries:")
        print(f"  ✅ Confirmed with images in Shopify: {verified_with_images}")
        print(f"  ❌ In push_proof but NO images in Shopify: {verified_without_images}")

    # Show sample of products without images
    if len(without_images) > 0:
        print("\n" + "="*60)
        print(f"Sample of products WITHOUT images (first 20):")
        print("="*60)
        for idx, row in without_images.head(20).iterrows():
            print(f"  {row['Handle']:50s} | SKU: {row['SKU']}")

if __name__ == "__main__":
    main()
