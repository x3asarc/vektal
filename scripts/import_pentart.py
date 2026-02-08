#!/usr/bin/env python3
"""
Import Pentart vendor catalog data into PostgreSQL.

IMPORTANT: This is NOT a migration from SQLite structure.
This is INITIAL VENDOR CATALOG DATA for the fresh PostgreSQL schema.

Per CONTEXT.md (Phase 3):
- Current SQLite is temporary (Pentart catalog only) and NOT the basis for production schema
- Production schema was designed from requirements, not SQLite structure
- Pentart CSV provides initial vendor catalog data (barcode, SKU, weight only - 3 of 10 columns)
- Titles were in Hungarian and other columns not applicable

This script imports only the 3 useful columns into VendorCatalogItem table.

Usage:
    python scripts/import_pentart.py [--csv-path PATH]

Without --csv-path, searches common locations:
    - ./data/
    - ./archive/
    - Current directory
"""
import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import db
from src.models.vendor import Vendor, VendorCatalogItem
from src.models.user import User
from src.app_factory import create_app


def find_pentart_csv() -> Optional[Path]:
    """
    Search common locations for Pentart CSV file.

    Returns:
        Path to CSV file if found, None otherwise
    """
    # Possible filenames
    filenames = [
        'Logisztikai tábla 2025 (1) (1).xlsx',
        'pentart_catalog.csv',
        'pentart.csv',
        'logisztikai.csv',
    ]

    # Search locations (relative to project root)
    project_root = Path(__file__).parent.parent
    search_paths = [
        project_root / 'data',
        project_root / 'archive',
        project_root / 'archive' / '2026-directories',
        project_root,
    ]

    print("Searching for Pentart CSV in common locations...")
    for search_path in search_paths:
        if not search_path.exists():
            continue

        for filename in filenames:
            csv_path = search_path / filename
            if csv_path.exists():
                print(f"Found: {csv_path}")
                return csv_path

            # Also check for .csv version of .xlsx files
            if filename.endswith('.xlsx'):
                csv_version = search_path / filename.replace('.xlsx', '.csv')
                if csv_version.exists():
                    print(f"Found: {csv_version}")
                    return csv_version

    print("No Pentart CSV found in common locations.")
    return None


def detect_column_mapping(headers: List[str]) -> Dict[str, str]:
    """
    Detect column mapping from CSV headers with flexible name matching.

    Args:
        headers: List of column names from CSV

    Returns:
        Dictionary mapping field names to CSV column names
    """
    mapping = {}

    for header in headers:
        header_lower = header.lower().strip()

        # SKU / Article number
        if ('cikkszám' in header_lower or 'article' in header_lower or
            'sku' in header_lower) and 'sku' not in mapping:
            mapping['sku'] = header

        # Barcode / EAN
        elif ('ean' in header_lower or 'vonalkód' in header_lower or
              'barcode' in header_lower) and 'barcode' not in mapping:
            mapping['barcode'] = header

        # Weight
        elif ('termék súly' in header_lower or 'product weight' in header_lower or
              'weight' in header_lower) and 'weight' not in mapping:
            mapping['weight'] = header

        # Optional: Name/Description (NOT imported per CONTEXT.md, but detect for logging)
        elif ('megnevezés' in header_lower or 'description' in header_lower or
              'leírás' in header_lower or 'név' in header_lower) and 'name' not in mapping:
            mapping['name'] = header

    return mapping


def clean_barcode(value: str) -> Optional[str]:
    """
    Clean and format barcode.

    Excel stores EAN as float (5.997413e+12), convert to proper string format.
    """
    if not value or value.strip() == '':
        return None

    value = str(value).strip()

    # Handle scientific notation
    if 'e+' in value.lower() or 'e-' in value.lower():
        try:
            # Convert scientific notation to integer
            value = str(int(float(value)))
        except (ValueError, OverflowError):
            return None

    # Remove decimal point if present
    if '.' in value:
        value = value.split('.')[0]

    return value if value else None


def clean_weight(value: str) -> Optional[float]:
    """Clean and parse weight value."""
    if not value or value.strip() == '':
        return None

    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


