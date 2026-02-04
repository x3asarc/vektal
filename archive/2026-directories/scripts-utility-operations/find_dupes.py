import pandas as pd
import sys

def find_duplicates(file_path):
    df = pd.read_csv(file_path)
    if 'Title' not in df.columns:
        print(f"No 'Title' column in {file_path}")
        return
    
    counts = df.groupby('Title').size().reset_index(name='count')
    dupes = counts[counts['count'] > 1]
    
    if dupes.empty:
        print("No duplicate titles found.")
    else:
        print("Duplicate Titles Found:")
        for _, row in dupes.iterrows():
            print(f"- {row['Title']} ({row['count']} occurrences)")
            skus = df[df['Title'] == row['Title']]['Variant SKU'].unique()
            print(f"  SKUs: {', '.join(map(str, skus))}")

if __name__ == "__main__":
    find_duplicates(sys.argv[1])
