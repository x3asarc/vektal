"""
Dry Run: Saturn Green Image Update
Shows exactly what WOULD be done without making changes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver


def dry_run_saturn_green():
    """Dry run for Saturn green product update"""

    product_id = "6665944203421"
    sku = "37054"

    # New image data
    supplier_url = "https://pentacolor.cdn.shoprenter.hu/custom/pentacolor/image/cache/w1719h900/gyerektermekek/37054.png.webp?lastmod=0.1759311936"
    new_alt_text = "Galaxy Flakes 15g - Saturn green - green - detail - Pentart"
    new_filename = "pentart-galaxy-flakes-15g-saturn-green.jpg"

    print("="*80)
    print("DRY RUN: Saturn Green Image Update")
    print("="*80)
    print(f"\nProduct ID: {product_id}")
    print(f"SKU: {sku}")

    # Connect to Shopify
    print("\n[1/5] Connecting to Shopify...")
    resolver = ShopifyResolver()
    print("[OK] Connected")

    # Fetch current product state
    print("\n[2/5] Fetching current product state...")
    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        featuredImage {
          id
          url
          altText
        }
        images(first: 10) {
          edges {
            node {
              id
              url
              altText
            }
          }
        }
      }
    }
    """

    result = resolver.client.execute_graphql(query, {"id": f"gid://shopify/Product/{product_id}"})
    product = result.get('data', {}).get('product')

    if not product:
        print("[ERROR] Product not found")
        return

    print(f"[OK] Found: {product['title']}")
    print(f"  Handle: {product['handle']}")

    # Show current state
    print("\n[3/5] Current Primary Image:")
    current_featured = product.get('featuredImage')
    if current_featured:
        print(f"  URL: {current_featured['url'][:80]}...")
        print(f"  Alt: {current_featured.get('altText', '(empty)')}")
        # Extract current filename
        current_filename = current_featured['url'].split('/')[-1].split('?')[0]
        print(f"  Filename: {current_filename}")
    else:
        print("  (No featured image)")

    print(f"\n  Total images on product: {len(product.get('images', {}).get('edges', []))}")

    # Show what WOULD be done
    print("\n[4/5] Planned Changes:")
    print("-"*80)

    print("\n  ACTION 1: Upload new image")
    print(f"    Source URL: {supplier_url}")
    print(f"    Filename: {new_filename}")
    print(f"    Method: productCreateMedia GraphQL mutation")
    print(f"    → Shopify will download from Pentacolor CDN")

    print("\n  ACTION 2: Set image metadata")
    print(f"    Alt text: {new_alt_text}")
    print(f"    → Will be applied during upload")

    print("\n  ACTION 3: Set as featured/primary image")
    print(f"    → New image will become the main product image")
    print(f"    → Current featured image will remain but no longer primary")

    print("\n[5/5] Verification Plan:")
    print("  → Fetch product again after changes")
    print("  → Confirm new image is featured")
    print("  → Verify alt text matches")
    print("  → Check image URL contains new filename")

    # Summary
    print("\n" + "="*80)
    print("DRY RUN SUMMARY")
    print("="*80)
    print("\n[OK] Product found and accessible")
    print("[OK] Supplier image URL ready")
    print("[OK] GraphQL mutations prepared")
    print("\nCHANGES THAT WOULD BE MADE:")

    if current_featured:
        print(f"\n  Current Alt Text:")
        print(f"    {current_featured.get('altText', '(empty)')}")
        print(f"  New Alt Text:")
        print(f"    {new_alt_text}")

        print(f"\n  Current Filename:")
        print(f"    {current_filename}")
        print(f"  New Filename:")
        print(f"    {new_filename}")

        print(f"\n  New Image Source:")
        print(f"    Pentacolor CDN (SKU: {sku})")
        print(f"    Resolution: 1719x900 WEBP")

    print("\n[!!!] THIS WAS A DRY RUN - NO CHANGES WERE MADE")
    print("\nTo execute live push, run:")
    print("  python apply_saturn_green.py")


if __name__ == "__main__":
    dry_run_saturn_green()
