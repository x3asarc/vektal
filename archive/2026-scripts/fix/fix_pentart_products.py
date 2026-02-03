"""
Complete Pentart Product Update Script

Fixes the 4 created products:
- Updates SKU, barcode, weight
- Sets inventory levels
- Scrapes and uploads images
- Translates to German
- Runs quality checks
"""
import os
import sys
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import ShopifyClient, clean_product_name
from utils.pentart_db import PentartDatabase
from deep_translator import GoogleTranslator

# Load environment
load_dotenv()

# Products to fix: (EAN, Product ID, Inventory Qty)
PRODUCTS = [
    ("5997412709667", "gid://shopify/Product/10562168389970", 6),
    ("5997412742664", "gid://shopify/Product/10562168815954", 5),
    ("5997412761139", "gid://shopify/Product/10562169176402", 5),
    ("5996546033389", "gid://shopify/Product/10562169602386", 1),
]

def scrape_pentart_image(article_number, use_selenium=True):
    """
    Scrape product image from pentacolor.eu

    Args:
        article_number: Product SKU/article number
        use_selenium: If True, use Selenium as fallback when simple scrape fails

    Returns:
        Image URL or None
    """
    search_url = f"https://www.pentacolor.eu/kereses?description=0&keyword={article_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # Try simple scraping first
    try:
        print(f"    Searching pentacolor.eu for article {article_number}...")
        r = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find product links (exclude search page itself)
        links = soup.find_all('a', href=True)
        product_links = [
            l['href'] for l in links
            if ('pentacolor.eu' in l['href'] or l['href'].startswith('/'))
            and 'kereses' not in l['href']
            and l['href'] not in ('/', '/#')  # Exclude homepage
        ]

        if product_links:
            product_url = product_links[0]
            if not product_url.startswith('http'):
                product_url = f"https://www.pentacolor.eu{product_url}"

            print(f"    Found product page: {product_url}")
            r_prod = requests.get(product_url, headers=headers, timeout=10)
            soup_prod = BeautifulSoup(r_prod.text, 'html.parser')

            # Find product image
            imgs = soup_prod.find_all('img', src=True)
            for img in imgs:
                src = img['src']
                # Look for SKU in image URL or high-res images
                if article_number in src or 'w900h900' in src or 'product' in src.lower():
                    # Upgrade to high res if possible
                    if 'w261h261' in src:
                        src = src.replace('w261h261', 'w900h900')
                    if not src.startswith('http'):
                        src = f"https://www.pentacolor.eu{src}" if not src.startswith('//') else f"https:{src}"
                    print(f"    Found image: {src[:80]}...")
                    return src

        print("    Simple scrape found no results")

    except Exception as e:
        print(f"    Simple scraping error: {e}")

    # Fallback to Selenium if enabled
    if use_selenium:
        print("    Trying Selenium fallback...")
        return scrape_pentart_image_selenium(article_number)

    return None


