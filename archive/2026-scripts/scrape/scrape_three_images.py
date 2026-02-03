"""
Scrape images from Pentart supplier for 3 products
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.pentart_db import PentartDatabase

# Correct SKUs (after fixing barcode issue)
SKUS = [
    "40070",   # Harztönung Jade 20 ml (was barcode 5996546033389)
    "20738",   # Dekofolie Bronze (was barcode 5997412742664)
    "13397",   # Textilkleber 80 ml (was barcode 5997412709667)
]

def main():
    print("="*70)
    print("SCRAPING IMAGES FROM PENTART DATABASE")
    print("="*70)

    db = PentartDatabase()

    for sku in SKUS:
        print(f"\n{'='*70}")
        print(f"SKU: {sku}")
        print(f"{'='*70}")

        # Look up product in Pentart database
        product = db.get_by_article_number(sku)

        if not product:
            print(f"  ERROR: SKU {sku} not found in Pentart database")
            continue

        print(f"  Description: {product.get('description', 'N/A')}")
        print(f"  EAN: {product.get('ean', 'N/A')}")
        print(f"  Weight: {product.get('product_weight', 'N/A')}g")

        # Check if product has image URL in database
        image_url = product.get('image_url')
        if image_url:
            print(f"  Image URL: {image_url}")
        else:
            print(f"  WARNING: No image URL in database")

            # Try to construct Pentart image URL
            # Pentart images are typically at: https://www.pentacolor.eu/products/{sku}/image.jpg
            constructed_url = f"https://www.pentacolor.eu/products/{sku}/image.jpg"
            print(f"  Trying constructed URL: {constructed_url}")

    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
