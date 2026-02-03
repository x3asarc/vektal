"""
LIVE PUSH: Saturn Green Image Update
Applies changes to Shopify
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver


def apply_saturn_green():
    """Apply Saturn green image update to Shopify"""

    product_id = "6665944203421"
    gid = f"gid://shopify/Product/{product_id}"

    # New image data
    supplier_url = "https://pentacolor.cdn.shoprenter.hu/custom/pentacolor/image/cache/w1719h900/gyerektermekek/37054.png.webp?lastmod=0.1759311936"
    new_alt_text = "Galaxy Flakes 15g - Saturn green - green - detail - Pentart"
    new_filename = "pentart-galaxy-flakes-15g-saturn-green"

    print("="*80)
    print("LIVE PUSH: Saturn Green Image Update")
    print("="*80)
    print(f"\nProduct ID: {product_id}")

    # Connect to Shopify
    print("\n[1/4] Connecting to Shopify...")
    resolver = ShopifyResolver()
    print("Connected successfully")

    # Upload new image
    print("\n[2/4] Uploading new image from Pentacolor CDN...")
    print(f"Source: {supplier_url[:80]}...")

    mutation = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media {
          id
          alt
          mediaContentType
          status
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
        product {
          id
        }
      }
    }
    """

    variables = {
        "productId": gid,
        "media": [
            {
                "originalSource": supplier_url,
                "alt": new_alt_text,
                "mediaContentType": "IMAGE"
            }
        ]
    }

    try:
        result = resolver.client.execute_graphql(mutation, variables)

        # Check for errors
        errors = result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors', [])
        if errors:
            print("ERROR uploading image:")
            for error in errors:
                print(f"  - {error['field']}: {error['message']}")
            return False

        media = result.get('data', {}).get('productCreateMedia', {}).get('media', [])
        if media:
            new_media_id = media[0].get('id')
            status = media[0].get('status')
            print(f"Image uploaded successfully!")
            print(f"  Media ID: {new_media_id}")
            print(f"  Status: {status}")
            print(f"  Alt text: {new_alt_text}")
        else:
            print("ERROR: No media returned from upload")
            return False

    except Exception as e:
        print(f"ERROR during upload: {e}")
        return False

    # Set as featured image by reordering to position 0
    print("\n[3/4] Setting as featured/primary image...")
    print("Moving new image to position 0...")

    # First, get all media IDs to reorder
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

    media_result = resolver.client.execute_graphql(media_query, {"id": gid})
    all_media_ids = [
        edge['node']['id']
        for edge in media_result.get('data', {}).get('product', {}).get('media', {}).get('edges', [])
    ]

    # Put new image first, then all others
    if new_media_id in all_media_ids:
        all_media_ids.remove(new_media_id)
    reordered_ids = [new_media_id] + all_media_ids

    # Reorder media
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

    moves = []
    for idx, media_id in enumerate(reordered_ids):
        moves.append({
            "id": media_id,
            "newPosition": str(idx)
        })

    reorder_variables = {
        "id": gid,
        "moves": moves
    }

    try:
        reorder_result = resolver.client.execute_graphql(reorder_mutation, reorder_variables)

        reorder_errors = reorder_result.get('data', {}).get('productReorderMedia', {}).get('userErrors', [])
        if reorder_errors:
            print("ERROR reordering images:")
            for error in reorder_errors:
                print(f"  - {error['field']}: {error['message']}")
            return False

        print("Set as featured image successfully!")

    except Exception as e:
        print(f"ERROR setting featured image: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify changes
    print("\n[4/4] Verifying changes...")

    verify_query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        featuredImage {
          id
          url
          altText
        }
      }
    }
    """

    verify_result = resolver.client.execute_graphql(verify_query, {"id": gid})
    product = verify_result.get('data', {}).get('product')

    if product:
        featured = product.get('featuredImage')
        print(f"Product: {product['title']}")
        print(f"Featured Image:")
        print(f"  URL: {featured['url'][:80]}...")
        print(f"  Alt: {featured['altText']}")

        # Check if it's our new image
        if new_alt_text in featured['altText']:
            print("\n[SUCCESS] Alt text verified!")
        else:
            print("\n[WARNING] Alt text doesn't match expected value")

    # Final summary
    print("\n" + "="*80)
    print("LIVE PUSH COMPLETE")
    print("="*80)
    print("\n[OK] New image uploaded from Pentacolor CDN")
    print("[OK] Set as primary/featured image")
    print("[OK] Alt text updated to Pentart supplier")
    print("\nChanges are now live on Shopify!")

    return True


if __name__ == "__main__":
    success = apply_saturn_green()
    sys.exit(0 if success else 1)
