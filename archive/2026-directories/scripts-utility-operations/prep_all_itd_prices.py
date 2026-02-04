import pandas as pd
import os

input_file = 'data/shopify_itd_products.csv'
if not os.path.exists(input_file):
    print(f"Error: {input_file} not found")
    exit(1)

df = pd.read_csv(input_file)

def set_metadata(row):
    handle = str(row.get('Handle', '')).lower()
    sku = str(row.get('SKU', '')).upper()
    title = str(row.get('Title', '')).lower()
    
    # 1. Price Logic
    # A3 check: "a3" in handle/title or SKU ends with 'L'
    if 'a3' in handle or 'a3' in title or sku.endswith('L') or sku.endswith('L-1'):
        row['Price_EUR'] = 1.56
    # A4 check
    elif 'a4' in handle or 'a4' in title:
        row['Price_EUR'] = 1.04
    else:
        # Default fallback
        row['Price_EUR'] = 1.04
        
    # 2. Barcode
    # Use existing barcode from Shopify
    row['ScrapedSKU'] = row.get('Barcode')
    
    # 3. Country
    row['Country'] = 'PL'
    
    # 4. Success Flag (for the push script)
    row['Success'] = 'YES'
    
    return row

df = df.apply(set_metadata, axis=1)

output_file = 'all_itd_prices_update.csv'
df.to_csv(output_file, index=False)

print(f"Prepared {len(df)} ITD products for pricing update.")
print("Price distribution:")
print(df['Price_EUR'].value_counts())
