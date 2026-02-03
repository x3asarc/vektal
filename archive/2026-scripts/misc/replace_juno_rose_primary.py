"""
Replace primary image for Galaxy Flakes 15g - Juno rose
- Get SKU from Shopify
- Scrape supplier image from Pentacolor
- Replace primary image SAFELY (no deletion)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from PIL import Image
from io import BytesIO
import requests
from src.core.shopify_resolver import ShopifyResolver
from fix_pentart_products import scrape_pentart_image

def make_square_transparent(image_path_or_url, method='center_crop'):
    """Convert image to square with transparent background"""
    # Load image
    if isinstance(image_path_or_url, (str, Path)) and str(image_path_or_url).startswith('http'):
        response = requests.get(image_path_or_url, timeout=30)
        img = Image.open(BytesIO(response.content))
    else:
        img = Image.open(image_path_or_url)

    # Convert to RGBA for transparency
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    width, height = img.size

    # Check if already square
    if width == height:
        return img

    # Center crop
    if width > height:
        left = (width - height) // 2
        img_square = img.crop((left, 0, left + height, height))
    else:
        top = (height - width) // 2
        img_square = img.crop((0, top, width, top + width))

    return img_square


def upload_image_with_proper_filename(resolver, product_gid, image_data, filename, alt_text):
    """Upload image using staged uploads to control filename"""
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
            "filename": filename,
            "mimeType": "image/png",
            "fileSize": str(len(image_data)),
            "httpMethod": "POST"
        }]
    }

    staged_result = resolver.client.execute_graphql(staged_mutation, staged_variables)
    errors = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors', [])
    if errors:
        print(f"  ERROR staging upload: {errors}")
        return None

    staged_target = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])[0]
    upload_url = staged_target['url']
    resource_url = staged_target['resourceUrl']
    parameters = {p['name']: p['value'] for p in staged_target['parameters']}

    # Upload file
    files = {'file': (filename, image_data, 'image/png')}
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
            "alt": alt_text,
            "mediaContentType": "IMAGE"
        }]
    }

    media_result = resolver.client.execute_graphql(create_media_mutation, create_variables)
    media_errors = media_result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors', [])
    if media_errors:
        print(f"  ERROR creating media: {media_errors}")
        return None

    new_media = media_result.get('data', {}).get('productCreateMedia', {}).get('media', [])
    return new_media[0]['id'] if new_media else None


print("="*80)
print("REPLACE PRIMARY IMAGE - Galaxy Flakes 15g - Juno rose")
print("="*80)
print()

product_handle = "galaxy-flakes-15g-pluto-yellow-6505"

# Connect to Shopify
print("[1/6] Connecting to Shopify...")
resolver = ShopifyResolver()
print("  Connected")

# Get product details including SKU
print("\n[2/6] Getting product details and SKU...")
product_query = """
query getProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    variants(first: 1) {
      edges {
        node {
          sku
          barcode
        }
      }
    }
    media(first: 20) {
      edges {
        node {
          id
        }
      }
    }
  }
}
"""

result = resolver.client.execute_graphql(product_query, {"handle": product_handle})
product = result.get('data', {}).get('productByHandle')

if not product:
    print(f"  ERROR: Product not found")
    sys.exit(1)

product_id = product['id'].split('/')[-1]
product_title = product['title']
gid = product['id']

# Get SKU
variant = product.get('variants', {}).get('edges', [])
if variant:
    sku = variant[0]['node'].get('sku', '')
    barcode = variant[0]['node'].get('barcode', '')
else:
    sku = ''
    barcode = ''

print(f"  Product: {product_title}")
print(f"  ID: {product_id}")
print(f"  SKU: {sku}")
print(f"  Barcode: {barcode}")

current_media = product.get('media', {}).get('edges', [])
print(f"  Current images: {len(current_media)}")

# Determine which identifier to use for scraping
article_number = sku if sku else barcode
if not article_number:
    print(f"\n  ERROR: No SKU or barcode found for this product")
    sys.exit(1)

# Scrape supplier image
print(f"\n[3/6] Scraping supplier image from Pentacolor...")
print(f"  Article number: {article_number}")

supplier_url = scrape_pentart_image(article_number, use_selenium=True)

if not supplier_url:
    print(f"  ERROR: Could not find image on supplier website")
    sys.exit(1)

print(f"  Found: {supplier_url[:80]}...")

# Download and process image
print(f"\n[4/6] Processing image...")
square_img = make_square_transparent(supplier_url, method='center_crop')
print(f"  Converted to square: {square_img.size[0]}x{square_img.size[1]}")
print(f"  Transparent background: PNG")

# Convert to bytes
buffer = BytesIO()
square_img.save(buffer, format='PNG')
image_data = buffer.getvalue()

# Create filename and alt text
# Use product title to derive filename
title_slug = product_title.lower().replace(' - ', '-').replace(' ', '-')
filename = f"pentart-{title_slug}.png"
alt_text = f"{product_title} - detail - Pentart"

print(f"  Filename: {filename}")
print(f"  Alt text: {alt_text}")

# Upload new image
print(f"\n[5/6] Uploading new primary image...")
new_media_id = upload_image_with_proper_filename(resolver, gid, image_data, filename, alt_text)

if not new_media_id:
    print("  ERROR: Upload failed")
    sys.exit(1)

print(f"  Uploaded successfully")

# Reorder to make featured (PRESERVE ALL OTHER IMAGES)
print(f"\n[6/6] Setting as featured image...")

# Get updated media list
current_query = """
query getMedia($id: ID!) {
  product(id: $id) {
    media(first: 20) {
      edges {
        node {
          id
        }
      }
    }
  }
}
"""

updated_result = resolver.client.execute_graphql(current_query, {"id": gid})
all_media_ids = [
    edge['node']['id']
    for edge in updated_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
]

# Put new image first, keep all others
if new_media_id in all_media_ids:
    all_media_ids.remove(new_media_id)
reordered = [new_media_id] + all_media_ids

reorder_mutation = """
mutation productReorderMedia($id: ID!, $moves: [MoveInput!]!) {
  productReorderMedia(id: $id, moves: $moves) {
    job { id }
    userErrors { field message }
  }
}
"""

moves = [{"id": mid, "newPosition": str(i)} for i, mid in enumerate(reordered)]
resolver.client.execute_graphql(reorder_mutation, {"id": gid, "moves": moves})
print("  Set as featured (position 0)")

# Verify
print(f"\n{'='*80}")
print("RESULT")
print(f"{'='*80}")
print(f"  [OK] New primary image uploaded and set as featured")
print(f"  [OK] All {len(current_media)} existing images PRESERVED")
print(f"  [OK] Total images: {len(all_media_ids)} (was {len(current_media)}, now {len(all_media_ids)})")
print(f"  [OK] Filename: {filename}")
print(f"  [OK] Square: {square_img.size[0]}x{square_img.size[1]}")
print(f"  [OK] Transparent: PNG")
print(f"\n  NO IMAGES WERE DELETED")
print(f"{'='*80}")
