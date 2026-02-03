"""
Preview Galaxy Flakes image updates (DRY RUN)
Shows current vs. proposed changes without applying
"""
import os
import sys
import pandas as pd
from pathlib import Path
from PIL import Image
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver


def preview_image(image_path):
    """Show image dimensions and first few bytes"""
    try:
        img = Image.open(image_path)
        return f"{img.width}x{img.height} {img.format}"
    except:
        return "Cannot read image"


def get_current_product_info(resolver, product_id):
    """Get current product image info from Shopify"""
    query = """
    query getProduct($id: ID!) {
      product(id: $id) {
        id
        title
        handle
        featuredImage {
          id
          url
          altText
        }
        images(first: 5) {
          edges {
            node {
              id
              url
              altText
            }
          }
        }
      }
    }
    """

    try:
        result = resolver.client.execute_graphql(query, {"id": f"gid://shopify/Product/{product_id}"})
        return result.get('data', {}).get('product')
    except Exception as e:
        return None


def main():
    """Preview all changes"""

    # Paths
    script_dir = Path(__file__).parent
    images_dir = script_dir / "data" / "supplier_images" / "galaxy_flakes"
    results_csv = images_dir / "download_results.csv"
    seo_plan_path = script_dir / "data" / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
    preview_dir = script_dir / "data" / "supplier_images" / "galaxy_flakes" / "preview"

    # Create preview directory
    preview_dir.mkdir(parents=True, exist_ok=True)

    # Read data
    print("Loading data...")
    results_df = pd.read_csv(results_csv)
    seo_df = pd.read_csv(seo_plan_path)
    primary_df = seo_df[seo_df['is_primary'] == True].copy()

    # Initialize Shopify
    print("Connecting to Shopify...")
    resolver = ShopifyResolver()

    print("\n" + "="*80)
    print("GALAXY FLAKES IMAGE UPDATE PREVIEW (DRY RUN)")
    print("="*80)

    changes = []

    for _, result_row in results_df.iterrows():
        product_id = result_row['product_id']
        title = result_row['title']
        image_path = Path(result_row['filepath'])

        # Get SEO plan info
        seo_row = primary_df[primary_df['product_id'].astype(str) == str(product_id)]
        if seo_row.empty:
            continue

        proposed_alt = seo_row.iloc[0]['proposed_alt']
        proposed_filename = seo_row.iloc[0]['proposed_filename']

        print(f"\n{'='*80}")
        print(f"Product: {title}")
        print(f"ID: {product_id}")
        print(f"-"*80)

        # Get current Shopify data
        print("Fetching current Shopify data...")
        current = get_current_product_info(resolver, product_id)

        if current:
            current_image = current.get('featuredImage')
            if current_image:
                print(f"\nCURRENT PRIMARY IMAGE:")
                print(f"  URL: {current_image.get('url', 'N/A')[:80]}...")
                print(f"  Alt Text: {current_image.get('altText', '(empty)')}")
                # Extract filename from URL
                current_filename = Path(current_image.get('url', '')).name.split('?')[0]
                print(f"  Filename: {current_filename}")
            else:
                print(f"\nCURRENT PRIMARY IMAGE: None")
        else:
            print(f"  ERROR: Could not fetch current data")

        # Show new image info
        print(f"\nPROPOSED NEW PRIMARY IMAGE:")
        if image_path.exists():
            img_info = preview_image(image_path)
            file_size = image_path.stat().st_size / 1024
            print(f"  File: {image_path.name}")
            print(f"  Dimensions: {img_info}")
            print(f"  Size: {file_size:.1f} KB")
            print(f"  Path: {image_path}")

            # Copy to preview directory for easy viewing
            preview_path = preview_dir / image_path.name
            shutil.copy(image_path, preview_path)
        else:
            print(f"  ERROR: Image file not found")

        print(f"\nPROPOSED ALT TEXT:")
        print(f"  {proposed_alt}")

        print(f"\nPROPOSED FILENAME:")
        print(f"  {proposed_filename}")

        print(f"\nACTIONS TO BE TAKEN:")
        print(f"  1. Upload new image from: {image_path.name}")
        print(f"  2. Set as primary/featured image")
        print(f"  3. Update alt text to: {proposed_alt}")
        print(f"  4. Image will be renamed to: {proposed_filename}")

        changes.append({
            'product_id': product_id,
            'title': title,
            'current_alt': current_image.get('altText', '') if current and current_image else '',
            'proposed_alt': proposed_alt,
            'current_filename': current_filename if current and current_image else '',
            'proposed_filename': proposed_filename,
            'new_image_path': str(image_path),
            'status': 'ready' if image_path.exists() else 'missing_image'
        })

    # Save preview summary
    preview_df = pd.DataFrame(changes)
    preview_csv = preview_dir / "preview_summary.csv"
    preview_df.to_csv(preview_csv, index=False)

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total products: {len(changes)}")
    print(f"Ready to update: {len([c for c in changes if c['status'] == 'ready'])}")
    print(f"Missing images: {len([c for c in changes if c['status'] == 'missing_image'])}")
    print(f"\nPreview images copied to: {preview_dir}")
    print(f"Preview summary saved to: {preview_csv}")
    print(f"\nThis was a DRY RUN - no changes were made to Shopify")
    print(f"\nTo apply these changes, run:")
    print(f"  python apply_galaxy_flakes_updates.py")


if __name__ == "__main__":
    main()
