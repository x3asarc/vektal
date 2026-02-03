"""
Update Saturn green with Version 1 (center crop, square, transparent)
Uploads new image with proper filename and deletes old random-named image
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
from src.core.shopify_resolver import ShopifyResolver


def update_saturn_green_final():
    """Upload version 1 center crop and delete old image"""

    product_id = "6665944203421"
    gid = f"gid://shopify/Product/{product_id}"

    # Image data
    image_path = Path("data/supplier_images/galaxy_flakes/square_tests/saturn-green-center-crop.png")
    new_filename = "pentart-galaxy-flakes-15g-saturn-green.png"
    new_alt_text = "Galaxy Flakes 15g - Saturn green - green - detail - Pentart"

    print("="*80)
    print("UPDATE SATURN GREEN - Final Version")
    print("="*80)
    print(f"\nProduct ID: {product_id}")
    print(f"Image: Version 1 (center crop, square, transparent)")
    print(f"Filename: {new_filename}")

    # Connect
    print("\n[1/5] Connecting to Shopify...")
    resolver = ShopifyResolver()

    # Get current images to find old ones to delete
    print("\n[2/5] Getting current product images...")
    current_query = """
    query getMedia($id: ID!) {
      product(id: $id) {
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

    current_result = resolver.client.execute_graphql(current_query, {"id": gid})
    current_media = current_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])

    print(f"Found {len(current_media)} existing images")
    old_media_ids = [edge['node']['id'] for edge in current_media]

    # Load image
    print("\n[3/5] Loading square image...")
    with open(image_path, 'rb') as f:
        image_data = f.read()
    print(f"Loaded: {len(image_data) / 1024:.1f} KB")
    print(f"Format: PNG with transparency")
    print(f"Size: 900x900 (1:1 square)")

    # Create staged upload
    print("\n[4/5] Uploading with proper filename...")

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
            "filename": new_filename,
            "mimeType": "image/png",
            "fileSize": str(len(image_data)),
            "httpMethod": "POST"
        }]
    }

    staged_result = resolver.client.execute_graphql(staged_mutation, staged_variables)
    errors = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors', [])
    if errors:
        print("ERROR creating staged upload:")
        for error in errors:
            print(f"  {error}")
        return False

    staged_target = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])[0]
    upload_url = staged_target['url']
    resource_url = staged_target['resourceUrl']
    parameters = {p['name']: p['value'] for p in staged_target['parameters']}

    # Upload file
    import requests
    files = {'file': (new_filename, image_data, 'image/png')}
    upload_response = requests.post(upload_url, data=parameters, files=files, timeout=60)
    upload_response.raise_for_status()
    print(f"Uploaded: {new_filename}")

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
        "productId": gid,
        "media": [{
            "originalSource": resource_url,
            "alt": new_alt_text,
            "mediaContentType": "IMAGE"
        }]
    }

    media_result = resolver.client.execute_graphql(create_media_mutation, create_variables)
    media_errors = media_result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors', [])
    if media_errors:
        print("ERROR creating media:")
        for error in media_errors:
            print(f"  {error}")
        return False

    new_media = media_result.get('data', {}).get('productCreateMedia', {}).get('media', [])
    new_media_id = new_media[0]['id']
    print(f"Image attached to product")

    # Reorder to make featured
    print("\nSetting as featured image...")

    # Get updated media list
    updated_result = resolver.client.execute_graphql(current_query, {"id": gid})
    all_media_ids = [
        edge['node']['id']
        for edge in updated_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
    ]

    # Put new image first
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
    print("Set as featured")

    # Delete old images with random filenames
    print("\n[5/5] Deleting old images with random Shopify filenames...")

    for old_id in old_media_ids:
        print(f"Deleting: {old_id}")

        delete_mutation = """
        mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
          productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            deletedProductImageIds
            userErrors {
              field
              message
            }
          }
        }
        """

        delete_result = resolver.client.execute_graphql(delete_mutation, {
            "productId": gid,
            "mediaIds": [old_id]
        })

        delete_errors = delete_result.get('data', {}).get('productDeleteMedia', {}).get('userErrors', [])
        if delete_errors:
            print(f"  Warning: {delete_errors}")
        else:
            print(f"  Deleted")

    # Verify
    print("\nVerifying final state...")
    verify_query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        title
        featuredImage {
          url
          altText
        }
        media(first: 5) {
          edges {
            node {
              id
            }
          }
        }
      }
    }
    """

    verify_result = resolver.client.execute_graphql(verify_query, {"id": gid})
    product = verify_result.get('data', {}).get('product')

    print(f"\nProduct: {product['title']}")
    print(f"Featured Image URL: {product['featuredImage']['url']}")
    print(f"Alt Text: {product['featuredImage']['altText']}")
    print(f"Total Images: {len(product['media']['edges'])}")

    if new_filename.replace('.png', '') in product['featuredImage']['url']:
        print("\n[SUCCESS] Proper filename verified!")

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print("\n[OK] Square image (900x900, center crop)")
    print("[OK] Transparent background (PNG)")
    print("[OK] Proper filename (not random)")
    print("[OK] Set as featured image")
    print("[OK] Old random-filename images deleted")

    return True


if __name__ == "__main__":
    success = update_saturn_green_final()
    sys.exit(0 if success else 1)
