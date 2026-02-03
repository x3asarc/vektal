import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

# Target products and their quantities
target_products = {
    "grottesche_0026": 1,
    "views_0142": 8,
    "views_0238": 8,
    "views_0009": 8,
    "views_0167": 11,
    "views_0154": 3,
    "views_0111": 3,
    "tiles_0040": 8,
    "views_0084": 8,
    "time_0028": 8,
    "rc003": 20,
}

print("Initializing Shopify connection...")
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

print("Fetching all products (this may take a moment)...\n")

# Query all products
gql = """
query GetAllProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
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
page = 0

while has_next:
    page += 1
    print(f"Fetching page {page}...")
    variables = {"first": 250, "after": cursor}
    result = resolver.client.execute_graphql(gql, variables)

    if not result or not result.get("data"):
        break

    data = result["data"]["products"]
    edges = data.get("edges", [])

    for edge in edges:
        product = edge["node"]
        for variant_edge in product["variants"]["edges"]:
            variant = variant_edge["node"]
            all_products.append({
                "product_id": product["id"],
                "title": product["title"],
                "handle": product["handle"],
                "vendor": product.get("vendor"),
                "sku": variant.get("sku", ""),
                "barcode": variant.get("barcode", ""),
                "variant_id": variant["id"]
            })

    page_info = data.get("pageInfo", {})
    has_next = page_info.get("hasNextPage", False)
    cursor = page_info.get("endCursor")

print(f"\nTotal products fetched: {len(all_products)}\n")

# Now find matching products
found = []
not_found = []

for target_sku, qty in target_products.items():
    print(f"--- Searching for: {target_sku} (qty: {qty}) ---")
    matches = []

    for p in all_products:
        sku_lower = p["sku"].lower() if p["sku"] else ""
        target_lower = target_sku.lower()

        # Match if:
        # 1. Exact match
        # 2. SKU contains target with underscore or hyphen
        # 3. SKU starts with target and ends with size suffix (-3, -4, etc.)
        if (sku_lower == target_lower or
            sku_lower == target_lower.replace("_", "-") or
            sku_lower.startswith(target_lower + "-") or
            sku_lower.startswith(target_lower.replace("_", "-") + "-")):
            matches.append(p)

    if matches:
        print(f"[FOUND {len(matches)} match(es)]")
        for match in matches:
            print(f"\n  Title: {match['title']}")
            print(f"  Handle: {match['handle']}")
            print(f"  SKU: {match['sku']}")
            print(f"  Barcode: {match['barcode']}")
            print(f"  Quantity to set: {qty}")
            found.append({
                **match,
                "target_quantity": qty,
                "search_sku": target_sku
            })
    else:
        print(f"[NOT FOUND]\n")
        not_found.append(target_sku)

print("\n" + "="*70)
print(f"SUMMARY: Found {len(found)} matching products out of {len(target_products)} targets")
print("="*70)

if found:
    print("\nFOUND PRODUCTS:")
    for p in found:
        print(f"\n  Search: {p['search_sku']} -> Actual SKU: {p['sku']} (Qty: {p['target_quantity']})")
        print(f"    Title: {p['title']}")
        print(f"    Handle: {p['handle']}")

if not_found:
    print(f"\nNOT FOUND ({len(not_found)}):")
    for sku in not_found:
        print(f"  - {sku}")

# Save results to CSV
import csv
if found:
    with open("found_products.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["SKU", "Handle", "Quantity"])
        writer.writeheader()
        for p in found:
            writer.writerow({
                "SKU": p["sku"],
                "Handle": p["handle"],
                "Quantity": p["target_quantity"]
            })
    print("\nResults saved to: found_products.csv")
