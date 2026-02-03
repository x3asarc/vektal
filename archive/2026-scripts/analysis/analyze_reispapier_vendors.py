import sys
import os
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

print("Initializing Shopify connection...")
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

print("Fetching all Reispapier products...\n")

#Query all products with "Reispapier" in title
gql = """
query GetAllProducts($first: Int!, $after: String) {
  products(first: $first, after: $after, query: "title:*Reispapier*") {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        handle
        title
        vendor
        variants(first: 50) {
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

all_products = []
has_next = True
cursor = None

while has_next:
    variables = {"first": 250, "after": cursor}
    result = resolver.client.execute_graphql(gql, variables)

    if not result or not result.get("data"):
        break

    data = result["data"]["products"]
    edges = data.get("edges", [])

    for edge in edges:
        product = edge["node"]
        vendor = product.get("vendor", "Unknown")
        for variant_edge in product["variants"]["edges"]:
            variant = variant_edge["node"]
            sku = variant.get("sku", "")
            if sku:  # Only include products with SKUs
                all_products.append({
                    "vendor": vendor,
                    "sku": sku,
                    "title": product["title"],
                    "handle": product["handle"]
                })

    page_info = data.get("pageInfo", {})
    has_next = page_info.get("hasNextPage", False)
    cursor = page_info.get("endCursor")

print(f"Total Reispapier products with SKUs: {len(all_products)}\n")

# Group by vendor and analyze SKU patterns
vendor_patterns = defaultdict(list)
for p in all_products:
    vendor_patterns[p["vendor"]].append(p)

print("="*70)
print("VENDOR ANALYSIS")
print("="*70)

for vendor, products in sorted(vendor_patterns.items()):
    print(f"\nVendor: {vendor}")
    print(f"  Product count: {len(products)}")

    # Show sample SKUs to understand pattern
    sku_samples = [p["sku"] for p in products[:10]]
    print(f"  Sample SKUs:")
    for sku in sku_samples:
        print(f"    - {sku}")

# Now check which vendor each missing product might belong to
missing_skus = ["views_0009", "views_0167", "views_0084", "rc003"]

print("\n" + "="*70)
print("ANALYZING MISSING PRODUCTS")
print("="*70)

for missing_sku in missing_skus:
    print(f"\n{missing_sku}:")
    # Check which vendor has similar SKU patterns
    for vendor, products in vendor_patterns.items():
        # Look for similar SKU patterns in this vendor
        similar = [p for p in products if any([
            missing_sku.lower().split("_")[0] in p["sku"].lower(),
            missing_sku.lower().replace("_", "-") in p["sku"].lower(),
            p["sku"].lower().startswith(missing_sku.lower().split("_")[0])
        ])]

        if similar:
            print(f"  Possible vendor: {vendor} ({len(similar)} similar SKUs)")
            print(f"    Examples:")
            for s in similar[:3]:
                print(f"      - {s['sku']}: {s['title']}")
