"""
Verify images on the 3 recently uploaded products
"""

from src.core.image_scraper import ShopifyClient
from src.core.image_verifier import verify_and_fix_product_image

# Product IDs from search
PRODUCTS = [
    {
        "product_id": "gid://shopify/Product/10563043885394",
        "sku": "40070",
        "barcode": "5996546033389",
        "title": "Resin Tint jade 20 ml",
        "vendor": "Pentart"
    },
    {
        "product_id": "gid://shopify/Product/10563042935122",
        "sku": "20738",
        "barcode": "5997412742664",
        "title": "Dekofolie Bronze 14 x 14 cm, 5 Stuck/Packung",
        "vendor": "Pentart"
    },
    {
        "product_id": "gid://shopify/Product/10563042378066",
        "sku": "13397",
        "barcode": "5997412709667",
        "title": "Textilkleber 80 ml",
        "vendor": "Pentart"
    }
]

def main():
    client = ShopifyClient()
    client.authenticate()

    print("\n" + "="*60)
    print("IMAGE VERIFICATION TEST - 3 RECENTLY UPLOADED PRODUCTS")
    print("="*60)

    for product in PRODUCTS:
        print(f"\n{'='*60}")
        print(f"Product: {product['title']}")
        print(f"SKU: {product['sku']}")
        print(f"ID: {product['product_id']}")
        print('='*60)

        # Get product media
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                vendor
                media(first: 10) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                image {
                                    url
                                    width
                                    height
                                }
                                alt
                            }
                        }
                    }
                }
            }
        }
        """

        result = client.execute_graphql(query, {"id": product["product_id"]})

        if not result or "data" not in result:
            print(f"ERROR: Could not fetch product - no result")
            continue

        product_data = result["data"].get("product")

        if not product_data:
            print(f"ERROR: Product not found in Shopify")
            print(f"Result: {result}")
            continue

        media = product_data.get("media", {}).get("edges", [])

        if not media:
            print(f"WARNING: No images found on product")
            continue

        print(f"\nFound {len(media)} image(s)")

        # Verify each image
        for idx, edge in enumerate(media, 1):
            node = edge.get("node", {})
            image = node.get("image", {})
            image_url = image.get("url")
            width = image.get("width")
            height = image.get("height")
            alt = node.get("alt", "")

            print(f"\n--- Image {idx} ---")
            print(f"URL: {image_url[:70]}..." if image_url else "No URL")
            print(f"Size: {width}x{height}")
            print(f"Alt: {alt[:50]}..." if alt else "No alt text")

            if not image_url:
                continue

            # Run verification
            print(f"\n[Verifier] Analyzing image quality...")

            try:
                verification = verify_and_fix_product_image(
                    product_id=product["product_id"],
                    image_url=image_url,
                    product_title=product["title"],
                    vendor=product["vendor"],
                    image_type="product",
                    shopify_client=client,
                    auto_fix=False
                )

                print(f"\n=== VERIFICATION RESULTS ===")

                if verification.get("needs_recrop"):
                    print(f"Status: NEEDS ATTENTION")
                    print(f"Issue: {verification.get('issue', 'Unknown')}")
                    print(f"Recommendation: {verification.get('recommendation', 'None')}")
                    print(f"Confidence: {verification.get('confidence', 0):.0%}")
                else:
                    print(f"Status: OK")
                    print(f"Confidence: {verification.get('confidence', 0):.0%}")

                print(f"===========================")

            except Exception as e:
                print(f"[Verifier] ERROR: {e}")

    print(f"\n{'='*60}")
    print("VERIFICATION TEST COMPLETE")
    print('='*60)

if __name__ == "__main__":
    main()
