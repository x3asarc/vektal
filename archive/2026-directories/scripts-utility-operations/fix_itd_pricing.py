import pandas as pd
import os
import re

file_path = 'final_push_data_clean.csv'
if not os.path.exists(file_path):
    print(f"Error: {file_path} not found")
    exit(1)

df = pd.read_csv(file_path)

def fix_row(row):
    # Only fix ITD Collection
    if row.get('Vendor') != 'ITD Collection':
        return row
    
    handle = str(row.get('Handle', '')).lower()
    sku = str(row.get('SKU', '')).upper()
    title = str(row.get('Title', '')).lower()
    
    # 1. Price Logic
    # A3 check: "a3" in handle/title or SKU ends with 'L' or 'L-1'
    if 'a3' in handle or 'a3' in title or sku.endswith('L') or sku.endswith('L-1'):
        row['Price'] = 1.56
    # A4 check
    elif 'a4' in handle or 'a4' in title:
        row['Price'] = 1.04
        
    # 2. Barcode/EAN Cleaning
    # ScrapedBarcode (from scraper) is higher quality but often a float
    scraped = str(row.get('ScrapedBarcode', ''))
    if scraped and scraped != 'nan' and scraped.strip() != '':
        # Remove .0 if it's there
        if scraped.endswith('.0'):
            scraped = scraped[:-2]
        row['ScrapedBarcode'] = scraped
    else:
        # Fallback to the original Barcode from Shopify if scraping failed
        orig_barcode = str(row.get('Barcode', ''))
        if orig_barcode and orig_barcode != 'nan' and orig_barcode.strip() != '':
            if orig_barcode.endswith('.0'):
                orig_barcode = orig_barcode[:-2]
            row['ScrapedBarcode'] = orig_barcode

    return row

df = df.apply(fix_row, axis=1)

# Ensure no NaNs in important columns for the push
df['Price'] = df['Price'].fillna(1.04) # Default to A4 price if unknown
df['Country'] = df['Country'].fillna('PL')

df.to_csv('final_push_data_ready.csv', index=False)

print("Pricing and Barcode Fix Complete!")
print("Summary for ITD Collection:")
itd_df = df[df['Vendor'] == 'ITD Collection']
print(itd_df['Price'].value_counts())
print("\nFirst 10 records with ScrapedBarcode and Price:")
print(itd_df[['Handle', 'ScrapedBarcode', 'Price']].head(10))
