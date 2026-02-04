import pandas as pd
import os
import glob
from datetime import datetime

def sync_to_push_proof():
    proof_file = os.path.join("data", "push_proof.csv")
    
    # Load existing proof or create empty
    if os.path.exists(proof_file):
        df_proof = pd.read_csv(proof_file)
    else:
        df_proof = pd.DataFrame(columns=["Time", "Handle", "SKU", "ScrapedBarcode", "ImageURL", "Price", "HSCode", "Country", "ProductTitle", "Status"])

    # Find the latest Paperdesigns source data
    # We need the product details (Title, Price, etc.) from the dry run result
    dry_run_file = os.path.join("temp", "preview_results.csv")
    if not os.path.exists(dry_run_file):
        print("Could not find temp/preview_results.csv")
        return

    df_source = pd.read_csv(dry_run_file)
    
    # Find the latest image push summary
    image_summaries = glob.glob("image_push_summary_*.csv")
    if not image_summaries:
        print("No image push summaries found.")
        return
    
    latest_img = max(image_summaries, key=os.path.getctime)
    df_img = pd.read_csv(latest_img)
    
    # Filter for successful image pushes
    success_img = df_img[df_img["Status"] == "Success"].copy()
    
    entries = []
    for _, row in success_img.iterrows():
        sku = row["SKU"]
        # Get extra info from source
        source_row = df_source[df_source["SKU"] == sku]
        if not source_row.empty:
            source_row = source_row.iloc[0]
            entries.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Handle": row["Handle"],
                "SKU": sku,
                "ScrapedBarcode": source_row.get("ScrapedBarcode", ""),
                "ImageURL": source_row.get("ImageURL", ""),
                "Price": source_row.get("Price", ""),
                "HSCode": source_row.get("HSCode", ""),
                "Country": source_row.get("Country", "IT"),
                "ProductTitle": source_row.get("Title", ""),
                "Status": "Success"
            })

    if entries:
        df_new = pd.DataFrame(entries)
        # Avoid duplicates if possible (simple SKU check)
        existing_skus = df_proof["SKU"].astype(str).tolist()
        df_new = df_new[~df_new["SKU"].astype(str).isin(existing_skus)]
        
        if not df_new.empty:
            df_new.to_csv(proof_file, mode='a', header=not os.path.exists(proof_file), index=False)
            print(f"Added {len(df_new)} new entries to {proof_file}")
        else:
            print("All entries already in push_proof.csv")
    else:
        print("No new successful entries to add.")

if __name__ == "__main__":
    sync_to_push_proof()
