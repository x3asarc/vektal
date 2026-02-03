"""
DRY RUN: Restore shared images to Galaxy Flakes products
- Download the 7 images from Juno Rose (which still has them)
- Rename them to proper SEO filenames
- Upload to other Galaxy Flakes products that lost them
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
from src.core.shopify_resolver import ShopifyResolver

print("="*80)
print("DRY RUN - Restore Shared Images from Juno Rose")
print("="*80)
print("\n** THIS IS A DRY RUN - NO CHANGES WILL BE MADE **\n")

# Load SEO plan
script_dir = Path(__file__).parent
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"

seo_df = pd.read_csv(seo_plan_path)

# Connect to Shopify
print("[1/4] Connecting to Shopify...")
resolver = ShopifyResolver()
print("  Connected")

# Get Juno Rose product (source of images)
juno_rose_gid = "gid://shopify/Product/6665942925469"

print("\n[2/4] Getting images from Juno Rose (source product)...")

query = """
query getProduct($id: ID!) {
  product(id: $id) {
    title
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

result = resolver.client.execute_graphql(query, {"id": juno_rose_gid})
juno_rose = result.get('data', {}).get('product')

media_list = juno_rose.get('media', {}).get('edges', [])

# Skip the first image (the new primary we just uploaded)
shared_images = media_list[1:]  # Images 2-8

print(f"  Product: {juno_rose['title']}")
print(f"  Total images: {len(media_list)}")
print(f"  Shared images to restore: {len(shared_images)} (excluding new primary)")
print()

print("  Images found:")
for i, edge in enumerate(shared_images, 1):
    node = edge['node']
    url = node.get('image', {}).get('url', '')
    filename = url.split('/')[-1].split('?')[0]
    alt = node.get('alt', '')
    print(f"    {i}. {filename[:60]}")
    print(f"       Alt: {alt[:70]}")

# Analyze what these images represent based on SEO plan
print("\n[3/4] Analyzing image types from SEO plan...")

# Get non-primary images from SEO plan for reference
non_primary = seo_df[seo_df['is_primary'] == False]

# Get unique clusters and their details
clusters = {}
for cluster_id in non_primary['cluster_id'].unique():
    cluster_rows = non_primary[non_primary['cluster_id'] == cluster_id]
    first_row = cluster_rows.iloc[0]

    clusters[cluster_id] = {
        'filename': first_row['proposed_filename'],
        'alt': first_row['proposed_alt'],
        'shot_type': first_row['shot_type'],
        'product_count': cluster_rows['product_id'].nunique(),
        'product_ids': sorted(cluster_rows['product_id'].unique())
    }

# Sort clusters by product count (most shared first)
sorted_clusters = sorted(clusters.items(), key=lambda x: x[1]['product_count'], reverse=True)

print(f"\n  Found {len(sorted_clusters)} image clusters in SEO plan:")
print()

for cluster_id, info in sorted_clusters[:len(shared_images)]:
    print(f"  Cluster {cluster_id}: {info['shot_type'].upper()}")
    print(f"    Proposed filename: {info['filename']}")
    print(f"    Proposed alt: {info['alt'][:60]}...")
    print(f"    Affects {info['product_count']} products")
    print()

# Get list of products that need these images
print("[4/4] Identifying products that need shared images...")

# Get all 12 Galaxy Flakes products that were processed
primary_df = seo_df[seo_df['is_primary'] == True]
processed_products = primary_df[primary_df['cluster_id'] == 5]  # The ones we already updated

print(f"\n  Products that lost shared images: {len(processed_products)}")
print()

for _, row in processed_products.head(5).iterrows():  # Show first 5 as example
    print(f"    - {row['product_title']} (ID: {row['product_id']})")
print(f"    ... and {len(processed_products) - 5} more" if len(processed_products) > 5 else "")

print()
print("="*80)
print("WHAT WOULD HAPPEN (DRY RUN)")
print("="*80)
print()

print(f"[STEP 1] Download {len(shared_images)} images from Juno Rose")
print(f"  - Save to local directory: data/shared_images/galaxy_flakes/")
print()

print(f"[STEP 2] Rename images to proper SEO filenames")
print(f"  Based on analysis, images would be renamed as:")
print()

# Map the shared images to clusters (we'll map first N images to first N clusters)
for i, (cluster_id, info) in enumerate(sorted_clusters[:len(shared_images)], 1):
    current_name = shared_images[i-1]['node'].get('image', {}).get('url', '').split('/')[-1].split('?')[0]
    new_name = info['filename']
    print(f"    {i}. {current_name[:50]}")
    print(f"       -> {new_name}")
    print(f"       Type: {info['shot_type']}")
    print()

print(f"[STEP 3] Upload renamed images to products")
print()

# For each cluster, show which products would receive it
for i, (cluster_id, info) in enumerate(sorted_clusters[:len(shared_images)], 1):
    print(f"  Image {i}: {info['filename']}")
    print(f"    Would be uploaded to {info['product_count']} products:")

    # Show first 3 products as example
    for pid in info['product_ids'][:3]:
        product_row = seo_df[seo_df['product_id'] == pid].iloc[0]
        print(f"      - {product_row['product_title']}")

    if info['product_count'] > 3:
        print(f"      ... and {info['product_count'] - 3} more products")
    print()

print(f"[STEP 4] Set proper alt text and positioning")
print(f"  - Each image would have its SEO-optimized alt text")
print(f"  - Images would be added after the primary image")
print(f"  - NO existing images would be deleted")
print()

print("="*80)
print("SUMMARY")
print("="*80)
print()
print(f"  Images to restore: {len(shared_images)}")
print(f"  Products to update: {len(processed_products)}")
print(f"  Total uploads: ~{len(shared_images) * len(processed_products)} (shared images × products)")
print()
print("  This will restore the shared images (groupshots, details)")
print("  that were deleted from the other Galaxy Flakes products.")
print()
print("="*80)
print("** DRY RUN COMPLETE - NO CHANGES MADE **")
print("="*80)
