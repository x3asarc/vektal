import sys
import pandas as pd

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Read push_proof.csv
df = pd.read_csv("push_proof.csv")

print(f"Total entries: {len(df)}")

# Check for duplicates based on SKU
duplicates = df[df.duplicated(subset=['SKU'], keep=False)]

if len(duplicates) > 0:
    print(f"\nFound {len(duplicates)} duplicate entries:")
    print(duplicates[['Handle', 'SKU', 'Time']].to_string())

    # Remove duplicates, keeping the most recent (last) entry for each SKU
    df_deduped = df.drop_duplicates(subset=['SKU'], keep='last')

    print(f"\n{'='*60}")
    print(f"After deduplication:")
    print(f"  Original: {len(df)} entries")
    print(f"  Deduplicated: {len(df_deduped)} entries")
    print(f"  Removed: {len(df) - len(df_deduped)} duplicates")

    # Save deduplicated version
    df_deduped.to_csv("push_proof.csv", index=False)
    print(f"\n✅ Saved deduplicated push_proof.csv")
else:
    print("\n✅ No duplicates found - push_proof.csv is clean!")

# Show summary
unique_skus = df.nunique()['SKU']
print(f"\nFinal count: {len(df)} entries with {unique_skus} unique SKUs")
