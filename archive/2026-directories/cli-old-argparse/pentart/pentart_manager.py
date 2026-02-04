"""
Pentart Product Database Manager

Command-line interface for managing Pentart product catalog.

Usage:
    python pentart_manager.py import [excel_file]  - Import Excel catalog to database
    python pentart_manager.py stats                 - Show database statistics
    python pentart_manager.py search <query>        - Search products by article number or description
    python pentart_manager.py sync [--dry-run]      - Bulk update Shopify with database data
"""

import sys
import os
import argparse

# Ensure scripts and utils are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.pentart_db import PentartDatabase


def cmd_import(args):
    """Import Pentart catalog from Excel."""
    from scripts.import_pentart_catalog import import_pentart_catalog

    excel_file = args.excel_file or "Logisztikai tábla 2025 (1) (1).xlsx"

    if not os.path.exists(excel_file):
        print(f"Error: Excel file not found: {excel_file}")
        return 1

    try:
        stats = import_pentart_catalog(excel_file)
        return 0 if stats['errors'] == 0 else 1
    except Exception as e:
        print(f"Error during import: {e}")
        return 1


def cmd_stats(args):
    """Show database statistics."""
    try:
        db = PentartDatabase()
        stats = db.get_stats()

        print("=" * 60)
        print("PENTART DATABASE STATISTICS")
        print("=" * 60)
        print(f"Total products:              {stats['total_products']}")
        print(f"Products with article #:     {stats['products_with_article_number']}")
        print(f"Products with EAN:           {stats['products_with_ean']}")
        print(f"Products with weight:        {stats['products_with_weight']}")
        print("=" * 60)

        # Calculate percentages
        total = stats['total_products']
        if total > 0:
            print("\nData Completeness:")
            print(f"  Article numbers: {stats['products_with_article_number'] / total * 100:.1f}%")
            print(f"  EAN barcodes:    {stats['products_with_ean'] / total * 100:.1f}%")
            print(f"  Weights:         {stats['products_with_weight'] / total * 100:.1f}%")

        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run 'python pentart_manager.py import' first to create the database.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_search(args):
    """Search products by article number or description."""
    query = args.query

    if not query:
        print("Error: Please provide a search query")
        return 1

    try:
        db = PentartDatabase()

        # First try exact article number match
        result = db.get_by_article_number(query)

        if result:
            print("\nFound exact match by article number:")
            print("-" * 60)
            print_product(result)
            return 0

        # Try EAN match
        result = db.get_by_ean(query)

        if result:
            print("\nFound exact match by EAN:")
            print("-" * 60)
            print_product(result)
            return 0

        # Try description search
        results = db.search_by_description(query)

        if results:
            print(f"\nFound {len(results)} products matching '{query}':")
            print("-" * 60)

            for idx, product in enumerate(results[:10], 1):  # Show first 10
                print(f"\n{idx}. {product['description']}")
                print(f"   Article #: {product.get('article_number', 'N/A')}")
                print(f"   EAN:       {product.get('ean', 'N/A')}")
                print(f"   Weight:    {product.get('product_weight', 'N/A')} g")

            if len(results) > 10:
                print(f"\n... and {len(results) - 10} more results")

            return 0
        else:
            print(f"No products found matching '{query}'")
            return 1

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run 'python pentart_manager.py import' first to create the database.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_sync(args):
    """Bulk update Shopify products with database data."""
    from scripts.bulk_update_pentart_shopify import main as sync_main

    # Pass arguments to sync script
    sync_args = ["sync"]
    if args.dry_run:
        sync_args.append("--dry-run")

    # Temporarily modify sys.argv for the sync script
    old_argv = sys.argv
    sys.argv = sync_args

    try:
        sync_main()
        return 0
    except Exception as e:
        print(f"Error during sync: {e}")
        return 1
    finally:
        sys.argv = old_argv


def print_product(product):
    """Print product details in a readable format."""
    print(f"Description:          {product.get('description', 'N/A')}")
    print(f"Article Number (SKU): {product.get('article_number', 'N/A')}")
    print(f"EAN (Barcode):        {product.get('ean', 'N/A')}")
    print(f"Product Weight:       {product.get('product_weight', 'N/A')} g")
    print(f"Density:              {product.get('density', 'N/A')}")
    print(f"Product Volume:       {product.get('product_volume', 'N/A')} ml")

    # Show packaging info if available
    if product.get('inner_qty'):
        print(f"\nPackaging:")
        print(f"  Inner Qty:          {product.get('inner_qty')}")
        print(f"  Inner Weight:       {product.get('inner_weight', 'N/A')} g")
        print(f"  Pcs per Carton:     {product.get('pcs_per_carton', 'N/A')}")
        print(f"  Carton Weight:      {product.get('carton_weight', 'N/A')} g")
        print(f"  Carton Size:        {product.get('carton_size', 'N/A')}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pentart Product Database Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pentart_manager.py import
  python pentart_manager.py import "custom_file.xlsx"
  python pentart_manager.py stats
  python pentart_manager.py search 21047
  python pentart_manager.py search "Mixed Media"
  python pentart_manager.py sync --dry-run
  python pentart_manager.py sync
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Import command
    import_parser = subparsers.add_parser("import", help="Import Excel catalog to database")
    import_parser.add_argument(
        "excel_file",
        nargs="?",
        help="Path to Excel file (default: Logisztikai tábla 2025 (1) (1).xlsx)"
    )

    # Stats command
    subparsers.add_parser("stats", help="Show database statistics")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search products")
    search_parser.add_argument("query", help="Article number or description to search for")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Bulk update Shopify products")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Execute command
    commands = {
        "import": cmd_import,
        "stats": cmd_stats,
        "search": cmd_search,
        "sync": cmd_sync
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
