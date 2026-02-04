import sys
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read the Shopify verification data
shopify_df = pd.read_csv("shopify_itd_products.csv")

# Read current push_proof.csv
push_proof_df = pd.read_csv("push_proof.csv")

print(f"Original push_proof.csv: {len(push_proof_df)} entries")
print(f"Shopify ITD products: {len(shopify_df)} products")

# Create a set of SKUs that have images in Shopify
shopify_with_images = set(
    shopify_df[shopify_df['ImageCount'] > 0]['SKU'].astype(str)
)

print(f"\nShopify products WITH images: {len(shopify_with_images)}")

# Filter push_proof to only include entries that:
# 1. Have images in Shopify, OR
# 2. Are not ITD Collection (other vendors like FN Deco, Aistcraft, etc.)

# Get all ITD Collection SKUs from Shopify (with or without images)
all_itd_skus = set(shopify_df['SKU'].astype(str))

verified_entries = []
removed_entries = []

for idx, row in push_proof_df.iterrows():
    sku = str(row['SKU'])

    # Check if this is an ITD Collection product
    if sku in all_itd_skus:
        # ITD Collection - only keep if it has images in Shopify
        if sku in shopify_with_images:
            verified_entries.append(row)
            print(f"✅ Verified: {row['Handle']} | {sku}")
        else:
            removed_entries.append(row)
            print(f"❌ Removed (no image in Shopify): {row['Handle']} | {sku}")
    else:
        # Not ITD Collection - keep it (it's from another vendor)
        verified_entries.append(row)
        print(f"✅ Kept (other vendor): {row['Handle']} | {sku}")

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Original entries: {len(push_proof_df)}")
print(f"Verified entries: {len(verified_entries)}")
print(f"Removed entries: {len(removed_entries)}")

if removed_entries:
    print(f"\nRemoved entries:")
    for entry in removed_entries:
        print(f"  - {entry['Handle']} | {entry['SKU']}")

# Create new push_proof.csv with only verified entries
if verified_entries:
    verified_df = pd.DataFrame(verified_entries)

    # Backup old push_proof.csv
    push_proof_df.to_csv("push_proof_backup.csv", index=False)
    print(f"\n✅ Backed up original to push_proof_backup.csv")

    # Write cleaned push_proof.csv
    verified_df.to_csv("push_proof.csv", index=False)
    print(f"✅ Wrote cleaned push_proof.csv with {len(verified_entries)} entries")
else:
    print("\n❌ No verified entries found!")
