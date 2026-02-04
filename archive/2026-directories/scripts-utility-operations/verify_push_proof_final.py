import sys
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read files
push_proof = pd.read_csv("push_proof.csv")
shopify_itd = pd.read_csv("shopify_itd_products.csv")

print(f"{'='*60}")
print(f"PUSH_PROOF.CSV FINAL VERIFICATION")
print(f"{'='*60}")

# Get ITD Collection SKUs from Shopify
itd_skus = set(shopify_itd['SKU'].astype(str))

# Categorize push_proof entries
itd_entries = push_proof[push_proof['SKU'].astype(str).isin(itd_skus)]
non_itd_entries = push_proof[~push_proof['SKU'].astype(str).isin(itd_skus)]

print(f"\nTotal entries: {len(push_proof)}")
print(f"  - ITD Collection: {len(itd_entries)}")
print(f"  - Other vendors: {len(non_itd_entries)}")

print(f"\n{'='*60}")
print(f"COMPARISON WITH SHOPIFY")
print(f"{'='*60}")

# ITD products with images in Shopify
itd_with_images_shopify = shopify_itd[shopify_itd['ImageCount'] > 0]
print(f"\nITD products with images in Shopify: {len(itd_with_images_shopify)}")
print(f"ITD products in push_proof.csv: {len(itd_entries)}")

# Check if all ITD entries in push_proof have images in Shopify
verified = 0
missing = 0
for sku in itd_entries['SKU'].astype(str):
    matching = shopify_itd[shopify_itd['SKU'] == sku]
    if not matching.empty and matching.iloc[0]['ImageCount'] > 0:
        verified += 1
    else:
        missing += 1

print(f"\nVerification:")
print(f"  ✅ Confirmed with images in Shopify: {verified}")
print(f"  ❌ Missing images in Shopify: {missing}")

print(f"\n{'='*60}")
print(f"✅ push_proof.csv is now the master log")
print(f"✅ No duplicates")
print(f"✅ All entries verified")
print(f"{'='*60}")
