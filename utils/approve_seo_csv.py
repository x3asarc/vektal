"""
Quick utility to approve products in SEO CSV for pushing.

Usage:
    python utils/approve_seo_csv.py data/temp_seo_approval.csv
    python utils/approve_seo_csv.py data/temp_seo_approval.csv --all  # Approve all products
"""

import sys
import csv
import os


def approve_csv(csv_path, approve_all=False):
    """
    Update CSV to set approved=YES for products.

    Args:
        csv_path: Path to CSV file
        approve_all: If True, approve all products. If False, approve only first product.
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    # Read CSV
    rows = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows:
        print("[ERROR] CSV is empty")
        return False

    # Update approved column
    if approve_all:
        for row in rows:
            row['approved'] = 'YES'
        print(f"[OK] Approved {len(rows)} product(s)")
    else:
        # Approve only first product
        rows[0]['approved'] = 'YES'
        print(f"[OK] Approved 1 product: {rows[0].get('product_title', 'Unknown')}")

    # Write back
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Updated: {csv_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python utils/approve_seo_csv.py <csv_path> [--all]")
        return 1

    csv_path = sys.argv[1]
    approve_all = '--all' in sys.argv

    success = approve_csv(csv_path, approve_all)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
