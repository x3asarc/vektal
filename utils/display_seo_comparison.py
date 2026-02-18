"""
Display SEO content comparison from CSV in a readable format.

Usage:
    python utils/display_seo_comparison.py data/temp_seo_approval.csv
"""

import sys
import csv
import os
import re


def strip_html(html):
    """Strip HTML tags to get plain text."""
    if not html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', html)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def truncate(text, max_length=500):
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def display_comparison(csv_path):
    """Display SEO content comparison from CSV."""
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    # Read CSV
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("[ERROR] CSV is empty")
        return False

    # Display first product (we generate for one at a time in this workflow)
    product = rows[0]

    print()
    print("=" * 70)
    print(f"Product: {product.get('product_title', 'Unknown')}")
    print(f"SKU: {product.get('sku', 'N/A')} | Barcode: {product.get('barcode', 'N/A')} | Vendor: {product.get('vendor', 'N/A')}")
    print("=" * 70)
    print()

    # Meta Title
    print("─" * 70)
    print("META TITLE (50-60 chars for SEO)")
    print("─" * 70)
    print()
    print("CURRENT:")
    current_title = product.get('original_meta_title', '') or product.get('product_title', '')
    print(f"  {current_title}")
    print(f"  ({len(current_title)} chars)")
    print()
    print("NEW:")
    new_title = product.get('generated_meta_title', '')
    print(f"  {new_title}")
    print(f"  ({len(new_title)} chars)")
    print()

    # Meta Description
    print("─" * 70)
    print("META DESCRIPTION (155-160 chars for SEO)")
    print("─" * 70)
    print()
    print("CURRENT:")
    current_desc = product.get('original_meta_description', '(empty)')
    print(f"  {current_desc}")
    if current_desc != '(empty)':
        print(f"  ({len(current_desc)} chars)")
    print()
    print("NEW:")
    new_desc = product.get('generated_meta_description', '')
    print(f"  {new_desc}")
    print(f"  ({len(new_desc)} chars)")
    print()

    # Product Description
    print("─" * 70)
    print("PRODUCT DESCRIPTION")
    print("─" * 70)
    print()
    print("CURRENT:")
    current_html = product.get('original_description_html', '(empty)')
    if current_html and current_html != '(empty)':
        current_text = strip_html(current_html)
        print(f"  {truncate(current_text, 500)}")
        if len(current_text) > 500:
            print(f"  ... (full content in CSV, {len(current_text)} chars)")
    else:
        print("  (empty)")
    print()
    print("NEW:")
    new_html = product.get('generated_description_html', '')
    if new_html:
        new_text = strip_html(new_html)
        print(f"  {truncate(new_text, 500)}")
        if len(new_text) > 500:
            print(f"  ... (full content in CSV, {len(new_text)} chars)")
    print()

    # Validation
    print("─" * 70)
    print("VALIDATION")
    print("─" * 70)
    status = product.get('validation_status', 'UNKNOWN')
    notes = product.get('validation_notes', '')

    if status == 'PASS':
        print(f"  ✓ {status} - {notes}")
    elif status == 'FAIL':
        print(f"  ✗ {status} - {notes}")
    else:
        print(f"  ⚠ {status} - {notes}")
    print()

    print("=" * 70)
    print()

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python utils/display_seo_comparison.py <csv_path>")
        return 1

    csv_path = sys.argv[1]
    success = display_comparison(csv_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
