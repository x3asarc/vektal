import pandas as pd
from datetime import datetime

# Read the push_proof.csv file
df = pd.read_csv("push_proof.csv")

# Convert Time column to datetime
df['Time'] = pd.to_datetime(df['Time'])

# Sort by time to ensure correct order
df = df.sort_values('Time')

# Calculate time differences between consecutive products
df['TimeDiff'] = df['Time'].diff()

# Filter to only look at today's run (2026-01-26) starting from the live run
today_run = df[df['Time'].dt.date == pd.to_datetime('2026-01-26').date()]

# Get time differences in seconds for today's run (skip the first one as it has no previous)
time_diffs = today_run['TimeDiff'].dt.total_seconds().dropna()

if len(time_diffs) > 0:
    print("Analysis of processing times from today's run:")
    print("=" * 60)
    print(f"Total products processed: {len(today_run)}")
    print(f"Average time per product: {time_diffs.mean():.1f} seconds")
    print(f"Minimum time per product: {time_diffs.min():.1f} seconds")
    print(f"Maximum time per product: {time_diffs.max():.1f} seconds")
    print(f"Median time per product: {time_diffs.median():.1f} seconds")
    print()
    print("Sample of individual processing times (in seconds):")
    print("-" * 60)

    # Show first 20 time differences with product info
    for idx, row in today_run.head(20).iterrows():
        if pd.notna(row['TimeDiff']):
            print(f"{row['Handle'][:40]:40s} | {row['TimeDiff'].total_seconds():5.1f}s")
else:
    print("No timing data available for today's run")
