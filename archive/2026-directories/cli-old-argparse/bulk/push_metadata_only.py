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

class ShopifyMetadataClient:
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
        try:
            response = requests.post(GRAPHQL_ENDPOINT, json={"query": query, "variables": variables}, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  GraphQL Request Failed: {e}")
            return None

    def get_variant_by_sku(self, sku):
        query = """
        query getVariantBySku($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                variants(first: 1) {
                  edges {
                    node {
                      id
                      barcode
                      inventoryItem { id }
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.execute_graphql(query, {"query": f"sku:{sku}"})
        if not result or not isinstance(result, dict):
            return None, None, None, None
            
        data = result.get("data")
        if not data:
            return None, None, None, None
            
        products = data.get("products")
        if not products or not products.get("edges"):
            return None, None, None, None
            
        product = products["edges"][0]["node"]
        variants = product.get("variants")
        if not variants or not variants.get("edges"):
            return None, None, None, None
            
        variant = variants["edges"][0]["node"]
        inv_item = variant.get("inventoryItem")
        inv_id = inv_item.get("id") if inv_item else None
        
        return product.get("id"), variant.get("id"), inv_id, variant.get("barcode")

    def update_metadata(self, product_id, variant_id, inv_item_id, barcode, price, country):
        mutation = """
        mutation updateTechnicalMetadata($productId: ID!, $variant: ProductVariantsBulkInput!, $inventoryItem: InventoryItemInput!, $inv_item_id: ID!) {
          productVariantsBulkUpdate(productId: $productId, variants: [$variant]) {
            userErrors { message }
          }
          inventoryItemUpdate(id: $inv_item_id, input: $inventoryItem) {
            userErrors { message }
          }
        }
        """
        
        variant_input = {"id": variant_id}
        if barcode:
            variant_input["barcode"] = str(barcode)
            
        inv_input = {}
        if country:
            inv_input["countryCodeOfOrigin"] = country
        if price:
            inv_input["cost"] = str(price)
            
        variables = {
            "productId": product_id,
            "variant": variant_input,
            "inv_item_id": inv_item_id,
            "inventoryItem": inv_input
        }
        
        return self.execute_graphql(mutation, variables)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the success CSV")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"File not found: {args.csv}")
        return

    df = pd.read_csv(args.csv)
    df_success = df[df["Success"] == "YES"].copy()
    print(f"Loaded {len(df_success)} products for metadata update.")

    client = ShopifyMetadataClient()
    client.authenticate()

    results = []
    
    for idx, row in df_success.iterrows():
        sku = str(row["SKU"])
        handle = row["Handle"]
        scraped_sku = row.get("ScrapedSKU")
        price = row.get("Price_EUR")
        country = row.get("Country", "IT") # Default for Paperdesigns
        
        print(f"\n[{idx+1}/{len(df_success)}] Updating metadata for {handle} (SKU: {sku})")
        
        try:
            prod_id, var_id, inv_id, current_barcode = client.get_variant_by_sku(sku)
            
            if not var_id:
                print(f"  ❌ Product/Variant not found in Shopify")
                results.append({"SKU": sku, "Status": "Not Found"})
                continue
                
            if not inv_id:
                print(f"  ❌ Inventory Item ID not found")
                # We can still try to update variant barcode but inventoryItemUpdate will fail
            
            # Prepare updates
            barcode_to_push = None
            if scraped_sku and str(scraped_sku) != str(current_barcode) and str(scraped_sku) != sku:
                barcode_to_push = scraped_sku
            
            # If we don't have inv_id, we must split the mutation or it will fail
            if not inv_id:
                print("  ⚠️ Skipping inventory update (no inv_id)")
                # Minimal variant update only
                mutation_var = """
                mutation updateVariant($productId: ID!, $variant: ProductVariantsBulkInput!) {
                  productVariantsBulkUpdate(productId: $productId, variants: [$variant]) {
                    userErrors { message }
                  }
                }
                """
                res = client.execute_graphql(mutation_var, {"productId": prod_id, "variant": {"id": var_id, "barcode": barcode_to_push} if barcode_to_push else {"id": var_id}})
            else:
                res = client.update_metadata(prod_id, var_id, inv_id, barcode_to_push, price, country)
            
            if not res:
                print(f"  ❌ GraphQL Error (No response)")
                results.append({"SKU": sku, "Status": "GraphQL Error"})
                continue

            # Check for errors
            errors = []
            data = res.get("data")
            if data:
                if data.get("productVariantsBulkUpdate") and data["productVariantsBulkUpdate"].get("userErrors"):
                    errors.extend(data["productVariantsBulkUpdate"]["userErrors"])
                if data.get("inventoryItemUpdate") and data["inventoryItemUpdate"].get("userErrors"):
                    errors.extend(data["inventoryItemUpdate"]["userErrors"])
            else:
                if res.get("errors"):
                    errors.extend(res["errors"])
                else:
                    errors.append({"message": "Unknown GraphQL response structure"})
                
            if not errors:
                print(f"  ✅ Metadata updated (Barcode: {barcode_to_push}, Price: {price}, Country: {country})")
                results.append({"SKU": sku, "Status": "Success"})
            else:
                print(f"  ❌ Update failed: {errors}")
                results.append({"SKU": sku, "Status": "Error", "Message": str(errors)})
                
            time.sleep(0.5)
        except Exception as e:
            print(f"  ❌ Unexpected Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({"SKU": sku, "Status": "System Error", "Message": str(e)})
            time.sleep(1)

    res_dir = "results"
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)
    out_file = os.path.join(res_dir, f"metadata_push_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    pd.DataFrame(results).to_csv(out_file, index=False)
    print(f"\nDone! Summary saved to {out_file}")

if __name__ == "__main__":
    main()
