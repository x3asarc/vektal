import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

resolver = ShopifyResolver()
print("Getting 1 SKU from 5 different vendors...\n")

# Query products by vendor
vendors_to_test = ["Paperdesigns", "Pentart", "ITD Collection", "Aistcraft", "Stamperia"]
test_products = []

for vendor in vendors_to_test:
    print(f"Fetching {vendor} product...")
    gql = """
    query GetVendorProduct($vendor: String!) {
      products(first: 1, query: $vendor) {
        edges {
          node {
            title
            vendor
            variants(first: 1) {
              edges {
                node {
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

    result = resolver.client.execute_graphql(gql, {"vendor": f"vendor:{vendor}"})
    if result and result.get("data", {}).get("products", {}).get("edges"):
        product = result["data"]["products"]["edges"][0]["node"]
        variant = product["variants"]["edges"][0]["node"]
        test_products.append({
            "vendor": product["vendor"],
            "sku": variant["sku"],
            "barcode": variant.get("barcode"),
            "title": product["title"]
        })
        print(f"  [OK] {variant['sku']}\n")

print("="*70)
print("TEST PRODUCTS:")
print("="*70)
for p in test_products:
    print(f"{p['vendor']}: {p['sku']} - {p['title']}")

import json
with open("test_skus.json", "w", encoding="utf-8") as f:
    json.dump(test_products, f, indent=2, ensure_ascii=False)

print(f"\nSaved to test_skus.json")
