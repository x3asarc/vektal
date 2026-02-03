"""
Download all Galaxy Flakes primary images from Pentacolor
Uses the enhanced scrape_pentart_image function with Selenium fallback
"""
import os
import sys
import pandas as pd
import requests
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fix_pentart_products import scrape_pentart_image


def download_image(image_url, output_path):
    """Download an image from URL to file"""
    try:
        response = requests.get(image_url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'wb') as f:
            f.write(response.content)

        file_size = os.path.getsize(output_path) / 1024  # KB
        filename = Path(output_path).name
        print(f"    Downloaded: {filename} ({file_size:.1f} KB)")
        return True

    except Exception as e:
        print(f"    Download failed: {e}")
        return False


def main():
    """Download all Galaxy Flakes primary images"""

    # Paths
    script_dir = Path(__file__).parent
    csv_path = script_dir / "data" / "output" / "farbe_metafields_galaxy_flakes.csv"
    seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
    output_dir = script_dir / "data" / "supplier_images" / "galaxy_flakes"

    # Read product data
    print("Reading product data...")
    df = pd.read_csv(csv_path)
    seo_df = pd.read_csv(seo_plan_path)

    # Filter for primary images only
    primary_images = seo_df[seo_df['is_primary'] == True].copy()
    print(f"Found {len(primary_images)} primary images to download")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    for idx, primary_row in primary_images.iterrows():
        product_id = str(primary_row['product_id'])
        target_filename = primary_row['proposed_filename']
        product_title = primary_row['product_title']

        print(f"\n{'='*70}")
        print(f"[{idx-1}/{len(primary_images)}] {product_title}")
        print(f"Target: {target_filename}")

        # Find matching product in farbe CSV
        product_row = df[df['product_id'] == f"gid://shopify/Product/{product_id}"]

        if product_row.empty:
            print(f"  ERROR: Product {product_id} not found in farbe CSV")
            results.append({
                'product_id': product_id,
                'title': product_title,
                'status': 'not_found_in_csv',
                'filename': target_filename,
            })
            continue

        product = product_row.iloc[0]
        sku = product['sku']
        barcode = product['barcode']

        print(f"  SKU: {sku}, Barcode: {barcode}")

        # Scrape image URL
        print(f"  Scraping pentacolor.eu...")
        image_url = scrape_pentart_image(str(sku))

        if not image_url:
            # Try with barcode if SKU failed
            print(f"  Trying with barcode...")
            image_url = scrape_pentart_image(str(barcode))

        if not image_url:
            print(f"  ERROR: No image found")
            results.append({
                'product_id': product_id,
                'title': product_title,
                'sku': sku,
                'barcode': barcode,
                'status': 'not_found',
                'filename': target_filename,
            })
            continue

        # Determine file extension from URL
        ext = Path(image_url).suffix
        if ext in ('.webp', '.png', '.jpg', '.jpeg'):
            pass  # Use as-is
        else:
            ext = '.jpg'  # Default

        # Set target path with correct extension
        target_path = output_dir / target_filename
        if target_path.suffix != ext:
            target_path = target_path.with_suffix(ext)

        # Download image
        print(f"  Downloading...")
        success = download_image(image_url, str(target_path))

        results.append({
            'product_id': product_id,
            'title': product_title,
            'sku': sku,
            'barcode': barcode,
            'status': 'success' if success else 'download_failed',
            'image_url': image_url,
            'filename': target_path.name,
            'filepath': str(target_path) if success else None,
        })

    # Save results
    results_df = pd.DataFrame(results)
    results_path = output_dir / 'download_results.csv'
    results_df.to_csv(results_path, index=False)

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total products: {len(results)}")
    print(f"Successful: {len([r for r in results if r['status'] == 'success'])}")
    print(f"Not found: {len([r for r in results if r['status'] == 'not_found'])}")
    print(f"Failed: {len([r for r in results if r['status'] == 'download_failed'])}")
    print(f"\nResults saved to: {results_path}")
    print(f"Images saved to: {output_dir}")


if __name__ == "__main__":
    main()
