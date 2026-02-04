import pandas as pd
import re
from datetime import datetime

# Read the log file
with open("live_run.log", "r", encoding="utf-8") as f:
    log_content = f.read()

# Read existing push_proof.csv
existing_proof = pd.read_csv("push_proof.csv")
existing_skus = set(existing_proof['SKU'].astype(str))
print(f"Existing push_proof.csv has {len(existing_skus)} SKUs")

# Parse the log to find successfully uploaded products
# Pattern: Processing <handle> | SKU: <sku> | Vendor: <vendor>
# Followed by: Uploaded clean image
# And: ImageURL from "Found Image: <url>"

missing_entries = []
log_blocks = log_content.split("--------------------")

for block in log_blocks:
    # Check if this block has a successful upload
    if "Uploaded clean image" in block or "Updated Country:" in block:
        # Extract Handle and SKU from "Processing <handle> | SKU: <sku> | Vendor: <vendor>"
        processing_match = re.search(r'Processing (.+?) \| SKU: (.+?) \| Vendor:', block)
        if not processing_match:
            continue

        handle = processing_match.group(1).strip()
        sku = processing_match.group(2).strip()

        # Skip if already in push_proof.csv
        if str(sku) in existing_skus:
            continue

        # Extract image URL from "Found Image: <url>"
        image_match = re.search(r'Found Image: (.+)', block)
        image_url = image_match.group(1).strip() if image_match else ""

        # Extract barcode from "Found SKU/Barcode: <barcode>" or "Updating barcode to: <barcode>"
        barcode_match = re.search(r'Found SKU/Barcode: (.+)', block)
        if not barcode_match:
            barcode_match = re.search(r'Updating barcode to: (.+)', block)

        scraped_barcode = barcode_match.group(1).strip() if barcode_match else ""
        if scraped_barcode == "None":
            scraped_barcode = ""

        # Only add if we have confirmed upload (not just "Found")
        if "Uploaded clean image" in block or "Updated Country:" in block:
            missing_entries.append({
                "Time": datetime.now().isoformat(),
                "Handle": handle,
                "SKU": sku,
                "ScrapedBarcode": scraped_barcode,
                "ImageURL": image_url,
                "Status": "Success"
            })
            print(f"Found missing: {handle} | {sku}")

print(f"\nFound {len(missing_entries)} missing entries from log")

if missing_entries:
    # Append to push_proof.csv
    df_missing = pd.DataFrame(missing_entries)
    df_missing.to_csv("push_proof.csv", mode='a', header=False, index=False)
    print(f"Added {len(missing_entries)} entries to push_proof.csv")

    # Show what was added
    print("\nAdded entries:")
    for entry in missing_entries:
        print(f"  {entry['Handle']} | {entry['SKU']}")
else:
    print("No missing entries found - push_proof.csv is up to date!")
