"""
Recreate Pentart Products from Scratch

1. Delete incomplete products
2. Create fresh with all fields (SKU, barcode, weight, country, HS code)
3. Upload images
4. Translate to German
5. Set inventory
6. Run quality check
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import ShopifyClient, clean_product_name
from utils.pentart_db import PentartDatabase
from deep_translator import GoogleTranslator

load_dotenv()

# Products to recreate: (EAN, Old Product ID, Inventory)
PRODUCTS_TO_DELETE = [
    ("5997412709667", "10562168389970", 6),
    ("5997412742664", "10562168815954", 5),
    ("5997412761139", "10562169176402", 5),
    ("5996546033389", "10562169602386", 1),
]

def scrape_pentart_image(article_number):
    """Scrape product image from pentacolor.eu"""
    search_url = f"https://www.pentacolor.eu/kereses?description=0&keyword={article_number}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        links = soup.find_all('a', href=True)
        product_links = [l['href'] for l in links if ('pentacolor.eu' in l['href'] or l['href'].startswith('/')) and 'kereses' not in l['href']]

        if product_links:
            product_url = product_links[0]
            if not product_url.startswith('http'):
                product_url = f"https://www.pentacolor.eu{product_url}"

            r_prod = requests.get(product_url, headers=headers, timeout=10)
            soup_prod = BeautifulSoup(r_prod.text, 'html.parser')

            imgs = soup_prod.find_all('img', src=True)
            for img in imgs:
                src = img['src']
                if article_number in src or 'w900h900' in src or 'product' in src.lower():
                    if 'w261h261' in src:
                        src = src.replace('w261h261', 'w900h900')
                    if not src.startswith('http'):
                        src = f"https://www.pentacolor.eu{src}" if not src.startswith('//') else f"https:{src}"
                    return src
        return None
    except Exception as e:
        return None

def main():
    """Delete and recreate products"""

    shopify = ShopifyClient()
    shopify.authenticate()
    pentart_db = PentartDatabase()

    location_id = shopify.get_default_location()
    print(f"Location: {location_id}")
    print("=" * 70)

    # Step 1: Delete old incomplete products
    print("\n[STEP 1] Deleting old incomplete products...")
    for ean, product_id_num, inv_qty in PRODUCTS_TO_DELETE:
        product_gid = f"gid://shopify/Product/{product_id_num}"
        print(f"  Deleting product {product_id_num}...")

        delete_mutation = f'''
        mutation {{
          productDelete(input: {{id: "{product_gid}"}}) {{
            deletedProductId
            userErrors {{ field message }}
          }}
        }}
        '''

        result = shopify.execute_graphql(delete_mutation)
        if result and result.get('data', {}).get('productDelete', {}).get('deletedProductId'):
            print(f"  [OK] Deleted {product_id_num}")
        else:
            print(f"  [WARN] Could not delete {product_id_num}")

    print("\n" + "=" * 70)

    # Step 2: Create fresh products with all fields
    print("\n[STEP 2] Creating products with complete data...")

    vendor = "Pentart"
    created_products = []

    for ean, _, inventory_qty in PRODUCTS_TO_DELETE:
        print(f"\n[PRODUCT] EAN: {ean}")
        print("-" * 70)

        try:
            # Get database info
            db_product = pentart_db.get_by_ean(ean)
            if not db_product:
                print("[ERROR] Not in database")
                continue

            article_num = db_product.get('article_number')
            hungarian_title = db_product.get('description')
            weight = db_product.get('product_weight')

            print(f"  Article: {article_num}")
            print(f"  HU Title: {hungarian_title}")
            print(f"  Weight: {weight}g")

            # Translate to German
            print(f"\n  [1/5] Translating to German...")
            try:
                translator = GoogleTranslator(source='hu', target='de')
                german_title = translator.translate(hungarian_title)
                print(f"  DE Title: {german_title}")
            except:
                german_title = hungarian_title
                print(f"  [WARN] Translation failed, using Hungarian")

            # Create product with ALL fields
            print(f"  [2/5] Creating product...")
            product_id, variant_id, inventory_item_id = shopify.create_product(
                title=german_title,
                vendor=vendor,
                sku=ean,  # Use EAN as SKU
                barcode=ean,
                price=None,
                weight=weight,
                country="HU",
                hs_code="3214.90",
                category=None
            )

            if not product_id:
                print(f"  [ERROR] Product creation failed")
                continue

            print(f"  [OK] Created: {product_id}")
            created_products.append((ean, product_id, inventory_item_id, inventory_qty, article_num, german_title))

            # Set inventory
            print(f"  [3/5] Setting inventory to {inventory_qty}...")
            if shopify.set_inventory_level(inventory_item_id, location_id, inventory_qty):
                print(f"  [OK] Inventory: {inventory_qty} units")
            else:
                print(f"  [ERROR] Inventory failed")

            # Scrape and upload image
            print(f"  [4/5] Scraping image...")
            image_url = scrape_pentart_image(article_num)

            if image_url:
                print(f"  [5/5] Uploading image...")
                alt_text = clean_product_name(german_title)
                media_result = shopify.update_product_media(product_id, image_url, alt_text)
                if media_result:
                    print(f"  [OK] Image uploaded")
            else:
                print(f"  [SKIP] No image found")

            # Activate product
            if shopify.activate_product(product_id):
                print(f"  [OK] Product activated")

            print(f"\n[SUCCESS] {ean} - Complete!")

        except Exception as e:
            print(f"[ERROR] {ean}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"\n[DONE] Created {len(created_products)} products!\n")

    # Step 3: Run quality check
    if created_products:
        print("\n[STEP 3] Running quality checks...")
        for ean, product_id, _, _, _, title in created_products:
            print(f"\nQuality check: {ean} - {title[:50]}...")
            os.system(f'python orchestrator/product_quality_agent.py --sku {ean}')

if __name__ == "__main__":
    main()
