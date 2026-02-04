import pandas as pd

df = pd.read_csv("temp/preview_results.csv")

# Filter for success
df_success = df[df["Success"] == "YES"].copy()

# Map columns for metadata push script
df_success["Price_EUR"] = df_success["Price"]
df_success["ScrapedSKU"] = df_success["ScrapedBarcode"]

# Ensure Success is YES
df_success["Success"] = "YES"

# Save for pushing
df_success.to_csv("paperdesigns_push_ready.csv", index=False)
print(f"Prepared {len(df_success)} products in paperdesigns_push_ready.csv")
