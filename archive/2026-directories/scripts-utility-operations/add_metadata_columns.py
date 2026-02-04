import sys
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

print("Adding metadata columns to existing push_proof.csv...")

# Read current push_proof.csv
push_proof = pd.read_csv("push_proof.csv")
print(f"Current push_proof.csv has {len(push_proof)} entries")

# Read Shopify data for reference
shopify_df = pd.read_csv("shopify_itd_products.csv")
print(f"Shopify data has {len(shopify_df)} ITD products")

# Check what columns we currently have
print(f"\nCurrent columns: {list(push_proof.columns)}")

# Add new columns if they don't exist
if 'Price' not in push_proof.columns:
    push_proof['Price'] = ""
    print("✅ Added 'Price' column")

if 'HSCode' not in push_proof.columns:
    push_proof['HSCode'] = ""
    print("✅ Added 'HSCode' column")

if 'Country' not in push_proof.columns:
    push_proof['Country'] = ""
    print("✅ Added 'Country' column")

if 'ProductTitle' not in push_proof.columns:
    push_proof['ProductTitle'] = ""
    print("✅ Added 'ProductTitle' column")

# Try to fill in data from Shopify where available
print("\nFilling in data from Shopify...")
filled_count = 0

for idx, row in push_proof.iterrows():
    sku = str(row['SKU'])

    # Find matching product in Shopify data
    matching = shopify_df[shopify_df['SKU'] == sku]

    if not matching.empty:
        shopify_product = matching.iloc[0]

        # Fill HSCode from Shopify if available and current is empty
        if pd.isna(row['HSCode']) or row['HSCode'] == "":
            if pd.notna(shopify_product['HSCode']) and shopify_product['HSCode'] != "":
                push_proof.at[idx, 'HSCode'] = str(int(shopify_product['HSCode'])) if isinstance(shopify_product['HSCode'], float) else str(shopify_product['HSCode'])
                filled_count += 1

        # Fill Country from Shopify if available and current is empty
        if pd.isna(row['Country']) or row['Country'] == "":
            if pd.notna(shopify_product['CountryOfOrigin']) and shopify_product['CountryOfOrigin'] != "":
                push_proof.at[idx, 'Country'] = str(shopify_product['CountryOfOrigin'])
                filled_count += 1

        # Fill ProductTitle from Shopify if available and current is empty
        if pd.isna(row['ProductTitle']) or row['ProductTitle'] == "":
            if pd.notna(shopify_product['Title']) and shopify_product['Title'] != "":
                push_proof.at[idx, 'ProductTitle'] = str(shopify_product['Title'])
                filled_count += 1

print(f"✅ Filled {filled_count} data points from Shopify")

# Reorder columns for better readability
column_order = ['Time', 'Handle', 'SKU', 'ScrapedBarcode', 'ImageURL', 'Price', 'HSCode', 'Country', 'ProductTitle', 'Status']
push_proof = push_proof[column_order]

# Backup old version
push_proof_old = pd.read_csv("push_proof.csv")
push_proof_old.to_csv("push_proof_before_metadata.csv", index=False)
print(f"\n✅ Backed up old version to push_proof_before_metadata.csv")

# Save updated version
push_proof.to_csv("push_proof.csv", index=False)
print(f"✅ Saved updated push_proof.csv with new columns")

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Entries: {len(push_proof)}")
print(f"Columns: {list(push_proof.columns)}")
print(f"\n✅ push_proof.csv is ready for metadata updates")
