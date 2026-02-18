"""
Automated Product Image Finder

Finds product images from multiple sources:
1. Vendor website (if configured)
2. Google Image Search (fallback)
3. Google Shopping (fallback)

Usage:
    python utils/find_product_image.py --sku "CBRP104"
    python utils/find_product_image.py --sku "CBRP104" --auto-add
"""

import os
import sys
import argparse
import re
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo.seo_generator import ShopifyClient


def search_vendor_website(vendor, product_title, barcode):
    """
    Search vendor website for product image.

    Returns:
        dict: {"found": bool, "source": str, "image_url": str, "page_url": str}
    """
    # Load vendor configs
    import yaml
    config_path = "config/vendor_configs.yaml"

    if not os.path.exists(config_path):
        return {"found": False, "source": "vendor", "error": "No vendor config"}

    with open(config_path, 'r', encoding='utf-8') as f:
        vendor_configs = yaml.safe_load(f)

    # Get vendor config
    vendor_key = vendor.lower().replace(" ", "_")
    vendor_config = vendor_configs.get(vendor_key, {})

    if not vendor_config.get("website"):
        return {"found": False, "source": "vendor", "error": f"No website configured for {vendor}"}

    print(f"   [INFO] Vendor website: {vendor_config['website']}")
    print(f"   [INFO] This would require web scraping - not implemented in basic version")

    return {"found": False, "source": "vendor", "error": "Vendor scraping not configured"}


def search_google_images(product_title, vendor, barcode):
    """
    Search Google Images for product.

    NOTE: This is a placeholder. Real implementation would use:
    - Google Custom Search API
    - SerpAPI
    - Or web scraping (requires selenium)

    Returns:
        dict: {"found": bool, "source": str, "image_url": str, "page_url": str}
    """
    search_query = f"{vendor} {product_title}"

    print(f"   [SEARCH] Google Images: '{search_query}'")
    print(f"   [INFO] Would search: https://www.google.com/search?tbm=isch&q={search_query.replace(' ', '+')}")

    # Add barcode if available
    if barcode:
        print(f"   [INFO] Also try: '{barcode}' or '{vendor} {barcode}'")

    return {
        "found": False,
        "source": "google_images",
        "error": "Automated Google search requires API key or selenium",
        "manual_url": f"https://www.google.com/search?tbm=isch&q={search_query.replace(' ', '+')}"
    }


def search_google_shopping(product_title, vendor, barcode):
    """
    Search Google Shopping for product.

    Returns:
        dict: {"found": bool, "source": str, "image_url": str, "page_url": str}
    """
    search_query = f"{vendor} {product_title}"

    print(f"   [SEARCH] Google Shopping: '{search_query}'")
    print(f"   [INFO] Would search: https://www.google.com/search?tbm=shop&q={search_query.replace(' ', '+')}")

    if barcode:
        print(f"   [INFO] Try barcode search: https://www.google.com/search?tbm=shop&q={barcode}")

    return {
        "found": False,
        "source": "google_shopping",
        "error": "Automated Google Shopping requires API key",
        "manual_url": f"https://www.google.com/search?tbm=shop&q={search_query.replace(' ', '+')}"
    }


def add_image_to_product(product_id, image_url, alt_text):
    """
    Add image to Shopify product.

    Args:
        product_id: Shopify product ID (gid://shopify/Product/...)
        image_url: URL of image to add
        alt_text: Alt text for image

    Returns:
        bool: Success status
    """
    client = ShopifyClient()
    if not client.authenticate():
        return False

    mutation = '''
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media {
          alt
          mediaContentType
          status
        }
        mediaUserErrors {
          field
          message
        }
      }
    }
    '''

    variables = {
        'productId': product_id,
        'media': [{
            'originalSource': image_url,
            'alt': alt_text,
            'mediaContentType': 'IMAGE'
        }]
    }

    result = client.execute_graphql(mutation, variables)

    if result:
        errors = result['data']['productCreateMedia'].get('mediaUserErrors', [])
        if errors:
            print(f"   [ERROR] Failed to add image: {errors}")
            return False

        media = result['data']['productCreateMedia']['media']
        if media:
            print(f"   [OK] Image added successfully (status: {media[0]['status']})")
            return True

    return False


