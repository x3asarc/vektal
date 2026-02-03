"""
Test existing Pentart scraper for Galaxy Flakes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_pentart_products import scrape_pentart_image

# Test with one Galaxy Flakes product
# Galaxy Flakes 15g - Jupiter white: SKU 37047, Barcode 5997412761122

print("Testing existing Pentart scraper with Galaxy Flakes product")
print("=" * 70)
print("Product: Galaxy Flakes 15g - Jupiter white")
print("SKU: 37047")
print("Barcode: 5997412761122")
print()

# Try with SKU
print("Attempting scrape with SKU...")
result_sku = scrape_pentart_image("37047")
if result_sku:
    print(f"✓ SUCCESS with SKU: {result_sku}")
else:
    print("✗ No result with SKU")

print()

# Try with barcode
print("Attempting scrape with barcode...")
result_barcode = scrape_pentart_image("5997412761122")
if result_barcode:
    print(f"✓ SUCCESS with barcode: {result_barcode}")
else:
    print("✗ No result with barcode")

print()
print("=" * 70)
if result_sku or result_barcode:
    print("CONCLUSION: Existing scraper works! No Selenium needed.")
else:
    print("CONCLUSION: Existing scraper doesn't work. Need Selenium.")
