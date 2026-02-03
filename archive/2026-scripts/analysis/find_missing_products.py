import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

missing_skus = [
    "Grottesche_0026",
    "Views_0238",
    "Views_0009",
    "Views_0167",
    "Views_0154",
    "Views_0111",
    "Views_0084",
    "RC003"
]

def search_product(resolver, sku_base):
    """Try multiple variations of a SKU"""
    variations = [
        sku_base,
        sku_base.lower(),
        sku_base.upper(),
        f"{sku_base.lower()}-3",  # A3 size
        f"{sku_base.lower()}-4",  # A4 size
        f"{sku_base.lower()}-2",  # A2 size
        sku_base.replace("_", "-"),
        sku_base.replace("_", "-").lower(),
    ]

    for variation in variations:
        identifier = {"kind": "sku", "value": variation}
        result = resolver.resolve_identifier(identifier)
        matches = result.get("matches", [])
        if matches:
            return matches[0], variation

    return None, None

print("Initializing Shopify connection...")
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

print("Searching for missing products...\n")

found_products = []
not_found = []

for sku in missing_skus:
    print(f"--- Searching for: {sku} ---")
    product, matched_variation = search_product(resolver, sku)

    if product:
        print(f"[FOUND]")
        print(f"  Title: {product.get('title')}")
        print(f"  Handle: {product.get('handle')}")
        variant = product.get('primary_variant', {})
        print(f"  SKU: {variant.get('sku')}")
        print(f"  Barcode: {variant.get('barcode')}")
        print(f"  Product ID: {product.get('id')}")
        print(f"  Matched variation: {matched_variation}")
        print()
        found_products.append({
            "original_sku": sku,
            "actual_sku": variant.get('sku'),
            "handle": product.get('handle'),
            "product_id": product.get('id'),
        })
    else:
        print(f"[NOT FOUND]")
        print()
        not_found.append(sku)

print("\n" + "="*60)
print(f"SUMMARY: Found {len(found_products)}/{len(missing_skus)}")
print("="*60)

if found_products:
    print("\nFOUND PRODUCTS:")
    for p in found_products:
        print(f"  {p['original_sku']} → {p['actual_sku']} (handle: {p['handle']})")

if not_found:
    print("\nSTILL NOT FOUND:")
    for sku in not_found:
        print(f"  {sku}")
