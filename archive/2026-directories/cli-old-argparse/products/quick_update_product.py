"""
Quick script to update a Pentart product using the existing ShopifyClient.
"""

import sys
from image_scraper import ShopifyClient
from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    if len(sys.argv) < 2:
        print("Usage: python quick_update_product.py <barcode>")
        sys.exit(1)

    target_barcode = sys.argv[1]

    print(f"\nUpdating product with barcode: {target_barcode}\n")

    # 1. Get data from database
    db = PentartDatabase(DB_PATH)
    db_product = db.get_by_ean(target_barcode)

    if not db_product:
        print(f"✗ Product not found in database")
        sys.exit(1)

    print(f"Database product:")
    print(f"  Description: {db_product['description']}")
    print(f"  Article Number (SKU): {db_product.get('article_number')}")
    print(f"  Product Weight: {db_product.get('product_weight')} g")
    print()

    # 2. Find in Shopify by SKU or search
    shopify = ShopifyClient()
    shopify.authenticate()
    print("✓ Authenticated with Shopify\n")

    # Try to get by SKU first (from database)
    product_id, variant_id, current_barcode = shopify.get_product_by_sku(db_product.get('article_number'))

    if not product_id:
        print(f"Product not found by SKU {db_product.get('article_number')}")
        print(f"Searching for barcode {target_barcode}...\n")

        # Search by barcode (need to search all products)
        # Use the search script we created earlier
        from search_barcode import ShopifyClient as SearchClient
        search_client = SearchClient()
        search_client.access_token = shopify.access_token

        query = """
        query getPentart($cursor: String) {
          products(first: 250, query: "vendor:Pentart", after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                variants(first: 5) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """

        cursor = None
        found = False

        while not found:
            result = search_client.execute_graphql(query, {"cursor": cursor})
            data = result.get("data", {}).get("products", {})

            for edge in data.get("edges", []):
                product = edge["node"]
                for v_edge in product.get("variants", {}).get("edges", []):
                    variant = v_edge["node"]
                    if variant.get("barcode") == target_barcode:
                        product_id = product["id"]
                        variant_id = variant["id"]
                        current_barcode = variant.get("barcode")
                        print(f"✓ Found: {product['title']}")
                        print(f"  Product ID: {product_id}")
                        print(f"  Variant ID: {variant_id}")
                        print(f"  Current SKU: {variant.get('sku') or 'MISSING'}")
                        print(f"  Current Barcode: {current_barcode}")
                        found = True
                        break
                if found:
                    break

            if not data.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = data["pageInfo"]["endCursor"]

        if not product_id:
            print("✗ Product not found in Shopify")
            sys.exit(1)

    else:
        print(f"✓ Found product by SKU")
        print(f"  Product ID: {product_id}")
        print(f"  Variant ID: {variant_id}")
        print(f"  Current Barcode: {current_barcode}")

    print()

    # 3. Prepare update
    new_sku = db_product.get('article_number')
    new_weight = db_product.get('product_weight')

    variant_update = {"id": variant_id}

    if new_sku:
        variant_update["sku"] = str(new_sku)
        print(f"Will update SKU to: {new_sku}")

    if new_weight:
        variant_update["weight"] = float(new_weight)
        variant_update["weightUnit"] = "GRAMS"
        print(f"Will update weight to: {new_weight} g")

    print()
    confirm = input("Proceed? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled")
        sys.exit(0)

    # 4. Update
    print("\nUpdating...")
    result = shopify.update_product_variants(product_id, [variant_update])

    if result:
        user_errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", [])
        if user_errors:
            print("✗ Update failed:")
            for error in user_errors:
                print(f"  - {error['message']}")
            sys.exit(1)
        else:
            print("✓ Successfully updated!")
            print("\nProduct is now updated with database values.")
    else:
        print("✗ Update failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
