"""
Complete Pentart Product Setup using REST API

Creates products with ALL fields:
- SKU, barcode, weight
- Country, HS code
- Inventory levels
- Images
- German translation
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import ShopifyClient
from utils.pentart_db import PentartDatabase
from deep_translator import GoogleTranslator

# Load environment
load_dotenv()

SHOP_DOMAIN = os.getenv('SHOP_DOMAIN')
API_VERSION = os.getenv('API_VERSION', '2024-01')

# Products to update: (EAN, Product ID, Variant ID, Inventory)
PRODUCTS = [
    ("5997412709667", "10562168389970", "52593398808914", 6),
    ("5997412742664", "10562168815954", "52593407426898", 5),
    ("5997412761139", "10562169176402", "52593413259602", 5),
    ("5996546033389", "10562169602386", "52593417027922", 1),
]

def scrape_pentart_image(article_number):
    """Scrape product image from pentacolor.eu"""
    search_url = f"https://www.pentacolor.eu/kereses?description=0&keyword={article_number}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        print(f"    Scraping for article {article_number}...")
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
        print(f"    Error: {e}")
        return None

class ShopifyRestAPI:
    """Shopify REST API Client"""

    def __init__(self):
        self.graphql_client = ShopifyClient()
        self.graphql_client.authenticate()
        self.access_token = self.graphql_client.access_token
        self.base_url = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}"

    def get_headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

    def update_variant(self, variant_id, sku=None, barcode=None, weight=None, weight_unit="g"):
        """Update variant via REST API"""
        url = f"{self.base_url}/variants/{variant_id}.json"

        data = {"variant": {}}
        if sku:
            data["variant"]["sku"] = sku
        if barcode:
            data["variant"]["barcode"] = barcode
        if weight is not None:
            data["variant"]["weight"] = float(weight)
            data["variant"]["weight_unit"] = weight_unit

        try:
            response = requests.put(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"    REST API Error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"    Response: {e.response.text}")
            return None

    def update_inventory_item(self, inventory_item_id, country_code=None, hs_code=None):
        """Update inventory item via REST API"""
        # Extract numeric ID from GID
        inv_id = inventory_item_id.split('/')[-1]
        url = f"{self.base_url}/inventory_items/{inv_id}.json"

        data = {"inventory_item": {}}
        if country_code:
            data["inventory_item"]["country_code_of_origin"] = country_code
        if hs_code:
            data["inventory_item"]["harmonized_system_code"] = hs_code

        try:
            response = requests.put(url, json=data, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"    REST API Error: {e}")
            return None

def main():
    """Process all products"""

    rest_api = ShopifyRestAPI()
    graphql = rest_api.graphql_client
    pentart_db = PentartDatabase()

    location_id = graphql.get_default_location()
    print(f"Location: {location_id}")
    print("=" * 70)

    for ean, product_id_num, variant_id_num, inventory_qty in PRODUCTS:
        product_id = f"gid://shopify/Product/{product_id_num}"
        variant_gid = f"gid://shopify/ProductVariant/{variant_id_num}"

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

            # Get inventory item ID via GraphQL
            query = f'''
            query {{
              productVariant(id: "{variant_gid}") {{
                inventoryItem {{ id }}
              }}
            }}
            '''
            result = graphql.execute_graphql(query)
            inventory_item_id = result['data']['productVariant']['inventoryItem']['id']
            inventory_item_num = inventory_item_id.split('/')[-1]

            print(f"\n[1/6] Updating variant (SKU, barcode, weight)...")
            # Use REST API to update variant
            variant_result = rest_api.update_variant(
                variant_id_num,
                sku=ean,
                barcode=ean,
                weight=weight,
                weight_unit="g"
            )

            if variant_result:
                updated = variant_result.get('variant', {})
                print(f"  [OK] SKU: {updated.get('sku')}")
                print(f"  [OK] Barcode: {updated.get('barcode')}")
                print(f"  [OK] Weight: {updated.get('weight')}g")
            else:
                print(f"  [ERROR] Variant update failed")

            print(f"\n[2/6] Updating inventory item (country, HS code)...")
            # Use REST API to update inventory item
            inv_result = rest_api.update_inventory_item(
                inventory_item_id,
                country_code="HU",
                hs_code="3214.90"
            )

            if inv_result:
                print(f"  [OK] Country: HU, HS Code: 3214.90")
            else:
                print(f"  [WARN] Inventory item update had issues")

            print(f"\n[3/6] Setting inventory to {inventory_qty} units...")
            if graphql.set_inventory_level(inventory_item_id, location_id, inventory_qty):
                print(f"  [OK] Inventory: {inventory_qty} units")
            else:
                print(f"  [ERROR] Inventory set failed")

            print(f"\n[4/6] Scraping image...")
            image_url = scrape_pentart_image(article_num)

            if image_url:
                print(f"[5/6] Uploading image...")
                from src.core.image_scraper import clean_product_name
                alt_text = clean_product_name(hungarian_title)
                media_result = graphql.update_product_media(product_id, image_url, alt_text)
                if media_result:
                    print(f"  [OK] Image uploaded")
            else:
                print(f"  [SKIP] No image found")

            print(f"\n[6/6] Translating to German...")
            try:
                translator = GoogleTranslator(source='hu', target='de')
                german_title = translator.translate(hungarian_title)
                print(f"  DE: {german_title}")

                # Update title via GraphQL
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
                title_result = graphql.execute_graphql(title_mutation)
                if title_result and title_result.get('data'):
                    print(f"  [OK] Title updated")
            except Exception as e:
                print(f"  [WARN] Translation error: {e}")

            print(f"\n[SUCCESS] {ean} - Complete!\n")

        except Exception as e:
            print(f"[ERROR] {ean}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print("\n[DONE] All products processed!")
    print("\nVerifying with quality agent:")
    print("  python orchestrator/product_quality_agent.py --sku 5997412709667")

if __name__ == "__main__":
    main()
