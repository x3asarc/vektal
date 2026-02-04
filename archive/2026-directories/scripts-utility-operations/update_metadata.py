import os
import sys
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

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

# File paths
PUSH_PROOF_CSV = os.path.join("data", "push_proof.csv")
METADATA_LOG_CSV = os.path.join("data", "metadata_updates.csv")

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

def get_product_by_sku(sku):
    """Get product and variant by SKU."""
    query = """
    query getProductBySKU($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            title
            variants(first: 1) {
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

    variables = {"query": f"sku:{sku}"}
    result = execute_graphql(query, variables)

    if not result or not result.get("data", {}).get("products", {}).get("edges"):
        return None, None, None, None

    product = result["data"]["products"]["edges"][0]["node"]
    product_id = product["id"]

    if product["variants"]["edges"]:
        variant = product["variants"]["edges"][0]["node"]
        variant_id = variant["id"]
        current_barcode = variant.get("barcode", "")
        inventory_item_id = variant["inventoryItem"]["id"]
        return product_id, variant_id, current_barcode, inventory_item_id

    return product_id, None, None, None

def update_product_variants(product_id, variants):
    """Update product variants (barcode, HS code, country, price)."""
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        product {
          id
        }
        productVariants {
          id
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "productId": product_id,
        "variants": variants
    }

    result = execute_graphql(mutation, variables)
    return result

def update_metadata_for_product(row):
    """Update metadata (barcode, HS code, country, price) for a single product."""
    sku = row['SKU']
    scraped_barcode = row.get('ScrapedBarcode', '')
    price = row.get('Price', '')
    hs_code = row.get('HSCode', '')
    country = row.get('Country', '')

    print(f"\nProcessing {row['Handle']} | SKU: {sku}")

    # Get product from Shopify
    product_id, variant_id, current_barcode, inventory_item_id = get_product_by_sku(sku)

    if not product_id:
        print(f"  ❌ SKU {sku} not found in Shopify")
        return {
            "SKU": sku,
            "Status": "Not Found",
            "Message": "Product not found in Shopify"
        }

    if not variant_id:
        print(f"  ❌ No variant found for SKU {sku}")
        return {
            "SKU": sku,
            "Status": "No Variant",
            "Message": "No variant found"
        }

    print(f"  Found Product ID: {product_id}")

    # Build variant update
    variant_update = {"id": variant_id}
    updates_made = []

    # Update barcode if different and available
    if scraped_barcode and str(scraped_barcode).strip() != "" and str(scraped_barcode).strip() != str(sku).strip():
        if str(scraped_barcode) != str(current_barcode):
            variant_update["barcode"] = str(scraped_barcode)
            print(f"  📝 Updating barcode: {current_barcode} → {scraped_barcode}")
            updates_made.append("barcode")
        else:
            print(f"  ✅ Barcode already correct: {scraped_barcode}")
    else:
        print(f"  ℹ️ Keeping existing barcode: {current_barcode}")

    # Build inventory item update
    inventory_item = {}

    if price and str(price).strip() != "":
        inventory_item["cost"] = str(price)
        print(f"  📝 Updating cost: €{price}")
        updates_made.append("price")

    if country and str(country).strip() != "":
        inventory_item["countryCodeOfOrigin"] = str(country).strip()
        print(f"  📝 Updating country: {country}")
        updates_made.append("country")

    if hs_code and str(hs_code).strip() != "":
        inventory_item["harmonizedSystemCode"] = str(hs_code).strip()
        print(f"  📝 Updating HS code: {hs_code}")
        updates_made.append("hs_code")

    if inventory_item:
        variant_update["inventoryItem"] = inventory_item

    # Only update if there are changes
    if len(variant_update) > 1:  # More than just the ID
        result = update_product_variants(product_id, [variant_update])

        if result and not result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors"):
            print(f"  ✅ Successfully updated: {', '.join(updates_made)}")
            return {
                "SKU": sku,
                "Status": "Success",
                "Updates": ', '.join(updates_made),
                "Message": "Metadata updated successfully"
            }
        else:
            errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
            print(f"  ❌ Update failed: {errors}")
            return {
                "SKU": sku,
                "Status": "Error",
                "Updates": ', '.join(updates_made),
                "Message": f"Update failed: {errors}"
            }
    else:
        print(f"  ℹ️ No updates needed")
        return {
            "SKU": sku,
            "Status": "No Changes",
            "Updates": "",
            "Message": "No metadata changes needed"
        }

def main():
    print("="*60)
    print("SHOPIFY METADATA UPDATE SCRIPT")
    print("="*60)
    print(f"\nThis script will update metadata (barcode, HS code, country, price)")
    print(f"for products in {PUSH_PROOF_CSV}\n")

    # Check if push_proof.csv exists
    if not os.path.exists(PUSH_PROOF_CSV):
        print(f"❌ Error: {PUSH_PROOF_CSV} not found!")
        print(f"Please run image_scraper.py first to generate push_proof.csv")
        return

    # Authenticate with Shopify
    print(f"Connecting to Shopify: {SHOP_DOMAIN}")
    if not authenticate():
        print("❌ Failed to authenticate. Exiting.")
        return

    # Read push_proof.csv
    df = pd.read_csv(PUSH_PROOF_CSV)
    print(f"\nLoaded {len(df)} products from {PUSH_PROOF_CSV}")

    # Filter for products that have metadata to update
    # (at least one of: ScrapedBarcode, Price, HSCode, Country)
    has_metadata = df[
        (df['ScrapedBarcode'].notna() & (df['ScrapedBarcode'] != '')) |
        (df['Price'].notna() & (df['Price'] != '')) |
        (df['HSCode'].notna() & (df['HSCode'] != '')) |
        (df['Country'].notna() & (df['Country'] != ''))
    ]

    print(f"Found {len(has_metadata)} products with metadata to update")

    if len(has_metadata) == 0:
        print("\n✅ No products need metadata updates!")
        return

    # Ask for confirmation
    print(f"\n{'='*60}")
    response = input(f"Ready to update {len(has_metadata)} products? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Update cancelled by user")
        return

    # Process each product
    print(f"\n{'='*60}")
    print("Starting metadata updates...")
    print(f"{'='*60}")

    results = []
    for idx, row in has_metadata.iterrows():
        result = update_metadata_for_product(row)
        result["Time"] = datetime.now().isoformat()
        result["Handle"] = row['Handle']
        results.append(result)

        # Rate limiting
        time.sleep(0.5)

    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(METADATA_LOG_CSV, index=False)

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    success_count = len(results_df[results_df['Status'] == 'Success'])
    no_changes_count = len(results_df[results_df['Status'] == 'No Changes'])
    error_count = len(results_df[results_df['Status'].isin(['Error', 'Not Found', 'No Variant'])])

    print(f"Total processed: {len(results)}")
    print(f"  ✅ Successfully updated: {success_count}")
    print(f"  ℹ️ No changes needed: {no_changes_count}")
    print(f"  ❌ Errors: {error_count}")

    print(f"\n✅ Results saved to {METADATA_LOG_CSV}")

if __name__ == "__main__":
    main()
