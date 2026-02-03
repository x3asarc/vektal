"""
Upload the images we already scraped to Shopify products
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

# Load scraped image results
with open("scraped_images_results.json", "r") as f:
    products = json.load(f)

def upload_image_to_product(product, resolver):
    """Upload image to a Shopify product"""
    barcode = product.get("barcode")
    image_url = product.get("image_url")
    title = product.get("title")

    print(f"\n{'='*70}")
    print(f"Product: {title}")
    print(f"Barcode: {barcode}")
    print(f"{'='*70}")

    # Find product by barcode (currently in SKU field)
    identifier = {"kind": "sku", "value": barcode}
    result = resolver.resolve_identifier(identifier)

    matches = result.get("matches", [])
    if not matches:
        print(f"  ERROR: Product not found")
        return False

    product_data = matches[0]
    product_id = product_data.get("id")
    product_handle = product_data.get("handle")

    print(f"  Found: {product_id}")
    print(f"  Handle: {product_handle}")
    print(f"  Image URL: {image_url}")

    # Upload image using GraphQL
    mutation = """
    mutation productCreateMedia($media: [CreateMediaInput!]!, $productId: ID!) {
      productCreateMedia(media: $media, productId: $productId) {
        media {
          ... on MediaImage {
            id
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

    variables = {
        "productId": product_id,
        "media": [
            {
                "originalSource": image_url,
                "mediaContentType": "IMAGE"
            }
        ]
    }

    print(f"  Uploading image...")

    try:
        response = resolver.client.execute_graphql(mutation, variables)

        if not response:
            print(f"  ERROR: No response from GraphQL")
            return False

        errors = response.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
        if errors:
            print(f"  ERROR: {errors}")
            return False

        media = response.get("data", {}).get("productCreateMedia", {}).get("media", [])
        if media:
            print(f"  OK Image uploaded successfully")
            return True
        else:
            print(f"  WARNING: No media returned")
            return False

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("UPLOADING IMAGES TO SHOPIFY")
    print("="*70)

    resolver = ShopifyResolver()

    # Add barcodes to products (these are currently in the SKU field)
    products[0]["barcode"] = "5996546033389"
    products[1]["barcode"] = "5997412742664"
    products[2]["barcode"] = "5997412709667"

    results = []
    for product in products:
        success = upload_image_to_product(product, resolver)
        results.append((product["sku"], success))

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    for sku, success in results:
        status = "OK SUCCESS" if success else "ERROR FAILED"
        print(f"SKU {sku}: {status}")

    successful = sum(1 for _, s in results if s)
    print(f"\n{successful}/{len(products)} images uploaded")

    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
