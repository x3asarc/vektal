"""
Import Pentart product catalog from Excel file into SQLite database.

Usage:
    python scripts/import_pentart_catalog.py [excel_file_path]
"""

import sys
import os
import sqlite3
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.paths import DB_PATH
DEFAULT_EXCEL_FILE = "Logisztikai tábla 2025 (1) (1).xlsx"


def clean_ean(value):
    """
    Clean and format EAN barcode.

    Excel stores EAN as float (5.997413e+12), convert to proper string format.
    """
    if pd.isna(value) or value == '':
        return None

    # Convert to string and remove decimal point if present
    ean_str = str(value)

    # Handle scientific notation
    if 'e+' in ean_str.lower():
        # Convert scientific notation to integer
        ean_int = int(float(ean_str))
        ean_str = str(ean_int)

    # Remove any .0 at the end
    if '.' in ean_str:
        ean_str = ean_str.split('.')[0]

    # Strip whitespace
    ean_str = ean_str.strip()

    return ean_str if ean_str else None


def clean_text(value):
    """Clean text fields - strip whitespace and handle NaN."""
    if pd.isna(value) or value == '':
        return None
    return str(value).strip()


def clean_number(value):
    """Clean numeric fields - handle NaN."""
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def import_pentart_catalog(excel_file: str, db_path: str = DB_PATH):
    """
    Import Pentart catalog from Excel into SQLite database.

    Args:
        excel_file: Path to Excel file
        db_path: Path to SQLite database

    Returns:
        Dictionary with import statistics
    """
    print(f"Starting Pentart catalog import from: {excel_file}")
    print(f"Database: {db_path}")
    print("-" * 60)

    # Check if file exists
    if not os.path.exists(excel_file):
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    # Check if database exists
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database file not found: {db_path}")

    # Read Excel file
    print("Reading Excel file...")
    try:
        # Try to read the first sheet
        df = pd.read_excel(excel_file, sheet_name=0)
        print(f"Read {len(df)} rows from Excel")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        raise

    # Map column names (flexible to handle different naming)
    # Looking for columns that match our expected fields
    column_mapping = {}

    for col in df.columns:
        col_lower = str(col).lower()
        if 'id' in col_lower and 'id' not in column_mapping:
            column_mapping['id'] = col
        elif 'megnevezés' in col_lower or 'description' in col_lower or 'leírás' in col_lower:
            column_mapping['description'] = col
        elif 'cikkszám' in col_lower or 'article' in col_lower or 'sku' in col_lower:
            column_mapping['article_number'] = col
        elif 'ean' in col_lower or 'vonalkód' in col_lower or 'barcode' in col_lower:
            column_mapping['ean'] = col
        elif 'termék súly' in col_lower or 'product weight' in col_lower:
            column_mapping['product_weight'] = col
        elif 'sűrűség' in col_lower or 'density' in col_lower:
            column_mapping['density'] = col
        elif 'termék űrtartalom' in col_lower or 'product volume' in col_lower or 'volume' in col_lower:
            column_mapping['product_volume'] = col
        elif 'inner qty' in col_lower or 'belső mennyiség' in col_lower:
            column_mapping['inner_qty'] = col
        elif 'inner súly' in col_lower or 'inner weight' in col_lower:
            column_mapping['inner_weight'] = col
        elif 'db/karton' in col_lower or 'pcs/carton' in col_lower:
            column_mapping['pcs_per_carton'] = col
        elif 'karton súly' in col_lower or 'carton weight' in col_lower:
            column_mapping['carton_weight'] = col
        elif 'karton méret' in col_lower or 'carton size' in col_lower:
            column_mapping['carton_size'] = col
        elif 'csomagolóanyag súly' in col_lower or 'packaging mat weight' in col_lower:
            column_mapping['packaging_mat_weight'] = col

    print(f"\nColumn mapping detected:")
    for key, val in column_mapping.items():
        print(f"  {key}: {val}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Statistics
    stats = {
        'total_rows': len(df),
        'inserted': 0,
        'skipped': 0,
        'errors': 0,
        'missing_article_number': 0,
        'missing_ean': 0,
        'missing_weight': 0
    }

    print("\nProcessing rows...")

    for idx, row in df.iterrows():
        try:
            # Extract and clean data
            product_id = clean_number(row.get(column_mapping.get('id')))
            description = clean_text(row.get(column_mapping.get('description')))
            article_number = clean_text(row.get(column_mapping.get('article_number')))
            ean = clean_ean(row.get(column_mapping.get('ean')))
            product_weight = clean_number(row.get(column_mapping.get('product_weight')))
            density = clean_number(row.get(column_mapping.get('density')))
            product_volume = clean_number(row.get(column_mapping.get('product_volume')))
            inner_qty = clean_text(row.get(column_mapping.get('inner_qty')))
            inner_weight = clean_number(row.get(column_mapping.get('inner_weight')))
            pcs_per_carton = clean_number(row.get(column_mapping.get('pcs_per_carton')))
            carton_weight = clean_number(row.get(column_mapping.get('carton_weight')))
            carton_size = clean_text(row.get(column_mapping.get('carton_size')))
            packaging_mat_weight = clean_number(row.get(column_mapping.get('packaging_mat_weight')))

            # Track missing data
            if not article_number:
                stats['missing_article_number'] += 1
            if not ean:
                stats['missing_ean'] += 1
            if not product_weight:
                stats['missing_weight'] += 1

            # Skip if no description (essential field)
            if not description:
                stats['skipped'] += 1
                continue

            # Insert or replace product
            cursor.execute('''
                INSERT OR REPLACE INTO pentart_products (
                    id, description, article_number, ean, product_weight,
                    density, product_volume, inner_qty, inner_weight,
                    pcs_per_carton, carton_weight, carton_size,
                    packaging_mat_weight, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product_id, description, article_number, ean, product_weight,
                density, product_volume, inner_qty, inner_weight,
                pcs_per_carton, carton_weight, carton_size,
                packaging_mat_weight, datetime.now()
            ))

            stats['inserted'] += 1

            # Progress indicator
            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(df)} rows...")

        except Exception as e:
            stats['errors'] += 1
            print(f"  Error on row {idx + 1}: {e}")

    # Commit changes
    conn.commit()

    # Get final count from database
    cursor.execute("SELECT COUNT(*) FROM pentart_products")
    db_count = cursor.fetchone()[0]

    conn.close()

    # Print summary
    print("\n" + "=" * 60)
    print("IMPORT SUMMARY")
    print("=" * 60)
    print(f"Total rows in Excel:          {stats['total_rows']}")
    print(f"Products inserted/updated:    {stats['inserted']}")
    print(f"Rows skipped:                 {stats['skipped']}")
    print(f"Errors:                       {stats['errors']}")
    print(f"Total products in database:   {db_count}")
    print("\nData Quality:")
    print(f"  Missing article numbers:    {stats['missing_article_number']}")
    print(f"  Missing EAN:                {stats['missing_ean']}")
    print(f"  Missing weight:             {stats['missing_weight']}")
    print("=" * 60)

    return stats


def main():
    """Main entry point."""
    # Get Excel file path from command line or use default
    if len(sys.argv) > 1:
        excel_file = sys.argv[1]
    else:
        excel_file = DEFAULT_EXCEL_FILE

    try:
        stats = import_pentart_catalog(excel_file)

        if stats['errors'] > 0:
            print("\nWarning: Some errors occurred during import.")
            sys.exit(1)
        else:
            print("\nImport completed successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
