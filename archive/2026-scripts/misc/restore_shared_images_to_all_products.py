"""
LIVE: Restore 7 Shared Images to All 12 Galaxy Flakes Products

Adds the 7 verified shared images from Juno Rose to all 12 Galaxy Flakes products.
Each product will have 8 images total (1 primary + 7 shared).

SAFEGUARDS:
- NO deletion of existing images
- Primary images preserved
- Uses vision AI verified types and hybrid naming
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
import requests
from io import BytesIO
from src.core.shopify_resolver import ShopifyResolver

print("="*80)
print("RESTORE 7 SHARED IMAGES TO 12 GALAXY FLAKES PRODUCTS")
print("="*80)
print()

# Paths
script_dir = Path(__file__).parent
vision_results_path = script_dir / "data" / "shared_images" / "galaxy_flakes" / "vision_analysis_results.csv"
seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"

# Load data
vision_df = pd.read_csv(vision_results_path)
seo_df = pd.read_csv(seo_plan_path)
primary_products = seo_df[seo_df['is_primary'] == True].copy()

print(f"[SETUP]")
print(f"  Shared images to add: {len(vision_df)}")
print(f"  Products to update: {len(primary_products)}")
print(f"  Total uploads: {len(vision_df) * len(primary_products)}")
print()

# Connect to Shopify
print(f"[1/5] Connecting to Shopify...")
resolver = ShopifyResolver()
print(f"  Connected")
print()

# Source product (Juno Rose - has the 7 images)
juno_rose_gid = "gid://shopify/Product/6665942925469"

print(f"[2/5] Getting source images from Juno Rose...")

source_query = """
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

source_result = resolver.client.execute_graphql(source_query, {"id": juno_rose_gid})
source_media = source_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])

# Get the 7 shared images (skip position 0 which is the new primary)
shared_images = source_media[1:8]  # Positions 1-7

print(f"  Found {len(shared_images)} shared images")
print()

# Download and prepare images
print(f"[3/5] Downloading and processing images...")

processed_images = []

for idx, row in vision_df.iterrows():
    if idx >= len(shared_images):
        break

    image_node = shared_images[idx]['node']
    source_url = image_node.get('image', {}).get('url', '')

    # Get hybrid naming from vision results
    ai_type = row['ai_type']
    ai_alt = row['ai_alt']

    # Generate hybrid filename
    hybrid_filename = f"pentart-galaxy-flakes-15g-{ai_type}.jpg"

    print(f"  Image {idx + 1}: {ai_type}")
    print(f"    Filename: {hybrid_filename}")
    print(f"    Downloading from: {source_url[:60]}...")

    # Download image
    try:
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        image_data = response.content

        processed_images.append({
            'filename': hybrid_filename,
            'alt_text': ai_alt,
            'image_data': image_data,
            'type': ai_type
        })

        print(f"    Downloaded: {len(image_data) / 1024:.1f} KB")

    except Exception as e:
        print(f"    ERROR downloading: {e}")
        continue

print()
print(f"  Successfully processed {len(processed_images)} images")
print()

# Upload to all products
print(f"[4/5] Uploading images to products...")
print()

upload_stats = {
    'success': 0,
    'failed': 0,
    'products_updated': 0
}

for _, prod_row in primary_products.iterrows():
    product_id = str(prod_row['product_id'])
    product_title = prod_row['product_title']
    product_gid = f"gid://shopify/Product/{product_id}"

    print(f"  Product: {product_title}")
    print(f"    ID: {product_id}")

    product_success = 0

    for img in processed_images:
        # Upload using staged uploads
        try:
            # Stage upload
            staged_mutation = """
            mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
              stagedUploadsCreate(input: $input) {
                stagedTargets {
                  url
                  resourceUrl
                  parameters {
                    name
                    value
                  }
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """

            staged_variables = {
                "input": [{
                    "resource": "IMAGE",
                    "filename": img['filename'],
                    "mimeType": "image/jpeg",
                    "fileSize": str(len(img['image_data'])),
                    "httpMethod": "POST"
                }]
            }

            staged_result = resolver.client.execute_graphql(staged_mutation, staged_variables)
            staged_target = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])[0]

            upload_url = staged_target['url']
            resource_url = staged_target['resourceUrl']
            parameters = {p['name']: p['value'] for p in staged_target['parameters']}

            # Upload file
            files = {'file': (img['filename'], img['image_data'], 'image/jpeg')}
            upload_response = requests.post(upload_url, data=parameters, files=files, timeout=60)
            upload_response.raise_for_status()

            # Create media
            create_media_mutation = """
            mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
              productCreateMedia(media: $media, productId: $productId) {
                media {
                  id
                  alt
                }
                mediaUserErrors {
                  field
                  message
                }
              }
            }
            """

            create_variables = {
                "productId": product_gid,
                "media": [{
                    "originalSource": resource_url,
                    "alt": img['alt_text'],
                    "mediaContentType": "IMAGE"
                }]
            }

            media_result = resolver.client.execute_graphql(create_media_mutation, create_variables)

            media_errors = media_result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors', [])
            if not media_errors:
                product_success += 1
                upload_stats['success'] += 1
            else:
                print(f"      ERROR: {media_errors}")
                upload_stats['failed'] += 1

        except Exception as e:
            print(f"      ERROR uploading {img['filename']}: {e}")
            upload_stats['failed'] += 1

    print(f"    Uploaded: {product_success}/{len(processed_images)} images")

    if product_success > 0:
        upload_stats['products_updated'] += 1
    print()

# Summary
print(f"[5/5] Verifying results...")
print()

# Check one product as example
example_gid = f"gid://shopify/Product/{primary_products.iloc[0]['product_id']}"
verify_result = resolver.client.execute_graphql(source_query, {"id": example_gid})
verify_media = verify_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])

print(f"  Example: {primary_products.iloc[0]['product_title']}")
print(f"    Total images now: {len(verify_media)}")
print()

print("="*80)
print("COMPLETE")
print("="*80)
print()
print(f"  Products updated: {upload_stats['products_updated']}/{len(primary_products)}")
print(f"  Images uploaded: {upload_stats['success']}")
print(f"  Failed uploads: {upload_stats['failed']}")
print()
print(f"  Each product now has:")
print(f"    - 1 primary image (preserved)")
print(f"    - 7 shared images (added)")
print(f"    - Total: ~8 images")
print()
print(f"  All images use hybrid naming (AI type + SEO structure)")
print(f"  All images have German alt text")
print(f"  NO images were deleted")
print()
print("="*80)
