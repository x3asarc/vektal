"""
Analyze which images were deleted and prepare recovery plan
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

# Paths
script_dir = Path(__file__).parent
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
audit_manifest_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "cache" / "audit_manifest.json"

print("="*80)
print("DELETED IMAGES ANALYSIS")
print("="*80)

# Load SEO plan
seo_df = pd.read_csv(seo_plan_path)

# Separate primary vs non-primary
primary_df = seo_df[seo_df['is_primary'] == True]
non_primary_df = seo_df[seo_df['is_primary'] == False]

print(f"\n[CURRENT STATE]")
print(f"  Primary images (cluster 5): 12 products - UPLOADED ✓")
print(f"  Non-primary images: {len(non_primary_df)} rows across {non_primary_df['cluster_id'].nunique()} clusters - DELETED ✗")

# Load audit manifest
with open(audit_manifest_path, 'r', encoding='utf-8') as f:
    audit_data = json.load(f)

print(f"\n[AUDIT MANIFEST INFO]")
print(f"  Total images cached: {len(audit_data.get('image_records', []))}")
print(f"  Products: {len(set(img['product_id'] for img in audit_data.get('image_records', [])))}")

# Group non-primary by cluster
clusters = defaultdict(list)
for _, row in non_primary_df.iterrows():
    clusters[row['cluster_id']].append(row)

print(f"\n[DELETED SHARED IMAGE CLUSTERS]")
print()

for cluster_id in sorted(clusters.keys()):
    cluster_rows = clusters[cluster_id]
    product_count = len(set(row['product_id'] for row in cluster_rows))
    filename = cluster_rows[0]['proposed_filename']
    shot_type = cluster_rows[0]['shot_type']
    alt_text = cluster_rows[0]['proposed_alt']

    print(f"Cluster {cluster_id}: {shot_type.upper()}")
    print(f"  Proposed filename: {filename}")
    print(f"  Proposed alt: {alt_text[:60]}...")
    print(f"  Affects {product_count} product(s)")

    # List which products
    product_ids = sorted(set(row['product_id'] for row in cluster_rows))
    print(f"  Product IDs: {', '.join(str(pid) for pid in product_ids)}")
    print()

print("="*80)
print("RECOVERY OPTIONS")
print("="*80)
print()
print("[OPTION 1: Re-upload from local cache]")
print("  • Pick representative images from cached files")
print("  • Images will have proper SEO filenames")
print("  • May not perfectly match original clustering")
print()
print("[OPTION 2: Skip shared images for now]")
print("  • Products keep only primary (supplier) images")
print("  • Shared images can be added later manually")
print()
print("[OPTION 3: User provides source images]")
print("  • User specifies which images to use for each cluster")
print("  • Guarantees correct images with SEO filenames")
print()

# Check if we have any cached images we can use
image_cache_dir = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "images"
sample_product = "6665944203421"  # Saturn green
sample_images = list((image_cache_dir / sample_product).glob("*.jpg"))

print(f"[LOCAL CACHE STATUS]")
print(f"  Sample product (Saturn green): {len(sample_images)} cached images")
if sample_images:
    print(f"  Example: {sample_images[0].name}")
print()
print("Note: Cached images have random Shopify filenames and no cluster assignments.")
print("We would need to manually map them to clusters or use any available image as placeholder.")
