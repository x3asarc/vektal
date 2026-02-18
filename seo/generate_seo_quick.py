"""
SEO Content Generator - Streamlined Workflow

Generates SEO-optimized content for Shopify products with approval workflow.

Workflow:
1. Fetch products → 2. Generate SEO content → 3. Export to CSV with approval column
4. User reviews/approves → 5. Push approved products to Shopify

Usage:
    # Generate (creates CSV with original + generated content)
    python seo/generate_seo_quick.py --vendor "Pentart" --output data/pentart_seo.csv

    # Review CSV, edit "approved" column to YES for products to update

    # Push approved products to Shopify
    python seo/generate_seo_quick.py --push-csv data/pentart_seo.csv
"""

import os
import sys
import argparse
import csv
import json
import re
from datetime import datetime
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo.seo_generator import SEOContentGenerator, ProductFetcher, ShopifyClient, ProductUpdater


def save_backup(products, backup_dir="data/backups"):
    """Save product data backup before generation."""
    try:
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if len(products) == 1:
            product = products[0]
            title_slug = re.sub(r'[^a-z0-9]+', '_', product.get("title", "unknown")[:30].lower())
            sku = product.get("sku", "no_sku")
            backup_file = f"{backup_dir}/backup_{timestamp}_{title_slug}_SKU{sku}.json"
        else:
            backup_file = f"{backup_dir}/backup_{timestamp}_{len(products)}_products.json"

        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "product_count": len(products),
            "products": [{
                "id": p.get("id"),
                "sku": p.get("sku"),
                "barcode": p.get("barcode"),
                "title": p.get("title"),
                "vendor": p.get("vendor"),
                "product_type": p.get("product_type"),
                "tags": p.get("tags"),
                "description_html": p.get("description_html")
            } for p in products]
        }

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        return True, backup_file
    except Exception as e:
        print(f"[WARNING] Backup failed: {e}")
        return False, None


def strip_html(html):
    """Strip HTML tags to get plain text."""
    if not html:
        return ""
    return re.sub(r'<[^>]+>', ' ', html).strip()


