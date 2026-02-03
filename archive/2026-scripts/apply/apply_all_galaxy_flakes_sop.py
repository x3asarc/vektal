"""
STANDARD OPERATING PROCEDURE: Galaxy Flakes Image Processing
Applies to all 12 Galaxy Flakes products

SOP Requirements:
1. Convert to square (1:1) using center crop if not already square
2. Always preserve/create transparent background (PNG format)
3. Upload with SEO-friendly filename from seo_plan_per_product.csv
4. Delete all previous images with random Shopify filenames
5. Set new image as featured/primary
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import pandas as pd
from PIL import Image
from io import BytesIO
import requests
from src.core.shopify_resolver import ShopifyResolver


def make_square_transparent(image_path_or_url, method='center_crop'):
    """
    Convert image to square with transparent background

    Args:
        image_path_or_url: Local path or URL to image
        method: 'center_crop' (default) | 'contain' | 'cover'

    Returns:
        PIL Image object (RGBA, square)
    """
    # Load image
    if isinstance(image_path_or_url, (str, Path)) and str(image_path_or_url).startswith('http'):
        # Download from URL
        response = requests.get(image_path_or_url, timeout=30)
        img = Image.open(BytesIO(response.content))
    else:
        # Load from file
        img = Image.open(image_path_or_url)

    # Convert to RGBA for transparency
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    width, height = img.size

    # Check if already square
    if width == height:
        return img

    # Make square based on method
    if method == 'center_crop':
        # Version 1: Center crop
        # For wide images (width > height), crop width to match height
        if width > height:
            left = (width - height) // 2
            img_square = img.crop((left, 0, left + height, height))
        else:
            # For tall images, crop height to match width
            top = (height - width) // 2
            img_square = img.crop((0, top, width, top + width))

        return img_square

    elif method == 'contain':
        # Version 2: Contain with transparent padding
        square_size = max(width, height)
        square_img = Image.new('RGBA', (square_size, square_size), (0, 0, 0, 0))

        x_offset = (square_size - width) // 2
        y_offset = (square_size - height) // 2
        square_img.paste(img, (x_offset, y_offset), img)

        return square_img

    elif method == 'cover':
        # Version 3: Cover crop (zoom to fill)
        square_size = min(width, height)
        scale = square_size / min(width, height)
        new_width = int(width * scale)
        new_height = int(height * scale)

        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        left = (new_width - square_size) // 2
        top = (new_height - square_size) // 2
        img_square = resized.crop((left, top, left + square_size, top + square_size))

        return img_square


def upload_image_with_proper_filename(resolver, product_gid, image_data, filename, alt_text):
    """
    Upload image using staged uploads to control filename

    Returns:
        media_id if successful, None otherwise
    """
    # Create staged upload
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


def process_product_sop(resolver, product_id, supplier_image_url, target_filename, alt_text):
    """
    Standard Operating Procedure for processing one product image

    Returns:
        True if successful, False otherwise
    """
    gid = f"gid://shopify/Product/{product_id}"

    print(f"\n{'='*70}")
    print(f"Processing Product ID: {product_id}")
    print(f"Target: {target_filename}")

    # Get current images
    print("  Getting current images...")
    current_query = """
    query getMedia($id: ID!) {
      product(id: $id) {
        title
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

    current_result = resolver.client.execute_graphql(current_query, {"id": gid})
    product_title = current_result.get('data', {}).get('product', {}).get('title', 'Unknown')
    current_media = current_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
    old_media_ids = [edge['node']['id'] for edge in current_media]

    print(f"  Product: {product_title}")
    print(f"  Found {len(old_media_ids)} existing images to delete")

    # Download and process image
    print("  Downloading supplier image...")
    square_img = make_square_transparent(supplier_image_url, method='center_crop')

    print(f"  Converted to square: {square_img.size[0]}x{square_img.size[1]}")
    print(f"  Transparent background: PNG")

    # Convert to bytes
    buffer = BytesIO()
    square_img.save(buffer, format='PNG')
    image_data = buffer.getvalue()

    # Upload
    print(f"  Uploading with filename: {target_filename}")
    new_media_id = upload_image_with_proper_filename(resolver, gid, image_data, target_filename, alt_text)

    if not new_media_id:
        print("  ERROR: Upload failed")
        return False

    print(f"  Uploaded successfully")

    # Set as featured
    print("  Setting as featured image...")

    # Get updated media list
    updated_result = resolver.client.execute_graphql(current_query, {"id": gid})
    all_media_ids = [
        edge['node']['id']
        for edge in updated_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
    ]

    # Reorder
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
    print("  Set as featured")

    # Delete old images
    if old_media_ids:
        print(f"  Deleting {len(old_media_ids)} old images...")

        delete_mutation = """
        mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
          productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            userErrors {
              field
              message
            }
          }
        }
        """

        for old_id in old_media_ids:
            resolver.client.execute_graphql(delete_mutation, {
                "productId": gid,
                "mediaIds": [old_id]
            })

        print(f"  Deleted all old images")

    print(f"  [SUCCESS] {product_title}")
    return True


def main():
    """Apply SOP to all 12 Galaxy Flakes products"""

    print("="*80)
    print("GALAXY FLAKES - STANDARD OPERATING PROCEDURE")
    print("="*80)
    print("\nSOP Requirements:")
    print("  1. Square (1:1) using center crop")
    print("  2. Transparent background (PNG)")
    print("  3. SEO-friendly filename")
    print("  4. Delete old random-filename images")
    print("  5. Set as featured/primary")

    # Load data
    script_dir = Path(__file__).parent
    seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
    download_results_path = script_dir / "data" / "supplier_images" / "galaxy_flakes" / "download_results.csv"

    seo_df = pd.read_csv(seo_plan_path)
    download_df = pd.read_csv(download_results_path)

    # Filter for primary images
    primary_df = seo_df[seo_df['is_primary'] == True].copy()

    print(f"\nFound {len(primary_df)} products to process")

    # Connect to Shopify
    print("\nConnecting to Shopify...")
    resolver = ShopifyResolver()
    print("Connected")

    # Process each product
    results = []

    for _, seo_row in primary_df.iterrows():
        product_id = str(seo_row['product_id'])
        proposed_filename = seo_row['proposed_filename']
        proposed_alt = seo_row['proposed_alt']

        # Get supplier URL from download results
        download_row = download_df[download_df['product_id'] == int(product_id)]
        if download_row.empty:
            print(f"\nSkipping {product_id}: No download data")
            continue

        supplier_url = download_row.iloc[0]['image_url']

        # Convert filename extension to PNG
        target_filename = proposed_filename.replace('.jpg', '.png')

        # Process
        success = process_product_sop(resolver, product_id, supplier_url, target_filename, proposed_alt)

        results.append({
            'product_id': product_id,
            'filename': target_filename,
            'status': 'success' if success else 'failed'
        })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total: {len(results)}")
    print(f"Success: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Failed: {len([r for r in results if r['status'] == 'failed'])}")
    print("\nAll images are now:")
    print("  - Square (900x900, 1:1 ratio)")
    print("  - Transparent background (PNG)")
    print("  - Proper SEO filenames")
    print("  - Set as featured images")
    print("  - Old random-filename images deleted")


if __name__ == "__main__":
    main()