def find_and_add_image(sku, auto_add=False):
    """
    Find image for product and optionally add it.

    Args:
        sku: Product SKU
        auto_add: If True, automatically add found image

    Returns:
        bool: Success status
    """
    print(f"Finding image for SKU: {sku}")
    print()

    # Fetch product from Shopify
    client = ShopifyClient()
    if not client.authenticate():
        return False

    query = """
    query GetProduct($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            title
            vendor
            descriptionHtml
            variants(first: 1) {
              edges {
                node {
                  sku
                  barcode
                }
              }
            }
            images(first: 5) {
              edges {
                node {
                  id
                  url
                }
              }
            }
          }
        }
      }
    }
    """

    result = client.execute_graphql(query, {"query": f"sku:{sku}"})

    if not result or not result["data"]["products"]["edges"]:
        print("[ERROR] Product not found")
        return False

    node = result["data"]["products"]["edges"][0]["node"]
    variant = node["variants"]["edges"][0]["node"] if node["variants"]["edges"] else {}

    product_id = node["id"]
    title = node["title"]
    vendor = node.get("vendor", "")
    barcode = variant.get("barcode", "")
    existing_images = node["images"]["edges"]

    print(f"Product: {title}")
    print(f"Vendor: {vendor}")
    print(f"Barcode: {barcode or 'N/A'}")
    print(f"Existing images: {len(existing_images)}")
    print()

    if existing_images:
        print("[OK] Product already has images:")
        for img in existing_images:
            print(f"  - {img['node']['url']}")
        return True

    print("=" * 70)
    print("SEARCHING FOR IMAGES")
    print("=" * 70)
    print()

    # Search strategy: Vendor → Google Images → Google Shopping
    search_results = []

    # 1. Try vendor website
    print("[1/3] Checking vendor website...")
    vendor_result = search_vendor_website(vendor, title, barcode)
    search_results.append(vendor_result)

    if vendor_result.get("found"):
        print(f"   [FOUND] Image on vendor website!")
        image_url = vendor_result["image_url"]
    else:
        print(f"   [NOT FOUND] {vendor_result.get('error', 'No result')}")
        print()

        # 2. Try Google Images
        print("[2/3] Trying Google Image Search...")
        google_result = search_google_images(title, vendor, barcode)
        search_results.append(google_result)

        if google_result.get("found"):
            print(f"   [FOUND] Image via Google Images!")
            image_url = google_result["image_url"]
        else:
            print(f"   [NOT FOUND] {google_result.get('error', 'No result')}")
            if google_result.get("manual_url"):
                print(f"   [MANUAL] Try: {google_result['manual_url']}")
            print()

            # 3. Try Google Shopping
            print("[3/3] Trying Google Shopping...")
            shopping_result = search_google_shopping(title, vendor, barcode)
            search_results.append(shopping_result)

            if shopping_result.get("found"):
                print(f"   [FOUND] Image via Google Shopping!")
                image_url = shopping_result["image_url"]
            else:
                print(f"   [NOT FOUND] {shopping_result.get('error', 'No result')}")
                if shopping_result.get("manual_url"):
                    print(f"   [MANUAL] Try: {shopping_result['manual_url']}")

    print()
    print("=" * 70)
    print("SEARCH SUMMARY")
    print("=" * 70)
    print()

    # Check if any source found an image
    found_image = any(r.get("found") for r in search_results)

    if not found_image:
        print("🚨 [FLAG] NO IMAGES FOUND")
        print()
        print("Manual search required:")
        for result in search_results:
            if result.get("manual_url"):
                print(f"  - {result['source']}: {result['manual_url']}")

        print()
        print("RECOMMENDED NEXT STEPS:")
        print("1. Search manually using links above")
        print("2. Once you find image URL, run:")
        print(f"   python utils/add_product_image.py --sku {sku} --image-url <URL>")

        return False

    # Image found - add it if auto_add
    if auto_add:
        print(f"[AUTO-ADD] Adding image to product...")
        alt_text = f"{vendor} {title}"
        success = add_image_to_product(product_id, image_url, alt_text)

        if success:
            print()
            print("✅ [SUCCESS] Image added to product!")
            return True
        else:
            print()
            print("❌ [FAILED] Could not add image")
            return False
    else:
        print(f"[INFO] Image found but not added (use --auto-add to add automatically)")
        print(f"       Image URL: {image_url}")
        print()
        print("To add manually:")
        print(f"  python utils/add_product_image.py --sku {sku} --image-url \"{image_url}\"")

        return True


def main():
    parser = argparse.ArgumentParser(description="Find and add product images")
    parser.add_argument("--sku", required=True, help="Product SKU")
    parser.add_argument("--auto-add", action="store_true", help="Automatically add found image")
    args = parser.parse_args()

    success = find_and_add_image(args.sku, auto_add=args.auto_add)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