def export_to_csv(results, output_path):
    """
    Export results to CSV with full content (no truncation).

    CSV Structure:
    - Product identification (id, sku, barcode, title, vendor)
    - Original content (full)
    - Generated content (full)
    - Validation results
    - Approval column (PENDING by default)
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "product_id",
            "sku",
            "barcode",
            "product_title",
            "vendor",
            "original_meta_title",
            "original_meta_description",
            "original_description_html",
            "generated_meta_title",
            "generated_meta_description",
            "generated_description_html",
            "validation_status",
            "validation_notes",
            "approved"
        ])
        writer.writeheader()

        for result in results:
            product = result["product"]
            seo = result["seo_content"]
            validation = seo.get("validation", {})

            # Validation status
            if "error" in seo:
                status = "ERROR"
                notes = seo["error"]
            elif validation.get("all_valid"):
                status = "PASS"
                notes = "All validations passed"
            else:
                status = "FAIL"
                notes = "; ".join([
                    f"{k}: {v['message']}"
                    for k, v in validation.items()
                    if k != "all_valid" and not v.get("valid", True)
                ])

            writer.writerow({
                "product_id": product.get("id", ""),
                "sku": product.get("sku", ""),
                "barcode": product.get("barcode", ""),
                "product_title": product.get("title", ""),
                "vendor": product.get("vendor", ""),
                "original_meta_title": product.get("title", ""),  # Shopify uses title as meta title fallback
                "original_meta_description": "",  # Would need metafield fetch
                "original_description_html": product.get("description_html", ""),
                "generated_meta_title": seo.get("meta_title", ""),
                "generated_meta_description": seo.get("meta_description", ""),
                "generated_description_html": seo.get("description_html", ""),
                "validation_status": status,
                "validation_notes": notes,
                "approved": "PENDING"
            })

    return len(results)


def push_from_csv(csv_path, shopify_client):
    """
    Read CSV and push approved products to Shopify.

    Only processes rows where approved = "YES"
    """
    if not os.path.exists(csv_path):
        print(f"[ERROR] CSV file not found: {csv_path}")
        return False

    # Read CSV and filter approved products
    approved_updates = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("approved", "").upper() == "YES":
                approved_updates.append({
                    "product_id": row["product_id"],
                    "product_title": row["product_title"],
                    "sku": row.get("sku", ""),
                    "seo_content": {
                        "meta_title": row["generated_meta_title"],
                        "meta_description": row["generated_meta_description"],
                        "description_html": row["generated_description_html"]
                    }
                })

    if not approved_updates:
        print("[ERROR] No products approved (approved=YES) in CSV")
        return False

    print(f"Found {len(approved_updates)} approved product(s)")
    print()

    # Push to Shopify
    updater = ProductUpdater(shopify_client)
    results = updater.batch_update_products(approved_updates)

    # Trigger quality checks for successful updates
    try:
        from orchestrator.trigger_quality_check import after_seo_update
        for item in results['successful']:
            # Find the SKU for this successful update
            sku = next((u['sku'] for u in approved_updates if u['product_title'] == item['title']), None)
            if sku:
                after_seo_update(sku)
    except Exception as e:
        print(f"[WARNING] Quality check trigger failed: {e}")

    # Generate report
    report_path = f"data/seo_push_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# SEO Push Report\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Source CSV:** {csv_path}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- Total Approved: {results['total']}\n")
        f.write(f"- Successfully Updated: {len(results['successful'])}\n")
        f.write(f"- Failed: {len(results['failed'])}\n\n")

        if results['successful']:
            f.write(f"## Successful Updates\n\n")
            for item in results['successful']:
                f.write(f"- ✓ {item['title']}\n")

        if results['failed']:
            f.write(f"\n## Failed Updates\n\n")
            for item in results['failed']:
                f.write(f"- ✗ {item['title']}\n")
                for error in item.get('errors', []):
                    f.write(f"  - Error: {error.get('message', 'Unknown')}\n")

    print()
    print("=" * 70)
    print(f"PUSH COMPLETE: {len(results['successful'])}/{results['total']} successful")
    print(f"Report saved to: {report_path}")
    print("=" * 70)

    return True


def extract_handle_from_url(url):
    """Extract product handle from Shopify URL."""
    # Handle both full URLs and just handles
    if url.startswith('http'):
        parsed = urlparse(url)
        path = parsed.path
        # Extract handle from /products/handle or /products/handle?variant=123
        if '/products/' in path:
            handle = path.split('/products/')[-1].split('?')[0].split('#')[0]
            return handle.strip('/')
    return url  # Already a handle

def generate_mode(args):
    """Generate SEO content and export to CSV."""
    print("=" * 70)
    print("SEO Content Generator - Generate Mode")
    print("=" * 70)
    print()

    # Initialize Shopify
    print("[1/4] Connecting to Shopify...")
    try:
        shopify = ShopifyClient()
        if not shopify.authenticate():
            print("[ERROR] Authentication failed")
            return 1
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    # Initialize SEO generator
    print("[2/4] Initializing AI generator...")
    try:
        generator = SEOContentGenerator(model_id=args.model)
        print(f"[OK] Using model: {args.model}")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    # Fetch products
    print("[3/4] Fetching products...")
    fetcher = ProductFetcher(shopify)
    products = []

    try:
        if args.url:
            handle = extract_handle_from_url(args.url)
            print(f"   > URL handle: {handle}")
            product = fetcher.fetch_by_handle(handle)
            products = [product] if product else []
        elif args.handle:
            print(f"   > Handle: {args.handle}")
            product = fetcher.fetch_by_handle(args.handle)
            products = [product] if product else []
        elif args.sku:
            print(f"   > SKU: {args.sku}")
            product = fetcher.fetch_by_sku(args.sku)
            products = [product] if product else []
        elif args.barcode:
            print(f"   > Barcode: {args.barcode}")
            product = fetcher.fetch_by_barcode(args.barcode)
            products = [product] if product else []
        elif args.vendor:
            print(f"   > Vendor: {args.vendor}")
            products = fetcher.fetch_by_vendor(args.vendor, limit=args.limit)
        elif args.collection:
            print(f"   > Collection: {args.collection}")
            products = fetcher.fetch_by_collection(args.collection, limit=args.limit)
        elif args.title:
            print(f"   > Title pattern: {args.title}")
            products = fetcher.fetch_by_title(args.title, limit=args.limit)

        if not products:
            print("[ERROR] No products found")
            return 1

        print(f"[OK] Found {len(products)} product(s)")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    # Save backup
    success, backup_file = save_backup(products)
    if success:
        print(f"[OK] Backup saved: {backup_file}")

    # Generate SEO content
    print(f"[4/4] Generating SEO content...")
    print()

    results = []
    for i, product in enumerate(products, 1):
        print(f"   [{i}/{len(products)}] {product['title'][:60]}...")

        try:
            seo_content = generator.generate_seo_content(product, quick_mode=True)
            results.append({"product": product, "seo_content": seo_content})

            if "error" in seo_content:
                print(f"       [ERROR] {seo_content['error']}")
            elif seo_content.get("validation", {}).get("all_valid"):
                print(f"       [OK] Valid")
            else:
                print(f"       [WARNING] Validation issues")
        except Exception as e:
            print(f"       [ERROR] {e}")
            results.append({"product": product, "seo_content": {"error": str(e)}})

    # Export to CSV
    print()
    print("=" * 70)
    print(f"Exporting to: {args.output}")

    count = export_to_csv(results, args.output)

    print(f"[OK] Exported {count} product(s)")
    print()
    print("NEXT STEPS:")
    print(f"1. Open {args.output} in Excel/Google Sheets")
    print(f"2. Review generated content")
    print(f"3. Edit 'approved' column to YES for products to update")
    print(f"4. Run: python seo/generate_seo_quick.py --push-csv {args.output}")
    print("=" * 70)

    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SEO Content Generator - Streamlined Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Mode selection
    parser.add_argument("--push-csv", type=str, metavar="FILE",
                        help="Push mode: Read CSV and push approved products to Shopify")

    # Generate mode filters
    parser.add_argument("--url", type=str, help="Generate mode: Product URL (extracts handle automatically)")
    parser.add_argument("--handle", type=str, help="Generate mode: Product handle from URL")
    parser.add_argument("--sku", type=str, help="Generate mode: Filter by SKU")
    parser.add_argument("--barcode", type=str, help="Generate mode: Filter by barcode")
    parser.add_argument("--vendor", type=str, help="Generate mode: Filter by vendor")
    parser.add_argument("--collection", type=str, help="Generate mode: Filter by collection (handle or GID)")
    parser.add_argument("--title", type=str, help="Generate mode: Filter by title pattern")

    # Generate mode options
    parser.add_argument("--output", type=str, default="data/seo_preview.csv",
                        help="Generate mode: Output CSV file (default: data/seo_preview.csv)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Generate mode: Max products to process (default: 50)")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash",
                        help="Generate mode: Gemini model ID (default: gemini-2.5-flash)")

    args = parser.parse_args()

    # Determine mode
    if args.push_csv:
        # PUSH MODE: Read CSV and push to Shopify
        print("=" * 70)
        print("SEO Content Generator - Push Mode")
        print("=" * 70)
        print()

        # Initialize Shopify
        print("Connecting to Shopify...")
        try:
            shopify = ShopifyClient()
            if not shopify.authenticate():
                print("[ERROR] Authentication failed")
                return 1
        except Exception as e:
            print(f"[ERROR] {e}")
            return 1

        # Push from CSV
        success = push_from_csv(args.push_csv, shopify)
        return 0 if success else 1

    elif any([args.url, args.handle, args.sku, args.barcode, args.vendor, args.collection, args.title]):
        # GENERATE MODE: Fetch products and generate SEO content
        return generate_mode(args)

    else:
        parser.error("Must specify either --push-csv or a filter (--url, --handle, --sku, --barcode, --vendor, --collection, --title)")


if __name__ == "__main__":
    sys.exit(main())
