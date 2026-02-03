"""
Find products by SKU to get correct product IDs
"""

from src.core.image_scraper import ShopifyClient

SKUS = ["40070", "20738", "13397", "5996546033389", "5997412742664", "5997412709667"]

def main():
    client = ShopifyClient()
    client.authenticate()

    print("\n" + "="*60)
    print("SEARCHING FOR PRODUCTS BY SKU")
    print("="*60)

    for sku in SKUS:
        print(f"\n--- Searching for SKU: {sku} ---")

        query = """
        query searchProducts($query: String!) {
            products(first: 5, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        vendor
                        variants(first: 1) {
                            edges {
                                node {
                                    id
                                    sku
                                    barcode
                                }
                            }
                        }
                        media(first: 5) {
                            edges {
                                node {
                                    ... on MediaImage {
                                        id
                                        image {
                                            url
                                            width
                                            height
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        # Try both SKU and barcode search
        result = client.execute_graphql(query, {"query": f"sku:{sku} OR barcode:{sku}"})

        if not result or "data" not in result:
            print(f"ERROR: Query failed")
            continue

        products = result["data"].get("products", {}).get("edges", [])

        if not products:
            print(f"NOT FOUND")
            continue

        for edge in products:
            product = edge.get("node", {})
            print(f"\nProduct ID: {product.get('id')}")
            print(f"Title: {product.get('title')}")
            print(f"Handle: {product.get('handle')}")
            print(f"Vendor: {product.get('vendor')}")

            variants = product.get("variants", {}).get("edges", [])
            if variants:
                variant = variants[0].get("node", {})
                print(f"SKU: {variant.get('sku')}")
                print(f"Barcode: {variant.get('barcode')}")

            media = product.get("media", {}).get("edges", [])
            print(f"Images: {len(media)}")

            if media:
                for idx, m in enumerate(media, 1):
                    img = m.get("node", {}).get("image", {})
                    if img:
                        print(f"  Image {idx}: {img.get('width')}x{img.get('height')} - {img.get('url', '')[:60]}...")

if __name__ == "__main__":
    main()