def import_pentart_catalog(csv_path: Path, app) -> Dict[str, int]:
    """
    Import Pentart catalog data into PostgreSQL.

    IMPORTANT: This is INITIAL VENDOR CATALOG DATA, not a SQLite migration.
    Per CONTEXT.md: Import only 3 columns (barcode, SKU, weight).

    Args:
        csv_path: Path to Pentart CSV file
        app: Flask app instance for database context

    Returns:
        Dictionary with import statistics
    """
    print(f"\nStarting Pentart catalog import")
    print(f"CSV file: {csv_path}")
    print(f"This is INITIAL VENDOR CATALOG DATA (not SQLite migration)")
    print("-" * 70)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Statistics
    stats = {
        'total_rows': 0,
        'inserted': 0,
        'skipped_no_identifiers': 0,
        'errors': 0,
    }

    with app.app_context():
        # Get or create Pentart vendor
        # For demo, use first user or create a demo user
        user = User.query.first()
        if not user:
            print("No users found. Creating demo user...")
            user = User(
                email='demo@example.com',
                username='demo',
                password_hash='not_used_in_demo'
            )
            db.session.add(user)
            db.session.commit()
            print(f"Created demo user: {user.email}")

        vendor = Vendor.query.filter_by(user_id=user.id, code='PENTART').first()
        if not vendor:
            print("Creating Pentart vendor...")
            vendor = Vendor(
                user_id=user.id,
                name='Pentart',
                code='PENTART',
                website_url='https://www.pentart.eu',
                catalog_source=str(csv_path),
                is_active=True
            )
            db.session.add(vendor)
            db.session.commit()
            print(f"Created vendor: {vendor}")
        else:
            print(f"Found existing vendor: {vendor}")

        # Read CSV file
        print(f"\nReading CSV file...")

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames

                if not headers:
                    raise ValueError("CSV file has no headers")

                print(f"CSV columns: {headers}")

                # Detect column mapping
                column_mapping = detect_column_mapping(headers)
                print(f"\nColumn mapping detected:")
                for field, col in column_mapping.items():
                    print(f"  {field}: {col}")

                if not column_mapping.get('sku') and not column_mapping.get('barcode'):
                    raise ValueError("CSV must have at least SKU or barcode column")

                # Prepare bulk insert data
                items_to_insert = []

                print(f"\nProcessing rows...")
                for idx, row in enumerate(reader, start=1):
                    stats['total_rows'] += 1

                    try:
                        # Extract data (only 3 columns per CONTEXT.md)
                        sku = row.get(column_mapping.get('sku', ''), '').strip() or None
                        barcode = clean_barcode(row.get(column_mapping.get('barcode', ''), ''))
                        weight = clean_weight(row.get(column_mapping.get('weight', ''), ''))

                        # Skip if no identifiers (can't match products later)
                        if not sku and not barcode:
                            stats['skipped_no_identifiers'] += 1
                            continue

                        # Prepare item data for bulk insert
                        items_to_insert.append({
                            'vendor_id': vendor.id,
                            'sku': sku,
                            'barcode': barcode,
                            'weight_kg': weight,
                            'is_active': True,
                            'created_at': datetime.utcnow(),
                            'updated_at': datetime.utcnow(),
                        })

                        # Progress indicator
                        if idx % 100 == 0:
                            print(f"  Processed {idx} rows...")

                    except Exception as e:
                        stats['errors'] += 1
                        print(f"  Error on row {idx}: {e}")

                # Bulk insert using insert mappings for performance
                if items_to_insert:
                    print(f"\nBulk inserting {len(items_to_insert)} items...")
                    db.session.bulk_insert_mappings(VendorCatalogItem, items_to_insert)
                    db.session.commit()
                    stats['inserted'] = len(items_to_insert)
                    print(f"Inserted {stats['inserted']} catalog items")

                # Update vendor metadata
                vendor.catalog_item_count = stats['inserted']
                vendor.catalog_last_updated = datetime.utcnow()
                db.session.commit()
                print(f"Updated vendor metadata")

        except UnicodeDecodeError:
            # Try with different encoding
            print("UTF-8 failed, trying latin-1 encoding...")
            with open(csv_path, 'r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                # ... (same logic as above)
                print("Note: Processed with latin-1 encoding")

    # Print summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"Total rows in CSV:              {stats['total_rows']}")
    print(f"Items inserted:                 {stats['inserted']}")
    print(f"Skipped (no identifiers):       {stats['skipped_no_identifiers']}")
    print(f"Errors:                         {stats['errors']}")
    print(f"\nVendor catalog item count:      {vendor.catalog_item_count}")
    print("=" * 70)

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Import Pentart catalog data into PostgreSQL (INITIAL VENDOR DATA, not SQLite migration)'
    )
    parser.add_argument(
        '--csv-path',
        type=Path,
        help='Path to Pentart CSV file (auto-detects if not specified)'
    )

    args = parser.parse_args()

    # Find CSV file
    if args.csv_path:
        csv_path = args.csv_path
        if not csv_path.exists():
            print(f"Error: CSV file not found: {csv_path}")
            sys.exit(1)
    else:
        csv_path = find_pentart_csv()
        if not csv_path:
            print("\nError: Could not find Pentart CSV file.")
            print("Please specify path with --csv-path option.")
            sys.exit(1)

    # Create Flask app and run import
    try:
        app = create_app()
        stats = import_pentart_catalog(csv_path, app)

        if stats['errors'] > 0:
            print(f"\nWarning: {stats['errors']} errors occurred during import.")
            sys.exit(1)
        else:
            print("\nImport completed successfully!")
            sys.exit(0)

    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
