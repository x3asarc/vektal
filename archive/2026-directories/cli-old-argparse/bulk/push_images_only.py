import os
import sys
import time
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.image_scraper import clean_product_name, get_valid_filename, validate_alt_text
from src.core.vendor_config import get_vendor_manager, generate_vendor_filename, generate_vendor_alt_text

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

    def get_product_by_sku(self, sku):
        query = """
        query getProductBySku($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                handle
                media(first: 10) {
                  edges {
                    node {
                      ... on MediaImage { id }
                    }
                  }
                }
              }
            }
          }
        }
        """
        result = self.execute_graphql(query, {"query": f"sku:{sku}"})
        if result and result.get("data", {}).get("products", {}).get("edges"):
            return result["data"]["products"]["edges"][0]["node"]
        return None

    def delete_media(self, product_id, media_ids):
        mutation = """
        mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
          productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            userErrors { message }
          }
        }
        """
        return self.execute_graphql(mutation, {"productId": product_id, "mediaIds": media_ids})

    def create_media(self, product_id, image_url, alt_text):
        mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
          productCreateMedia(productId: $productId, media: $media) {
            media {
              id
              alt
              ... on MediaImage {
                id
                image {
                  url
                }
              }
            }
            userErrors { message }
          }
        }
        """
        media_input = {
            "originalSource": image_url,
            "mediaContentType": "IMAGE",
            "alt": alt_text
        }
        return self.execute_graphql(mutation, {"productId": product_id, "media": [media_input]})

    def rename_media_files(self, media_updates):
        """
        Rename uploaded media files using Shopify's fileUpdate mutation.

        Args:
            media_updates: List of dicts with 'id' and 'filename' keys
                          Example: [{"id": "gid://shopify/MediaImage/123", "filename": "product-name.jpg"}]

        Returns:
            GraphQL response with updated file info

        Note:
            - Maximum 25 files can be updated per mutation
            - Filename extension must match the original file type
            - This is called AFTER productCreateMedia to rename images for SEO
        """
        mutation = """
        mutation fileUpdate($files: [FileUpdateInput!]!) {
          fileUpdate(files: $files) {
            files {
              id
              alt
              ... on MediaImage {
                id
                image {
                  url
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        # Process in batches of 25 (Shopify's limit)
        batch_size = 25
        all_results = []

        for i in range(0, len(media_updates), batch_size):
            batch = media_updates[i:i + batch_size]
            result = self.execute_graphql(mutation, {"files": batch})
            all_results.append(result)

        return all_results if len(all_results) > 1 else all_results[0]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to the success CSV")
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"File not found: {args.csv}")
        return

    df = pd.read_csv(args.csv)
    # Filter for successful finds
    df_success = df[df["Success"] == "YES"].copy()
    print(f"Loaded {len(df_success)} products for image push.")

    client = ShopifyClient()
    client.authenticate()

    results = []
    
    # Load vendor configuration manager
    vendor_manager = get_vendor_manager()
    print(f"Loaded vendor configurations for {len(vendor_manager.configs)} vendors\n")

    for idx, row in df_success.iterrows():
        sku = str(row["SKU"])
        handle = row["Handle"]
        image_url = row["ImageURL"]
        title = row.get("Title", handle)
        vendor = row.get("Vendor", None)  # Get vendor from CSV if available

        print(f"\n[{idx+1}/{len(df_success)}] Processing {handle} (SKU: {sku})")
        if vendor:
            detected_vendor = vendor_manager.detect_vendor(vendor)
            print(f"  Vendor: {vendor} (using config: {detected_vendor})")

        try:
            product = client.get_product_by_sku(sku)
            if not product:
                print(f"  ❌ Product not found in Shopify")
                results.append({"SKU": sku, "Handle": handle, "Status": "Not Found"})
                continue

            product_id = product["id"]

            # 1. Check existing images
            media_ids = [edge["node"]["id"] for edge in product["media"]["edges"]]
            if media_ids:
                print(f"  ℹ️ Product already has {len(media_ids)} images. Skipping.")
                results.append({"SKU": sku, "Handle": handle, "Status": "Skipped"})
                continue

            # 2. Generate vendor-specific alt text with keyword optimization
            alt_text = generate_vendor_alt_text(title, vendor, add_keywords=True)
            print(f"  Alt text: \"{alt_text}\"")

            # 3. Upload new image with vendor-optimized alt text
            res = client.create_media(product_id, image_url, alt_text)
            if res and not res.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
                print(f"  ✅ Image uploaded successfully")

                # 4. Get media ID from response for renaming
                media_data = res.get("data", {}).get("productCreateMedia", {}).get("media", [])
                if media_data and len(media_data) > 0:
                    media_id = media_data[0].get("id")

                    # 5. Generate vendor-specific SEO-friendly filename
                    # Extract file extension from original URL
                    original_ext = os.path.splitext(image_url.split('?')[0])[1] or '.jpg'
                    # Use vendor configuration to generate filename
                    cleaned_title = clean_product_name(title) or title
                    new_filename = generate_vendor_filename(cleaned_title, sku, vendor, extension=original_ext)

                    # 6. Rename the uploaded image
                    try:
                        rename_res = client.rename_media_files([{
                            "id": media_id,
                            "filename": new_filename
                        }])

                        if rename_res and not rename_res.get("data", {}).get("fileUpdate", {}).get("userErrors"):
                            print(f"  ✅ Image renamed to: {new_filename}")
                            results.append({"SKU": sku, "Handle": handle, "Status": "Success", "Filename": new_filename})
                        else:
                            rename_errors = rename_res.get("data", {}).get("fileUpdate", {}).get("userErrors", [])
                            print(f"  ⚠️ Rename failed: {rename_errors}")
                            results.append({"SKU": sku, "Handle": handle, "Status": "Success (no rename)", "Message": str(rename_errors)})
                    except Exception as rename_err:
                        print(f"  ⚠️ Rename error: {rename_err}")
                        results.append({"SKU": sku, "Handle": handle, "Status": "Success (no rename)"})
                else:
                    print(f"  ⚠️ Could not extract media ID for renaming")
                    results.append({"SKU": sku, "Handle": handle, "Status": "Success (no rename)"})
            else:
                errors = res.get("data", {}).get("productCreateMedia", {}).get("userErrors", [])
                print(f"  ❌ Upload failed: {errors}")
                results.append({"SKU": sku, "Handle": handle, "Status": "Error", "Message": str(errors)})

            time.sleep(0.5) # Rate limiting
        except Exception as e:
            print(f"  ❌ Error processing {sku}: {e}")
            results.append({"SKU": sku, "Handle": handle, "Status": "System Error", "Message": str(e)})
            time.sleep(2) # Backoff

    # Save summary
    res_dir = "results"
    if not os.path.exists(res_dir):
        os.makedirs(res_dir)
    out_file = os.path.join(res_dir, f"image_push_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    pd.DataFrame(results).to_csv(out_file, index=False)
    print(f"\nDone! Summary saved to {out_file}")

    # 3. Log successes to push_proof.csv
    proof_file = os.path.join("data", "push_proof.csv")
    success_items = [r for r in results if r["Status"] == "Success"]
    if success_items:
        # We need the full data from the original DF to log Price, HSCode, etc.
        df_source = df_success.set_index("SKU")
        proof_entries = []
        for item in success_items:
            sku = item["SKU"]
            source_row = df_source.loc[sku]
            proof_entries.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Handle": item["Handle"],
                "SKU": sku,
                "ScrapedBarcode": source_row.get("ScrapedBarcode", source_row.get("ScrapedSKU", "")),
                "ImageURL": source_row.get("ImageURL", ""),
                "Price": source_row.get("Price", source_row.get("Price_EUR", "")),
                "HSCode": source_row.get("HSCode", ""),
                "Country": source_row.get("Country", "IT"),
                "ProductTitle": source_row.get("Title", ""),
                "Status": "Success"
            })
        
        df_proof_new = pd.DataFrame(proof_entries)
        if not os.path.exists(os.path.dirname(proof_file)):
            os.makedirs(os.path.dirname(proof_file))
            
        if os.path.exists(proof_file):
            df_existing = pd.read_csv(proof_file)
            # Avoid duplicates
            df_proof_new = df_proof_new[~df_proof_new["SKU"].astype(str).isin(df_existing["SKU"].astype(str))]
            if not df_proof_new.empty:
                df_proof_new.to_csv(proof_file, mode='a', header=False, index=False)
                print(f"Logged {len(df_proof_new)} new products to {proof_file}")
        else:
            df_proof_new.to_csv(proof_file, index=False)
            print(f"Created {proof_file} with {len(df_proof_new)} products")

if __name__ == "__main__":
    main()
