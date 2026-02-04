import pandas as pd
import os
import re
import argparse
import sys

# Add root to path so we can import from image_scraper later if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def slugify(text):
    """Convert text to a Shopify-compatible handle."""
    if not text or not isinstance(text, str):
        return ""
    # Convert to lowercase
    text = text.lower()
    # Replace non-alphanumeric with hyphens
    text = re.sub(r'[^a-z0-9]+', '-', text)
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    # Strip leading/trailing hyphens
    return text.strip('-')

def amend_handles(completed_csv, export_csv, dry_run=True):
    """Amend handles in completed_csv using titles from export_csv."""
    print(f"Reading completed file: {completed_csv}")
    df_comp = pd.read_csv(completed_csv)
    
    print(f"Reading export file: {export_csv}")
    df_exp = pd.read_csv(export_csv)
    
    # Identify duplicate titles in the export file for disambiguation
    # We use 'Variant SKU' because Handles might already be messy there too
    title_counts = df_exp.groupby('Title').size()
    duplicate_titles = title_counts[title_counts > 1].index.tolist()
    
    if duplicate_titles:
        print(f"Found {len(duplicate_titles)} duplicate titles in export. Disambiguation active.")

    # Create a mapping from SKU to (Title, CleanTitle)
    # We'll use the SKU to find the correct title
    sku_to_title = {}
    for _, row in df_exp.iterrows():
        sku = str(row.get('Variant SKU', '')).strip()
        title = str(row.get('Title', '')).strip()
        if sku and title:
            # Disambiguation logic: if title is duplicated, append SKU
            final_title = title
            if title in duplicate_titles:
                final_title = f"{title} - {sku}"
            sku_to_title[sku] = final_title

    changes = 0
    updated_rows = []
    
    for _, row in df_comp.iterrows():
        sku = str(row.get('SKU', '')).strip()
        old_handle = str(row.get('Handle', '')).strip()
        
        if sku in sku_to_title:
            new_title = sku_to_title[sku]
            new_handle = slugify(new_title)
            
            if old_handle != new_handle:
                print(f"Update SKU {sku}:")
                print(f"  Old: {old_handle}")
                print(f"  New: {new_handle} (from '{new_title}')")
                row['Handle'] = new_handle
                changes += 1
        
        updated_rows.append(row)

    if not dry_run and changes > 0:
        pd.DataFrame(updated_rows).to_csv(completed_csv, index=False)
        print(f"\nSuccessfully amended {changes} handles in {completed_csv}")
    else:
        print(f"\nDry run: {changes} handles would be amended.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amend handles in completed CSV based on export titles.")
    parser.add_argument("completed", help="Path to the 'completed' CSV file (e.g. data/archive/fndeco_batch1_completed.csv)")
    parser.add_argument("--export", required=True, help="Path to the Shopify export CSV file")
    parser.add_argument("--live", action="store_true", help="Perform actual updates (no dry run)")
    
    args = parser.parse_args()
    
    amend_handles(args.completed, args.export, dry_run=not args.live)
