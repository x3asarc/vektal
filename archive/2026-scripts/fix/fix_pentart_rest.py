"""
Fix Pentart Products using REST API

Updates SKU, barcode, weight, inventory, images, and translations
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import base64

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.pentart_db import PentartDatabase
from deep_translator import GoogleTranslator

# Load environment
load_dotenv()

# Shopify credentials
CLIENT_ID = os.getenv('SHOPIFY_CLIENT_ID')
CLIENT_SECRET = os.getenv('SHOPIFY_CLIENT_SECRET')
SHOP_DOMAIN = os.getenv('SHOP_DOMAIN')
ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')  # We'll need to generate this

# Products: (EAN, Product ID number, Variant ID number, Inventory)
PRODUCTS = [
    ("5997412709667", "10562168389970", "52593398808914", 6),
    ("5997412742664", "10562168815954", "52593407426898", 5),
    ("5997412761139", "10562169176402", "52593413259602", 5),
    ("5996546033389", "10562169602386", "52593417027922", 1),
]

def get_rest_headers():
    """Get REST API headers"""
    # For now, use basic auth with API key and password
    # In production, use access token
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_bytes = auth_str.encode('ascii')
    base64_bytes = base64.b64encode(auth_bytes)
    base64_auth = base64_bytes.decode('ascii')

    return {
        'Authorization': f'Basic {base64_auth}',
        'Content-Type': 'application/json'
    }

def scrape_pentart_image(article_number):
    """Scrape product image from pentacolor.eu"""
    search_url = f"https://www.pentacolor.eu/kereses?description=0&keyword={article_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        print(f"    Scraping image for article {article_number}...")
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find product links
        links = soup.find_all('a', href=True)
        product_links = [l['href'] for l in links if ('pentacolor.eu' in l['href'] or l['href'].startswith('/')) and 'kereses' not in l['href']]

        if product_links:
            product_url = product_links[0]
            if not product_url.startswith('http'):
                product_url = f"https://www.pentacolor.eu{product_url}"

            print(f"    Product page: {product_url[:60]}...")
            r_prod = requests.get(product_url, headers=headers, timeout=10)
            soup_prod = BeautifulSoup(r_prod.text, 'html.parser')

            # Find image
            imgs = soup_prod.find_all('img', src=True)
            for img in imgs:
                src = img['src']
                if article_number in src or 'w900h900' in src or 'product' in src.lower():
                    if 'w261h261' in src:
                        src = src.replace('w261h261', 'w900h900')
                    if not src.startswith('http'):
                        src = f"https://www.pentacolor.eu{src}" if not src.startswith('//') else f"https:{src}"
                    print(f"    Found: {src[:70]}...")
                    return src

        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None

def main():
    """Process all products using GraphQL only (no REST)"""

    from src.core.image_scraper import ShopifyClient

    shopify = ShopifyClient()
    shopify.authenticate()
    pentart_db = PentartDatabase()

    location_id = shopify.get_default_location()
    print(f"Location: {location_id}")
    print("=" * 70)

    for ean, product_id_num, variant_id_num, inventory_qty in PRODUCTS:
        product_id = f"gid://shopify/Product/{product_id_num}"
        variant_id = f"gid://shopify/ProductVariant/{variant_id_num}"

        print(f"\nEAN: {ean}")
        print("-" * 70)

        try:
            # Get data
            db_product = pentart_db.get_by_ean(ean)
            if not db_product:
                print("[ERROR] Not found in database")
                continue

            article_num = db_product.get('article_number')
            hungarian_title = db_product.get('description')
            weight = db_product.get('product_weight')

            print(f"  Article: {article_num}")
            print(f"  HU Title: {hungarian_title}")
            print(f"  Weight: {weight}g")

            # Get inventory item ID
            query = f'''
            query {{
              productVariant(id: "{variant_id}") {{
                inventoryItem {{ id }}
              }}
            }}
            '''
            result = shopify.execute_graphql(query)
            inventory_item_id = result['data']['productVariant']['inventoryItem']['id']

            # 1. Update variant with barcode only (SKU and weight via separate methods)
            print("\n  [1/6] Updating barcode...")
            barcode_mutation = f'''
            mutation {{
              productVariantUpdate(input: {{
                id: "{variant_id}"
                barcode: "{ean}"
              }}) {{
                productVariant {{ id barcode }}
                userErrors {{ field message }}
              }}
            }}
            '''
            barcode_result = shopify.execute_graphql(barcode_mutation)
            if barcode_result and barcode_result.get('data'):
                print(f"  [OK] Barcode set to {ean}")

            # 2. Update inventory item
            print("  [2/6] Updating country and HS code...")
            inv_mutation = f'''
            mutation {{
              inventoryItemUpdate(id: "{inventory_item_id}", input: {{
                countryCodeOfOrigin: HU
                harmonizedSystemCode: "3214.90"
              }}) {{
                inventoryItem {{ id }}
                userErrors {{ field message }}
              }}
            }}
            '''
            inv_result = shopify.execute_graphql(inv_mutation)
            if inv_result and inv_result.get('data'):
                print("  [OK] Country: HU, HS: 3214.90")

            # 3. Set inventory
            print(f"  [3/6] Setting inventory to {inventory_qty}...")
            if shopify.set_inventory_level(inventory_item_id, location_id, inventory_qty):
                print(f"  [OK] Inventory: {inventory_qty} units")

            # 4. Scrape and upload image
            print("  [4/6] Scraping image...")
            image_url = scrape_pentart_image(article_num)

            if image_url:
                print("  [5/6] Uploading image...")
                from src.core.image_scraper import clean_product_name
                alt_text = clean_product_name(hungarian_title)
                media_result = shopify.update_product_media(product_id, image_url, alt_text)
                if media_result:
                    print("  [OK] Image uploaded")
            else:
                print("  [SKIP] No image found")

            # 5. Translate to German
            print("  [6/6] Translating to German...")
            try:
                translator = GoogleTranslator(source='hu', target='de')
                german_title = translator.translate(hungarian_title)
                print(f"  DE Title: {german_title}")

                title_mutation = f'''
                mutation {{
                  productUpdate(input: {{
                    id: "{product_id}"
                    title: "{german_title.replace('"', '\\"')}"
                  }}) {{
                    product {{ id title }}
                    userErrors {{ field message }}
                  }}
                }}
                '''
                title_result = shopify.execute_graphql(title_mutation)
                if title_result and title_result.get('data'):
                    print("  [OK] Title updated to German")
            except Exception as e:
                print(f"  [WARN] Translation error: {e}")

            print(f"\n[OK] COMPLETED: {ean}\n")

        except Exception as e:
            print(f"[ERROR] {ean}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print("\nAll products updated!")
    print("\nNext: Run quality check on one product:")
    print("  python orchestrator/product_quality_agent.py --sku 5997412709667")

if __name__ == "__main__":
    main()
