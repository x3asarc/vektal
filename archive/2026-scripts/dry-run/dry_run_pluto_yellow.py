"""
DRY RUN: Galaxy Flakes Pluto Yellow
Shows what WOULD happen - makes NO actual changes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
from src.core.shopify_resolver import ShopifyResolver

print("="*80)
print("DRY RUN - Galaxy Flakes Product")
print("="*80)
print("\n** THIS IS A DRY RUN - NO CHANGES WILL BE MADE **\n")

# User provided handle
product_handle = "galaxy-flakes-15g-pluto-yellow-6505"

print(f"[LOOKING UP PRODUCT FROM SHOPIFY]")
print(f"  Handle: {product_handle}")

# Connect to Shopify
resolver = ShopifyResolver()
print("  Connected to Shopify")

# Query product by handle
product_query = """
query getProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    featuredImage {
      url
      altText
    }
    media(first: 20) {
      edges {
        node {
          id
          alt
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
"""

result = resolver.client.execute_graphql(product_query, {"handle": product_handle})
product = result.get('data', {}).get('productByHandle')

if not product:
    print(f"\n  ERROR: Product with handle '{product_handle}' not found in Shopify")
    print("\n  Please verify the handle is correct.")
    sys.exit(1)

product_id = product['id'].split('/')[-1]
product_title = product['title']

print(f"  Found: {product_title}")
print(f"  ID: {product_id}")
print()

# Load SEO plan and download results
script_dir = Path(__file__).parent
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
download_results_path = script_dir / "data" / "supplier_images" / "galaxy_flakes" / "download_results.csv"

seo_df = pd.read_csv(seo_plan_path)
download_df = pd.read_csv(download_results_path)

# Find in SEO plan
seo_row = seo_df[(seo_df['product_id'] == int(product_id)) & (seo_df['is_primary'] == True)]

if seo_row.empty:
    print(f"[WARNING] Product ID {product_id} not found in SEO plan")
    print(f"This product may not be part of the Galaxy Flakes batch.")
    proposed_filename = "pentart-galaxy-flakes-product.png"
    proposed_alt = product_title
    supplier_url = None
else:
    proposed_filename = seo_row.iloc[0]['proposed_filename'].replace('.jpg', '.png')
    proposed_alt = seo_row.iloc[0]['proposed_alt']

    # Get supplier image
    download_row = download_df[download_df['product_id'] == int(product_id)]
    if not download_row.empty:
        supplier_url = download_row.iloc[0]['image_url']
        supplier_status = download_row.iloc[0]['status']
    else:
        supplier_url = None
        supplier_status = "not_found"

print(f"[PRODUCT INFO]")
print(f"  Title: {product_title}")
print(f"  Handle: {product_handle}")
print(f"  ID: {product_id}")
print()

print(f"[SUPPLIER IMAGE]")
if supplier_url:
    print(f"  Status: {supplier_status}")
    print(f"  URL: {supplier_url[:80]}...")
else:
    print(f"  Status: Not available")
    print(f"  Note: This product may need manual image sourcing")
print()

# Show current state
media_list = product.get('media', {}).get('edges', [])
print(f"[CURRENT STATE IN SHOPIFY]")
print(f"  Total images: {len(media_list)}")
print()

if media_list:
    print("  Current images:")
    for i, edge in enumerate(media_list, 1):
        node = edge['node']
        alt = node.get('alt', '(no alt text)')
        url = node.get('image', {}).get('url', '')
        # Extract filename from URL
        filename = url.split('/')[-1].split('?')[0] if url else 'N/A'
        is_featured = " <- FEATURED" if i == 1 else ""
        print(f"    {i}. {filename[:50]}{is_featured}")
        print(f"       Alt: {alt[:60]}")
else:
    print("  No images currently on product")

print()
print("="*80)
print("WHAT WOULD HAPPEN (DRY RUN)")
print("="*80)
print()

if supplier_url:
    print(f"[STEP 1] Download supplier image from Pentacolor")
    print(f"  URL: {supplier_url[:80]}...")
    print()
    print(f"[STEP 2] Process image")
    print(f"  - Convert to square (1:1 ratio, center crop)")
    print(f"  - Ensure transparent background (PNG format)")
    print(f"  - Target size: 900x900 pixels")
    print()
    print(f"[STEP 3] Upload new image")
    print(f"  - Filename: {proposed_filename}")
    print(f"  - Alt text: {proposed_alt}")
    print(f"  - Method: Staged upload (for filename control)")
    print()
    print(f"[STEP 4] Set as featured")
    print(f"  - Reorder new image to position 0 (featured)")
    if media_list:
        print(f"  - Current featured image moves to position 1")
        print(f"  - All other {len(media_list)-1 if len(media_list) > 1 else 0} images remain in same order")
    else:
        print(f"  - New image becomes the only image")
    print()
    print(f"[STEP 5] Deletion")
    print(f"  - NO IMAGES WILL BE DELETED")
    print(f"  - All {len(media_list)} existing images will be PRESERVED")
    print()
    print("="*80)
    print("FINAL STATE (AFTER OPERATION)")
    print("="*80)
    print()
    print(f"Total images: {len(media_list) + 1} (current: {len(media_list)}, new: 1)")
    print()
    print(f"Image list:")
    print(f"  1. {proposed_filename} <- FEATURED (NEW)")
    if media_list:
        for i, edge in enumerate(media_list, 2):
            node = edge['node']
            url = node.get('image', {}).get('url', '')
            filename = url.split('/')[-1].split('?')[0] if url else 'N/A'
            print(f"  {i}. {filename[:50]} (PRESERVED)")
else:
    print("[INFO] No supplier image available for this product")
    print("Operation would require manual image sourcing")

print()
print("="*80)
print("** DRY RUN COMPLETE - NO CHANGES MADE **")
print("="*80)
