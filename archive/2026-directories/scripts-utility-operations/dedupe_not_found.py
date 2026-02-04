import pandas as pd

# Read the not_found.csv file
df = pd.read_csv("not_found.csv")

print(f"Total entries before deduplication: {len(df)}")
print()

# Remove duplicates based on Handle and SKU combination
df_deduped = df.drop_duplicates(subset=['Handle', 'SKU'], keep='first')

print(f"Total unique entries after deduplication: {len(df_deduped)}")
print()

# Show the unique entries
print("Unique entries in not_found.csv:")
print("=" * 80)
for idx, row in df_deduped.iterrows():
    print(f"Handle: {row['Handle']}")
    print(f"  SKU: {row['SKU']}")
    print(f"  Title: {row['Title']}")
    print(f"  Vendor: {row['Vendor']}")
    print(f"  URL: {row['URL']}")
    print("-" * 80)

# Save the deduplicated data back to not_found.csv
df_deduped.to_csv("not_found.csv", index=False)
print(f"\nDeduplicated file saved to not_found.csv")
print(f"Removed {len(df) - len(df_deduped)} duplicate entries")
