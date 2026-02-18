"""
Add image to Shopify product.

Usage:
    python utils/add_product_image.py --sku "CBRP104" --image-url "https://example.com/image.jpg"
    python utils/add_product_image.py --sku "CBRP104" --image-url "https://example.com/image.jpg" --alt "Product photo"
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo.seo_generator import ShopifyClient


def add_image(sku, image_url, alt_text=None):
    """Add image to product."""
    print(f"Adding image to SKU: {sku}")
    print(f"Image URL: {image_url}")
    print()

    client = ShopifyClient()
    if not client.authenticate():
        return False

    # Fetch product
    query = """
    query GetProduct($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            title
            vendor
          }
        }
      }
    }
    """

    result = client.execute_graphql(query, {"query": f"sku:{sku}"})

    if not result or not result["data"]["products"]["edges"]:
        print("[ERROR] Product not found")
        return False

    node = result["data"]["products"]["edges"][0]["node"]
    product_id = node["id"]
    title = node["title"]
    vendor = node.get("vendor", "")

    print(f"Product: {title}")
    print(f"Vendor: {vendor}")
    print()

    # Generate alt text if not provided
    if not alt_text:
        alt_text = f"{vendor} {title}".strip()

    print(f"Alt text: {alt_text}")
    print()

    # Add image
    mutation = '''
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media {
          alt
          mediaContentType
          status
        }
        mediaUserErrors {
          field
          message
        }
        product {
          id
          images(first: 10) {
            edges {
              node {
                id
                url
              }
            }
          }
        }
      }
    }
    '''

    variables = {
        'productId': product_id,
        'media': [{
            'originalSource': image_url,
            'alt': alt_text,
            'mediaContentType': 'IMAGE'
        }]
    }

    result = client.execute_graphql(mutation, variables)

    if result:
        errors = result['data']['productCreateMedia'].get('mediaUserErrors', [])
        if errors:
            print(f"[ERROR] Failed to add image:")
            for error in errors:
                print(f"  - {error['message']}")
            return False

        media = result['data']['productCreateMedia']['media']
        product = result['data']['productCreateMedia']['product']

        if media:
            print(f"✅ [SUCCESS] Image added!")
            print(f"   Status: {media[0]['status']}")
            print(f"   Total images: {len(product['images']['edges'])}")
            return True

    print("[ERROR] Unknown error")
    return False


def main():
    parser = argparse.ArgumentParser(description="Add image to product")
    parser.add_argument("--sku", required=True, help="Product SKU")
    parser.add_argument("--image-url", required=True, help="Image URL")
    parser.add_argument("--alt", help="Alt text (optional)")
    args = parser.parse_args()

    success = add_image(args.sku, args.image_url, args.alt)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
