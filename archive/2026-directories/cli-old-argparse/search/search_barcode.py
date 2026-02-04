"""Search for a specific barcode in all Pentart products."""

import sys
from find_and_update_by_barcode import ShopifyClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python search_barcode.py <barcode>")
        sys.exit(1)

    target_barcode = sys.argv[1]

    client = ShopifyClient()
    client.authenticate()

    print(f"\nSearching for barcode {target_barcode}...\n")

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
            productType
            tags
            handle
            onlineStoreUrl
            collections(first: 10) {
              edges {
                node {
                  title
                }
              }
            }
            variants(first: 5) {
              edges {
                node {
                  id
                  sku
                  barcode
                  price
                  inventoryItem {
                    id
                    unitCost {
                      amount
                      currencyCode
                    }
                    countryCodeOfOrigin
                    harmonizedSystemCode
                  }
                  inventoryQuantity
                  metafield(namespace: "custom", key: "farbe") {
                    value
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    cursor = None
    total = 0
    found = None

    while True:
        result = client.execute_graphql(query, {"cursor": cursor})

        # Debug: print result on first iteration
        if cursor is None:
            print(f"First query result keys: {result.keys()}")
            if 'data' in result and result['data'] is not None:
                print(f"Data keys: {result['data'].keys()}")
            if 'errors' in result:
                print(f"Errors: {result['errors']}")
                print("\nGraphQL query failed. Exiting.")
                return

        data = result.get("data", {}).get("products", {})
        edges = data.get("edges", [])

        for edge in edges:
            total += 1
            product = edge["node"]

            for v_edge in product.get("variants", {}).get("edges", []):
                variant = v_edge["node"]
                if variant.get("barcode") == target_barcode:
                    found = (product, variant)
                    print(f"✓ FOUND after checking {total} products!")
                    print(f"\n--- PRODUCT INFORMATION ---")
                    print(f"  Product: {product['title']}")
                    print(f"  Product ID: {product['id']}")
                    print(f"  Product Type: {product.get('productType', 'N/A')}")
                    print(f"  Tags: {', '.join(product.get('tags', [])) if product.get('tags') else 'N/A'}")

                    # Collections
                    collections = product.get('collections', {}).get('edges', [])
                    if collections:
                        collection_names = [c['node']['title'] for c in collections]
                        print(f"  Collections: {', '.join(collection_names)}")
                    else:
                        print(f"  Collections: N/A")

                    # URL
                    url = product.get('onlineStoreUrl')
                    if url:
                        print(f"  URL: {url}")
                    else:
                        handle = product.get('handle', '')
                        print(f"  Handle: {handle}")

                    print(f"\n--- VARIANT INFORMATION ---")
                    print(f"  Variant ID: {variant['id']}")
                    print(f"  SKU: {variant.get('sku', 'MISSING')}")
                    print(f"  Barcode: {variant.get('barcode')}")
                    print(f"  Selling Price: {variant.get('price', 'N/A')}")

                    # Farbe metafield
                    farbe = variant.get('metafield')
                    if farbe and farbe.get('value'):
                        print(f"  Farbe: {farbe['value']}")
                    else:
                        print(f"  Farbe: N/A")

                    # Inventory Item information
                    inv_item = variant.get('inventoryItem', {})
                    if inv_item:
                        print(f"\n--- INVENTORY & COST ---")

                        # Cost
                        unit_cost = inv_item.get('unitCost')
                        if unit_cost:
                            print(f"  Cost: {unit_cost.get('amount', 'N/A')} {unit_cost.get('currencyCode', '')}")
                        else:
                            print(f"  Cost: N/A")

                        # Country of origin
                        country = inv_item.get('countryCodeOfOrigin')
                        print(f"  Country of Origin: {country if country else 'N/A'}")

                        # HS Code
                        hs_code = inv_item.get('harmonizedSystemCode')
                        print(f"  HS Code: {hs_code if hs_code else 'N/A'}")

                        # Inventory quantity
                        inv_qty = variant.get('inventoryQuantity')
                        if inv_qty is not None:
                            print(f"  Inventory Quantity: {inv_qty}")
                        else:
                            print(f"  Inventory Quantity: N/A")

                    return

        if total % 250 == 0:
            print(f"  Checked {total} products...")

        page_info = data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info["endCursor"]

    if not found:
        print(f"✗ Barcode {target_barcode} not found in {total} Pentart products")
        print("The product may not exist in Shopify yet, or may have a different/missing barcode")


if __name__ == "__main__":
    main()
