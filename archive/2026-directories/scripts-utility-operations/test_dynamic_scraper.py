import sys
import os
import argparse

# Add parent directory to path so we can import from image_scraper
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from image_scraper import DynamicScraper, parse_price

def test_dynamic(vendor, sku, manual_url=None, test_fallback=False):
    """Test the dynamic scraper for a specific vendor and SKU.

    Args:
        vendor: Vendor/supplier name
        sku: Product SKU
        manual_url: Optional manual URL to test
        test_fallback: If True, also test retailer fallback
    """
    print(f"\n{'='*60}")
    print(f"Testing Dynamic Scraper")
    print(f"Vendor: {vendor}")
    print(f"SKU: {sku}")
    print(f"{'='*60}\n")

    scraper = DynamicScraper()

    # 1. Test site finding
    print("Step 1: Finding supplier site...")
    site_url = scraper.find_supplier_site(vendor, sku, manual_url=manual_url)
    if not site_url:
        print(f"FAILED: Could not find site for {vendor}")
        if test_fallback:
            print("\nStep 2: Trying retailer fallback...")
            retailer_data = scraper.try_retailer_fallback(vendor, sku)
            if retailer_data and retailer_data['image_url']:
                print_results(retailer_data)
            else:
                print("FAILED: Retailer fallback also failed")
        return

    print(f"SUCCESS: Found site {site_url}")

    # 2. Test domain verification
    print("\nStep 2: Verifying domain...")
    from urllib.parse import urlparse
    domain = urlparse(site_url).netloc
    is_verified = scraper.verify_supplier_site(domain, vendor)
    if is_verified:
        print(f"SUCCESS: Domain {domain} verified for {vendor}")
    else:
        print(f"WARNING: Domain {domain} NOT verified for {vendor}")

    # 3. Test generic extraction
    print("\nStep 3: Extracting product data...")
    data = scraper.generic_extract(sku, site_url)

    print_results(data)

    # 4. Test retailer fallback if requested or if confidence is low
    if test_fallback or (data.get('confidence', 0) < 40):
        print("\nStep 4: Testing retailer fallback...")
        retailer_data = scraper.try_retailer_fallback(vendor, sku)
        if retailer_data and retailer_data['image_url']:
            print("\nRetailer Fallback Results:")
            print_results(retailer_data)
        else:
            print("No results from retailer fallback")

def print_results(data):
    """Print extracted data in a formatted way."""
    print("\nExtracted Data:")
    print(f"  Title: {data.get('title', 'N/A')}")
    print(f"  Image URL: {data.get('image_url', 'N/A')}")
    print(f"  Price: €{data.get('price', 'N/A')}")
    print(f"  Confidence Score: {data.get('confidence', 0)}/100")
    print(f"  HS Code: {data.get('hs_code', 'N/A')}")
    print(f"  Country: {data.get('country', 'N/A')}")
    if data.get('source'):
        print(f"  Source: {data.get('source')}")

    if data.get('confidence', 0) < 60:
        print("\n  WARNING: Low confidence. Manual approval would be triggered.")
    else:
        print("\n  SUCCESS: High confidence result!")

def main():
    parser = argparse.ArgumentParser(
        description="Test the Dynamic Scraper against specific vendors and SKUs"
    )
    parser.add_argument(
        "--vendor",
        type=str,
        required=True,
        help="Vendor/supplier name to test"
    )
    parser.add_argument(
        "--sku",
        type=str,
        required=True,
        help="Product SKU to search for"
    )
    parser.add_argument(
        "--manual-url",
        type=str,
        help="Optional manual URL to test instead of automated search"
    )
    parser.add_argument(
        "--test-fallback",
        action="store_true",
        help="Also test retailer fallback logic"
    )

    args = parser.parse_args()

    test_dynamic(args.vendor, args.sku, args.manual_url, args.test_fallback)

if __name__ == "__main__":
    main()
