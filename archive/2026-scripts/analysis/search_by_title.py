import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver

search_terms = [
    ("Grottesche", 1),
    ("Views 0238", 8),
    ("Views 009", 8),  # Try without leading zero
    ("Views 0009", 8),
    ("Views 167", 11),
    ("Views 0167", 11),
    ("Views 154", 3),
    ("Views 0154", 3),
    ("Views 111", 3),
    ("Views 0111", 3),
    ("Views 084", 8),
    ("Views 0084", 8),
    ("RC003", 20),
    ("RC 003", 20),
]

print("Initializing Shopify connection...")
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

print("Searching for products by title...\n")

found = []

for search_term, qty in search_terms:
    print(f"--- Searching for: '{search_term}' (qty: {qty}) ---")
    identifier = {"kind": "title", "value": search_term}
    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    if matches:
        print(f"[FOUND {len(matches)} match(es)]")
        for idx, product in enumerate(matches, 1):
            variant = product.get('primary_variant', {})
            print(f"\n  Match {idx}:")
            print(f"    Title: {product.get('title')}")
            print(f"    Handle: {product.get('handle')}")
            print(f"    SKU: {variant.get('sku')}")
            print(f"    Barcode: {variant.get('barcode')}")
            print(f"    Product ID: {product.get('id')}")
            print(f"    Quantity to set: {qty}")
            found.append({
                "search_term": search_term,
                "title": product.get('title'),
                "handle": product.get('handle'),
                "sku": variant.get('sku'),
                "barcode": variant.get('barcode'),
                "product_id": product.get('id'),
                "quantity": qty
            })
    else:
        print(f"[NOT FOUND]\n")

print("\n" + "="*70)
print(f"SUMMARY: Found {len(found)} products")
print("="*70)

if found:
    print("\nFOUND PRODUCTS - USE THESE:")
    for p in found:
        print(f"\nSearch: '{p['search_term']}' -> Quantity: {p['quantity']}")
        print(f"  Title: {p['title']}")
        print(f"  Handle: {p['handle']}")
        print(f"  SKU: {p['sku']}")