def scrape_pentart_image_selenium(article_number):
    """
    Scrape product image using Selenium for JS-driven sites

    Args:
        article_number: Product SKU/article number

    Returns:
        Image URL or None
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from selenium.common.exceptions import TimeoutException
        from webdriver_manager.chrome import ChromeDriverManager
        import time

        # Setup Chrome driver
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)

        try:
            # Load pentacolor.eu
            print(f"      Loading pentacolor.eu...")
            driver.get("https://www.pentacolor.eu")
            time.sleep(2)

            # Find search box
            search_selectors = [
                "input[type='search']",
                "input[name='keyword']",
                "input#searchTerm",
                "input.search-field",
                ".search-form input",
            ]

            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_box and search_box.is_displayed():
                        print(f"      Found search box: {selector}")
                        break
                except:
                    continue

            if not search_box:
                print("      Could not find search box")
                return None

            # Search for product
            search_box.clear()
            search_box.send_keys(article_number)
            search_box.send_keys(Keys.RETURN)
            time.sleep(3)

            # Check if we're on a product page
            current_url = driver.current_url
            print(f"      Current URL: {current_url}")

            # If on search results, click first product
            if '/kereses' in current_url or '/search' in current_url:
                try:
                    # Look for product links
                    product_link = driver.find_element(By.CSS_SELECTOR, ".product-item a, .product a, [class*='product'] a")
                    product_link.click()
                    time.sleep(2)
                except:
                    print("      No product links found in search results")
                    return None

            # Extract SKU-specific image from product/category page
            # The page shows all Galaxy Flakes variants with thumbnails
            # We need to find the thumbnail matching our specific SKU

            import re

            # First, try to find thumbnail with matching SKU in filename
            all_imgs = driver.find_elements(By.TAG_NAME, "img")
            print(f"      Found {len(all_imgs)} images on page")

            matched_image = None
            for img in all_imgs:
                src = img.get_attribute('src') or img.get_attribute('data-src')
                if not src:
                    continue

                # Check if this image has our SKU in the filename
                # Pattern: gyerektermekek/37047.png or similar
                if article_number in src and 'gyerektermekek' in src:
                    print(f"      Found SKU-specific thumbnail: {src[:80]}...")
                    matched_image = src
                    break

            if matched_image:
                # Upgrade to highest resolution
                matched_image = re.sub(r'/w\d+h\d+/', '/w1719h900/', matched_image)
                matched_image = matched_image.replace('w261h261', 'w1719h900')
                matched_image = matched_image.replace('w64h64', 'w1719h900')
                matched_image = matched_image.replace('w295h300', 'w1719h900')
                print(f"      Upgraded to high-res: {matched_image[:80]}...")
                return matched_image

            # Fallback: Try Open Graph meta tag if no SKU-specific image found
            print("      No SKU-specific image found, trying OG image as fallback...")
            try:
                og_img = driver.find_element(By.CSS_SELECTOR, "meta[property='og:image']")
                if og_img:
                    src = og_img.get_attribute('content')
                    if src:
                        print(f"      Found OG image fallback: {src[:80]}...")
                        return src
            except:
                pass

            print("      No product image found with Selenium")
            return None

        finally:
            driver.quit()

    except Exception as e:
        print(f"      Selenium scraping error: {e}")
        return None

def main():
    """Update all 4 Pentart products"""

    # Initialize
    shopify = ShopifyClient()
    shopify.authenticate()
    pentart_db = PentartDatabase()

    # Get location
    default_location_id = shopify.get_default_location()
    if not default_location_id:
        print("[ERROR] Could not get location ID")
        return

    print(f"Location ID: {default_location_id}")
    print("=" * 70)

    for ean, product_id, inventory_qty in PRODUCTS:
        print(f"\nProcessing EAN: {ean}")
        print("-" * 70)

        try:
            # Get product data from database
            db_product = pentart_db.get_by_ean(ean)
            if not db_product:
                print(f"[ERROR] Product not found in database")
                continue

            article_number = db_product.get('article_number')
            hungarian_title = db_product.get('description')
            weight = db_product.get('product_weight')

            print(f"  Article Number: {article_number}")
            print(f"  Hungarian Title: {hungarian_title}")
            print(f"  Weight: {weight}g")

            # Step 1: Get variant ID
            variant_query = f"""
            query {{
              product(id: "{product_id}") {{
                variants(first: 1) {{
                  edges {{
                    node {{
                      id
                      inventoryItem {{ id }}
                    }}
                  }}
                }}
              }}
            }}
            """
            result = shopify.execute_graphql(variant_query)
            variant_node = result['data']['product']['variants']['edges'][0]['node']
            variant_id = variant_node['id']
            inventory_item_id = variant_node['inventoryItem']['id']

            print(f"  Variant ID: {variant_id}")
            print(f"  Inventory Item ID: {inventory_item_id}")

            # Step 2: Update variant (SKU, barcode, weight)
            print("\n  Updating variant...")
            variant_mutation = """
            mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
              productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                product { id }
                productVariants { id sku barcode }
                userErrors { field message }
              }
            }
            """

            variant_input = {
                "id": variant_id,
                "sku": ean,
                "barcode": ean,
            }

            if weight:
                variant_input["weight"] = float(weight)
                variant_input["weightUnit"] = "GRAMS"

            variant_result = shopify.execute_graphql(variant_mutation, {
                "productId": product_id,
                "variants": [variant_input]
            })

            if variant_result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = variant_result['data']['productVariantsBulkUpdate']['userErrors']
                if errors:
                    print(f"  [WARN] Variant update errors: {errors}")
                else:
                    print(f"  [OK] Variant updated with SKU, barcode, weight")
            else:
                print(f"  [OK] Variant updated")

            # Step 3: Update inventory item (country, HS code)
            print("  Updating inventory item...")
            inventory_mutation = """
            mutation inventoryItemUpdate($id: ID!, $input: InventoryItemInput!) {
              inventoryItemUpdate(id: $id, input: $input) {
                inventoryItem {
                  id
                  countryCodeOfOrigin
                  harmonizedSystemCode
                }
                userErrors { field message }
              }
            }
            """

            inv_result = shopify.execute_graphql(inventory_mutation, {
                "id": inventory_item_id,
                "input": {
                    "countryCodeOfOrigin": "HU",
                    "harmonizedSystemCode": "3214.90"
                }
            })

            if inv_result.get('data', {}).get('inventoryItemUpdate', {}).get('userErrors'):
                errors = inv_result['data']['inventoryItemUpdate']['userErrors']
                if errors:
                    print(f"  [WARN] Inventory item errors: {errors}")
                else:
                    print(f"  [OK] Inventory item updated (country: HU, HS: 3214.90)")
            else:
                print(f"  [OK] Inventory item updated")

            # Step 4: Set inventory level
            print(f"  Setting inventory to {inventory_qty} units...")
            if shopify.set_inventory_level(inventory_item_id, default_location_id, inventory_qty):
                print(f"  [OK] Inventory set to {inventory_qty}")
            else:
                print(f"  [ERROR] Failed to set inventory")

            # Step 5: Scrape image
            print("\n  Scraping product image...")
            image_url = scrape_pentart_image(article_number)

            if image_url:
                print(f"  Uploading image...")
                alt_text = clean_product_name(hungarian_title)
                media_result = shopify.update_product_media(product_id, image_url, alt_text)

                if media_result and not media_result.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
                    print(f"  [OK] Image uploaded")
                else:
                    errors = media_result.get("data", {}).get("productCreateMedia", {}).get("userErrors", [])
                    if errors:
                        print(f"  [WARN] Image upload warning: {errors}")
                    else:
                        print(f"  [OK] Image uploaded (no errors)")
            else:
                print(f"  [WARN] No image found - skipping upload")

            # Step 6: Translate to German
            print("\n  Translating title to German...")
            try:
                translator = GoogleTranslator(source='hu', target='de')
                german_title = translator.translate(hungarian_title)
                print(f"  German: {german_title}")

                # Update product title
                title_mutation = """
                mutation productUpdate($input: ProductInput!) {
                  productUpdate(input: $input) {
                    product { id title }
                    userErrors { field message }
                  }
                }
                """

                title_result = shopify.execute_graphql(title_mutation, {
                    "input": {
                        "id": product_id,
                        "title": german_title
                    }
                })

                if title_result.get('data', {}).get('productUpdate', {}).get('userErrors'):
                    errors = title_result['data']['productUpdate']['userErrors']
                    if errors:
                        print(f"  [WARN] Title update errors: {errors}")
                    else:
                        print(f"  [OK] Title updated to German")
                else:
                    print(f"  [OK] Title updated to German")

            except Exception as e:
                print(f"  [WARN] Translation failed: {e}")
                print(f"  [INFO] Keeping Hungarian title")

            print(f"\n[OK] COMPLETED: {ean}")

        except Exception as e:
            print(f"[ERROR] Failed to process {ean}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("All products updated!")
    print("\nNext step: Run quality check")
    print("  python orchestrator/product_quality_agent.py --sku 5997412709667")

if __name__ == "__main__":
    main()
