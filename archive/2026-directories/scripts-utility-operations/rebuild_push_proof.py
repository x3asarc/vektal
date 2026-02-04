import sys
import pandas as pd
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read Shopify data
shopify_df = pd.read_csv("shopify_itd_products.csv")

# Read existing push_proof to preserve non-ITD entries
existing_proof = pd.read_csv("push_proof.csv")

print(f"Current push_proof.csv: {len(existing_proof)} entries")
print(f"Shopify ITD products: {len(shopify_df)} total")

# Filter for ITD Collection products that HAVE images
itd_with_images = shopify_df[
    (shopify_df['Vendor'] == 'ITD Collection') &
    (shopify_df['ImageCount'] > 0)
].copy()

print(f"ITD Collection products with images: {len(itd_with_images)}")

# Get non-ITD entries from existing push_proof
all_itd_skus = set(shopify_df['SKU'].astype(str))
non_itd_entries = existing_proof[~existing_proof['SKU'].astype(str).isin(all_itd_skus)]

print(f"Non-ITD entries to preserve: {len(non_itd_entries)}")

# Create new push_proof entries for ITD products
new_entries = []

for idx, row in itd_with_images.iterrows():
    # Check if this product was in the old push_proof (to preserve original timestamp)
    existing = existing_proof[existing_proof['SKU'] == row['SKU']]

    if not existing.empty:
        # Preserve the original entry
        new_entries.append(existing.iloc[0])
    else:
        # Create new entry for products that were already in Shopify
        new_entries.append({
            "Time": row['UpdatedAt'],  # Use Shopify's UpdatedAt timestamp
            "Handle": row['Handle'],
            "SKU": row['SKU'],
            "ScrapedBarcode": row['Barcode'] if pd.notna(row['Barcode']) else "",
            "ImageURL": row['FirstImageURL'],
            "Status": "Success"
        })

# Combine non-ITD entries with all ITD entries
all_entries = list(non_itd_entries.to_dict('records')) + new_entries

# Sort by timestamp
all_entries_df = pd.DataFrame(all_entries)
all_entries_df['Time'] = pd.to_datetime(all_entries_df['Time'])
all_entries_df = all_entries_df.sort_values('Time')

# Backup old push_proof
existing_proof.to_csv("push_proof_old.csv", index=False)
print(f"\n✅ Backed up old push_proof.csv to push_proof_old.csv")

# Write new push_proof
all_entries_df.to_csv("push_proof.csv", index=False)

print(f"\n{'='*60}")
print(f"NEW push_proof.csv CREATED")
print(f"{'='*60}")
print(f"Total entries: {len(all_entries_df)}")
print(f"  - ITD Collection with images: {len(itd_with_images)}")
print(f"  - Other vendors: {len(non_itd_entries)}")
print(f"\n✅ push_proof.csv is now the master log of ALL completed products")
