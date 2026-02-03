"""
DRY RUN: Restore 7 Shared Images to All 12 Galaxy Flakes Products

Current State:
- 12 products have ONLY primary image (1 image each)
- 7 shared images from Juno Rose verified with vision AI

Goal:
- Add the 7 shared images to all 12 products
- Final: Each product has 8 images (1 primary + 7 shared)

This is a DRY RUN - NO CHANGES WILL BE MADE
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
from src.core.shopify_resolver import ShopifyResolver

print("="*80)
print("DRY RUN - Restore 7 Shared Images to 12 Galaxy Flakes Products")
print("="*80)
print("\n** THIS IS A DRY RUN - NO CHANGES WILL BE MADE **\n")

# Paths
script_dir = Path(__file__).parent
vision_results_path = script_dir / "data" / "shared_images" / "galaxy_flakes" / "vision_analysis_results.csv"
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"

# Load vision AI results (the 7 images we verified)
vision_df = pd.read_csv(vision_results_path)
seo_df = pd.read_csv(seo_plan_path)

print("[1/4] Loading verified images from vision AI analysis...")
print(f"  Found {len(vision_df)} images with vision AI verification")
print()

# Show the 7 images with their AI-verified types and hybrid names
print("  Verified Images (with hybrid naming):")
print()
for _, row in vision_df.iterrows():
    num = row['image_num']
    ai_type = row['ai_type']
    ai_filename = row['ai_filename']
    ai_alt = row['ai_alt']

    print(f"  {num}. Type: {ai_type.upper()}")
    print(f"     Filename: {ai_filename}")
    print(f"     Alt: {ai_alt[:70]}...")
    print()

# Get the 12 products that need these images
primary_products = seo_df[seo_df['is_primary'] == True].copy()

print(f"[2/4] Identifying products that need shared images...")
print(f"  Found {len(primary_products)} Galaxy Flakes products")
print()

# Connect to Shopify to check current state
print("[3/4] Checking current state in Shopify...")
resolver = ShopifyResolver()
print("  Connected")
print()

# Query to get product images
query = """
query getProduct($id: ID!) {
  product(id: $id) {
    title
    media(first: 20) {
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
"""

current_states = []
for _, prod_row in primary_products.iterrows():
    product_id = str(prod_row['product_id'])
    gid = f"gid://shopify/Product/{product_id}"

    result = resolver.client.execute_graphql(query, {"id": gid})
    product = result.get('data', {}).get('product')

    if product:
        media_count = len(product.get('media', {}).get('edges', []))
        current_states.append({
            'product_id': product_id,
            'title': product['title'],
            'current_images': media_count
        })

print("  Current state of products:")
for state in current_states[:5]:
    print(f"    - {state['title']}: {state['current_images']} image(s)")
print(f"    ... and {len(current_states) - 5} more")
print()

# Calculate what will happen
print("="*80)
print("WHAT WOULD HAPPEN (DRY RUN)")
print("="*80)
print()

print(f"[STEP 1] Download 7 shared images from Juno Rose product")
print(f"  Source: Product ID 6665942925469 (Galaxy Flakes 15g - Juno rose)")
print()

print(f"[STEP 2] Process each image with hybrid naming")
print()
for _, row in vision_df.iterrows():
    num = row['image_num']
    ai_type = row['ai_type']
    hybrid_filename = f"pentart-galaxy-flakes-15g-{ai_type}.jpg"

    print(f"  Image {num}: {row['current_filename'][:50]}")
    print(f"    -> Rename to: {hybrid_filename}")
    print(f"    -> Alt text: {row['ai_alt'][:60]}...")
    print()

print(f"[STEP 3] Upload 7 images to each of 12 products")
print(f"  Total uploads: {len(vision_df)} images × {len(current_states)} products = {len(vision_df) * len(current_states)} uploads")
print()

# Show example for one product
example_product = current_states[0]
print(f"  Example: {example_product['title']}")
print(f"    Current: {example_product['current_images']} image (primary only)")
print(f"    After: {example_product['current_images'] + len(vision_df)} images (1 primary + 7 shared)")
print()
print(f"    Image list after operation:")
print(f"      1. pentart-galaxy-flakes-15g-{primary_products.iloc[0]['product_title'].split()[-1].lower()}.png (PRIMARY - preserved)")

for idx, row in vision_df.iterrows():
    ai_type = row['ai_type']
    hybrid_filename = f"pentart-galaxy-flakes-15g-{ai_type}.jpg"
    print(f"      {idx + 2}. {hybrid_filename} (NEW - shared)")
print()

print(f"[STEP 4] Set proper positioning")
print(f"  - Primary image stays at position 0 (featured)")
print(f"  - Shared images added at positions 1-7")
print(f"  - NO deletion of any images")
print()

print("="*80)
print("FINAL STATE (AFTER OPERATION)")
print("="*80)
print()

print(f"All {len(current_states)} products will have:")
print(f"  - 1 primary image (current, preserved)")
print(f"  - 7 shared images (new, with hybrid naming)")
print(f"  - Total: 8 images per product")
print()

print("Image types across all products:")
print(f"  - 1× packshot (pentart-galaxy-flakes-15g-packshot.jpg)")
print(f"  - 3× groupshot (pentart-galaxy-flakes-15g-groupshot.jpg)")
print(f"  - 2× detail (pentart-galaxy-flakes-15g-detail.jpg)")
print(f"  - 1× lifestyle (pentart-galaxy-flakes-15g-lifestyle.jpg)")
print()

# Show what each product would look like
print("Products after restoration:")
print()
for state in current_states:
    before = state['current_images']
    after = before + len(vision_df)
    print(f"  {state['title']}")
    print(f"    Before: {before} image → After: {after} images (+{len(vision_df)})")

print()
print("="*80)
print("SUMMARY")
print("="*80)
print()
print(f"  Products to update: {len(current_states)}")
print(f"  Images to add per product: {len(vision_df)}")
print(f"  Total uploads: {len(vision_df) * len(current_states)}")
print(f"  Images deleted: 0 (NO DELETION)")
print()
print("  All images use:")
print("    - Vision AI verified types (packshot/groupshot/detail/lifestyle)")
print("    - Hybrid filenames (accurate type + SEO structure)")
print("    - German alt text (AI description + SEO keywords)")
print()
print("="*80)
print("** DRY RUN COMPLETE - NO CHANGES MADE **")
print("="*80)
print()
print("Review the plan above. If approved, I'll create the actual restore script.")
