"""
LIVE PUSH: Saturn Green with Custom Filename
Uses staged uploads to control the filename
"""
import sys
import os
import requests
import mimetypes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver


def apply_saturn_green_with_filename():
    """Apply Saturn green with custom filename using staged uploads"""

    product_id = "6665944203421"
    gid = f"gid://shopify/Product/{product_id}"

    # Image data
    supplier_url = "https://pentacolor.cdn.shoprenter.hu/custom/pentacolor/image/cache/w1719h900/gyerektermekek/37054.png.webp?lastmod=0.1759311936"
    new_alt_text = "Galaxy Flakes 15g - Saturn green - green - detail - Pentart"
    new_filename = "pentart-galaxy-flakes-15g-saturn-green.jpg"

    print("="*80)
    print("LIVE PUSH: Saturn Green with Custom Filename")
    print("="*80)
    print(f"\nProduct ID: {product_id}")
    print(f"Target Filename: {new_filename}")

    # Connect to Shopify
    print("\n[1/5] Connecting to Shopify...")
    resolver = ShopifyResolver()
    print("Connected")

    # Download image from supplier
    print("\n[2/5] Downloading image from Pentacolor CDN...")
    print(f"Source: {supplier_url[:80]}...")

    try:
        response = requests.get(supplier_url, timeout=30)
        response.raise_for_status()
        image_data = response.content
        image_size = len(image_data) / 1024
        print(f"Downloaded: {image_size:.1f} KB")
    except Exception as e:
        print(f"ERROR downloading image: {e}")
        return False

    # Create staged upload
    print("\n[3/5] Creating staged upload...")

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

    # Determine file size and mime type
    file_size = str(len(image_data))
    mime_type = "image/jpeg"  # We'll convert to JPG

    staged_variables = {
        "input": [
            {
                "resource": "IMAGE",
                "filename": new_filename,
                "mimeType": mime_type,
                "fileSize": file_size,
                "httpMethod": "POST"
            }
        ]
    }

    try:
        staged_result = resolver.client.execute_graphql(staged_mutation, staged_variables)

        errors = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors', [])
        if errors:
            print("ERROR creating staged upload:")
            for error in errors:
                print(f"  - {error['field']}: {error['message']}")
            return False

        staged_targets = staged_result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
        if not staged_targets:
            print("ERROR: No staged upload target returned")
            return False

        staged_target = staged_targets[0]
        upload_url = staged_target['url']
        resource_url = staged_target['resourceUrl']
        parameters = {p['name']: p['value'] for p in staged_target['parameters']}

        print(f"Staged upload created")
        print(f"Resource URL: {resource_url[:60]}...")

    except Exception as e:
        print(f"ERROR creating staged upload: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Upload file to staged location
    print("\n[4/5] Uploading to staged location...")

    try:
        # Convert WEBP to JPG if needed
        from PIL import Image
        from io import BytesIO

        img = Image.open(BytesIO(image_data))
        if img.mode in ('RGBA', 'LA', 'P'):
            # Convert to RGB for JPG
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img

        # Save as JPG
        jpg_buffer = BytesIO()
        img.save(jpg_buffer, format='JPEG', quality=95)
        jpg_data = jpg_buffer.getvalue()

        print(f"Converted to JPG: {len(jpg_data) / 1024:.1f} KB")

        # Upload to Shopify's staged location
        files = {'file': (new_filename, jpg_data, mime_type)}
        upload_response = requests.post(upload_url, data=parameters, files=files, timeout=60)
        upload_response.raise_for_status()

        print(f"Uploaded successfully")

    except Exception as e:
        print(f"ERROR uploading file: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Create product media from staged upload
    print("\n[5/5] Attaching image to product...")

    create_media_mutation = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media {
          id
          alt
          mediaContentType
          ... on MediaImage {
            image {
              url
            }
          }
        }
        mediaUserErrors {
          field
          message
        }
      }
    }
    """

    create_media_variables = {
        "productId": gid,
        "media": [
            {
                "originalSource": resource_url,
                "alt": new_alt_text,
                "mediaContentType": "IMAGE"
            }
        ]
    }

    try:
        media_result = resolver.client.execute_graphql(create_media_mutation, create_media_variables)

        media_errors = media_result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors', [])
        if media_errors:
            print("ERROR creating media:")
            for error in media_errors:
                print(f"  - {error['field']}: {error['message']}")
            return False

        media = media_result.get('data', {}).get('productCreateMedia', {}).get('media', [])
        if not media:
            print("ERROR: No media returned")
            return False

        new_media_id = media[0]['id']
        print(f"Image attached to product")
        print(f"Media ID: {new_media_id}")

        # Reorder to make it featured
        print("\nSetting as featured image...")

        # Get all media IDs
        media_query = """
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

        media_list_result = resolver.client.execute_graphql(media_query, {"id": gid})
        all_media_ids = [
            edge['node']['id']
            for edge in media_list_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
        ]

        # Put new image first
        if new_media_id in all_media_ids:
            all_media_ids.remove(new_media_id)
        reordered_ids = [new_media_id] + all_media_ids

        # Reorder
        reorder_mutation = """
        mutation productReorderMedia($id: ID!, $moves: [MoveInput!]!) {
          productReorderMedia(id: $id, moves: $moves) {
            job {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        moves = [{"id": media_id, "newPosition": str(idx)} for idx, media_id in enumerate(reordered_ids)]

        reorder_result = resolver.client.execute_graphql(reorder_mutation, {"id": gid, "moves": moves})

        reorder_errors = reorder_result.get('data', {}).get('productReorderMedia', {}).get('userErrors', [])
        if reorder_errors:
            print("ERROR reordering:")
            for error in reorder_errors:
                print(f"  - {error['field']}: {error['message']}")
        else:
            print("Set as featured image")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify
    print("\nVerifying changes...")
    verify_query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        title
        featuredImage {
          url
          altText
        }
      }
    }
    """

    verify_result = resolver.client.execute_graphql(verify_query, {"id": gid})
    product = verify_result.get('data', {}).get('product')

    if product:
        featured = product['featuredImage']
        print(f"\nProduct: {product['title']}")
        print(f"Featured Image URL: {featured['url']}")
        print(f"Alt Text: {featured['altText']}")

        # Check if filename is in URL
        if new_filename.replace('.jpg', '') in featured['url']:
            print(f"\n[SUCCESS] Custom filename verified in URL!")
        else:
            print(f"\n[INFO] Filename in URL: {featured['url'].split('/')[-1].split('?')[0]}")

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print(f"\n[OK] Image uploaded with filename: {new_filename}")
    print(f"[OK] Set as primary/featured image")
    print(f"[OK] Alt text: {new_alt_text}")

    return True


if __name__ == "__main__":
    success = apply_saturn_green_with_filename()
    sys.exit(0 if success else 1)
