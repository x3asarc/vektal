import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_client import ShopifyGraphQLClient

# Product codes and their quantities
product_map = {
    "grottesche_0026": 1,
    "grottesche-0026": 1,
    "views_0142": 8,
    "views-0142": 8,
    "views_0238": 8,
    "views-0238": 8,
    "views_0009": 8,
    "views-0009": 8,
    "views_0167": 11,
    "views-0167": 11,
    "views_0154": 3,
    "views-0154": 3,
    "views_0111": 3,
    "views-0111": 3,
    "tiles_0040": 8,
    "tiles-0040": 8,
    "views_0084": 8,
    "views-0084": 8,
    "time_0028": 8,
    "time-0028": 8,
    "rc003": 20,
    "rc-003": 20,
}

print("Initializing Shopify connection...")
client = ShopifyGraphQLClient()
print("Successfully authenticated with Shopify.\n")

# Search for products with these keywords in title or SKU
search_keywords = ["Views", "Grottesche", "Tiles", "Time", "RC"]

print("Searching all products for keywords...\n")

query = """
query ($query: String!) {
  products(first: 250, query: $query) {
    edges {
      node {
        id
        title
        handle
        variants(first: 10) {
          edges {
            node {
              id
              sku
              barcode
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
"""

found_products = []

for keyword in search_keywords:
    print(f"--- Searching for keyword: {keyword} ---")
    try:
        result = client.execute(query, variables={"query": f"title:*{keyword}* OR sku:*{keyword}*"})
        products = result.get("data", {}).get("products", {}).get("edges", [])

        if products:
            print(f"[FOUND {len(products)} product(s)]")
            for edge in products:
                product = edge["node"]
                for variant_edge in product["variants"]["edges"]:
                    variant = variant_edge["node"]
                    sku = variant.get("sku", "").lower()

                    # Check if this SKU matches any of our target products
                    qty = product_map.get(sku)
                    if qty:
                        print(f"\n  MATCH!")
                        print(f"    Title: {product['title']}")
                        print(f"    Handle: {product['handle']}")
                        print(f"    SKU: {variant['sku']}")
                        print(f"    Barcode: {variant.get('barcode')}")
                        print(f"    Current Inventory: {variant.get('inventoryQuantity')}")
                        print(f"    Target Quantity: {qty}")
                        found_products.append({
                            "title": product["title"],
                            "handle": product["handle"],
                            "sku": variant["sku"],
                            "barcode": variant.get("barcode"),
                            "product_id": product["id"],
                            "variant_id": variant["id"],
                            "current_inventory": variant.get("inventoryQuantity"),
                            "target_quantity": qty
                        })
        else:
            print(f"  No products found")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*70)
print(f"SUMMARY: Found {len(found_products)} matching products")
print("="*70)

if found_products:
    print("\nFOUND PRODUCTS:")
    for p in found_products:
        print(f"\n  SKU: {p['sku']} (Quantity: {p['target_quantity']})")
        print(f"    Title: {p['title']}")
        print(f"    Handle: {p['handle']}")
        print(f"    Current Inventory: {p['current_inventory']}")
else:
    print("\nNo matching products found in the store.")
