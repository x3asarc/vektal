"""
Pentacolor Image Scraper for Galaxy Flakes
Scrapes product images from pentacolor.eu (Pentart supplier site)
Uses Selenium to handle JS-driven RapidSearch
"""

import os
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class PentacolorScraper:
    """Scrape product images from Pentacolor (pentacolor.eu)"""

    BASE_URLS = [
        "https://pentacolor.shoprenter.hu",
        "https://www.pentacolor.eu",
    ]

    def __init__(self, headless=True, timeout=30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def setup_driver(self):
        """Initialize Chrome WebDriver with appropriate options"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(self.timeout)

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def search_product(self, sku=None, barcode=None, product_name=None):
        """
        Search for a product by SKU, barcode, or name

        Args:
            sku: Product SKU/article number
            barcode: Product EAN/barcode
            product_name: Product name

        Returns:
            dict with image_url, product_url, title, or None if not found
        """
        if not self.driver:
            self.setup_driver()

        # Try different search terms
        search_terms = []
        if sku:
            search_terms.append(str(sku))
        if barcode:
            search_terms.append(str(barcode))
        if product_name:
            search_terms.append(str(product_name))

        for base_url in self.BASE_URLS:
            print(f"\n{'='*60}")
            print(f"Trying {base_url}...")

            for search_term in search_terms:
                print(f"\nSearching for: {search_term}")
                result = self._search_on_site(base_url, search_term)
                if result and result.get('image_url'):
                    print(f"✓ Found image: {result['image_url']}")
                    return result

        return None

    def _search_on_site(self, base_url, search_term):
        """Search on a specific site"""
        try:
            # Load homepage
            self.driver.get(base_url)
            time.sleep(2)

            print(f"Page title: {self.driver.title}")

            # Look for search box with multiple selectors
            search_selectors = [
                "input[type='search']",
                "input[name='s']",
                "input[name='search']",
                "input.search-field",
                "input#search",
                "input.search-input",
                "input[placeholder*='Search']",
                "input[placeholder*='Keresés']",
                "#searchTerm",
                ".search-form input",
            ]

            search_box = None
            for selector in search_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if search_box and search_box.is_displayed():
                        print(f"Found search box: {selector}")
                        break
                except:
                    continue

            if not search_box:
                print("Could not find search box")
                return None

            # Enter search term
            search_box.clear()
            search_box.send_keys(search_term)
            search_box.send_keys(Keys.RETURN)

            # Wait for results to load
            time.sleep(3)

            # Try to find product image in results
            result = self._extract_product_info()
            return result

        except TimeoutException:
            print(f"Timeout loading {base_url}")
            return None
        except Exception as e:
            print(f"Error searching {base_url}: {e}")
            return None

    def _extract_product_info(self):
        """Extract product image and info from current page"""
        try:
            current_url = self.driver.current_url
            print(f"Current URL: {current_url}")

            # Check if we landed on a product page directly
            if '/product/' in current_url or '/termek/' in current_url:
                return self._extract_from_product_page()

            # Otherwise, look for product links in search results
            product_selectors = [
                ".product-list .product-item a",
                ".products .product a",
                ".search-results .product a",
                "[class*='product-'] a[href*='product']",
                "[class*='product-'] a[href*='termek']",
            ]

            for selector in product_selectors:
                try:
                    product_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if product_links:
                        print(f"Found {len(product_links)} product links with selector: {selector}")
                        # Click first product
                        product_links[0].click()
                        time.sleep(2)
                        return self._extract_from_product_page()
                except:
                    continue

            return None

        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None

    def _extract_from_product_page(self):
        """Extract image from product detail page"""
        try:
            # Multiple strategies for finding product image
            image_selectors = [
                ".product-image img",
                ".product-photo img",
                "[class*='product-image'] img",
                "[class*='gallery'] img",
                ".main-image img",
                "#product-image img",
                "img[alt*='product']",
                "img[alt*='termék']",
            ]

            image_url = None
            for selector in image_selectors:
                try:
                    img_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for img in img_elements:
                        src = img.get_attribute('src') or img.get_attribute('data-src')
                        if src and not src.endswith('.gif') and 'placeholder' not in src.lower():
                            # Get highest quality version
                            src = src.replace('_thumb', '').replace('_small', '').replace('_medium', '')
                            image_url = src
                            print(f"Found image with selector {selector}: {image_url}")
                            break
                    if image_url:
                        break
                except:
                    continue

            if not image_url:
                print("No product image found on page")
                return None

            # Get product title
            title_selectors = [
                "h1.product-title",
                "h1[class*='product']",
                ".product-name",
                "h1",
            ]

            title = None
            for selector in title_selectors:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    title = title_elem.text.strip()
                    if title:
                        break
                except:
                    continue

            return {
                'image_url': image_url,
                'product_url': self.driver.current_url,
                'title': title or '',
            }

        except Exception as e:
            print(f"Error extracting from product page: {e}")
            return None


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

        print(f"✓ Downloaded to: {output_path}")
        return True

    except Exception as e:
        print(f"✗ Download failed: {e}")
        return False


def scrape_galaxy_flakes_images(csv_path, output_dir, dry_run=False):
    """
    Scrape primary images for all Galaxy Flakes products

    Args:
        csv_path: Path to farbe_metafields_galaxy_flakes.csv
        output_dir: Directory to save images
        dry_run: If True, only search without downloading
    """
    # Read product data
    df = pd.read_csv(csv_path)
    print(f"Found {len(df)} products to scrape")

    # Read SEO plan to get target filenames
    seo_plan_path = Path(csv_path).parent.parent / "svse" / "galaxy-flakes-15g-juno-rose" / "reports" / "seo_plan_per_product.csv"
    seo_df = pd.read_csv(seo_plan_path)

    # Filter for primary images only
    primary_images = seo_df[seo_df['is_primary'] == True].copy()
    print(f"Found {len(primary_images)} primary images to download")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize scraper
    scraper = PentacolorScraper(headless=True)

    results = []

    try:
        for _, primary_row in primary_images.iterrows():
            product_id = str(primary_row['product_id'])
            target_filename = primary_row['proposed_filename']

            print(f"\n{'='*70}")
            print(f"Processing: {primary_row['product_title']}")
            print(f"Product ID: {product_id}")
            print(f"Target filename: {target_filename}")

            # Find matching product in farbe CSV
            product_row = df[df['product_id'] == f"gid://shopify/Product/{product_id}"]

            if product_row.empty:
                print(f"✗ Product {product_id} not found in farbe CSV")
                results.append({
                    'product_id': product_id,
                    'title': primary_row['product_title'],
                    'status': 'not_found_in_csv',
                    'filename': target_filename,
                })
                continue

            product = product_row.iloc[0]
            sku = product['sku']
            barcode = product['barcode']
            title = product['title']

            print(f"SKU: {sku}, Barcode: {barcode}")

            # Search for product
            result = scraper.search_product(
                sku=sku,
                barcode=barcode,
                product_name=title,
            )

            if not result or not result.get('image_url'):
                print(f"✗ No image found for {title}")
                results.append({
                    'product_id': product_id,
                    'title': title,
                    'sku': sku,
                    'barcode': barcode,
                    'status': 'not_found',
                    'filename': target_filename,
                })
                continue

            # Determine file extension from URL
            ext = Path(result['image_url']).suffix or '.jpg'
            if not ext.startswith('.'):
                ext = '.jpg'

            # Ensure target filename has correct extension
            target_path = Path(output_dir) / target_filename
            if target_path.suffix != ext:
                # Replace extension
                target_path = target_path.with_suffix(ext)

            if dry_run:
                print(f"[DRY RUN] Would download: {result['image_url']}")
                print(f"[DRY RUN] To: {target_path}")
                results.append({
                    'product_id': product_id,
                    'title': title,
                    'sku': sku,
                    'barcode': barcode,
                    'status': 'found',
                    'image_url': result['image_url'],
                    'product_url': result.get('product_url'),
                    'filename': str(target_path.name),
                })
            else:
                # Download image
                success = download_image(result['image_url'], str(target_path))
                results.append({
                    'product_id': product_id,
                    'title': title,
                    'sku': sku,
                    'barcode': barcode,
                    'status': 'downloaded' if success else 'download_failed',
                    'image_url': result['image_url'],
                    'product_url': result.get('product_url'),
                    'filename': str(target_path.name),
                    'filepath': str(target_path) if success else None,
                })

            # Brief pause between requests
            time.sleep(2)

    finally:
        scraper.close()

    # Save results
    results_df = pd.DataFrame(results)
    results_path = Path(output_dir) / 'scrape_results.csv'
    results_df.to_csv(results_path, index=False)
    print(f"\n{'='*70}")
    print(f"Results saved to: {results_path}")

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total products: {len(results)}")
    print(f"Found: {len([r for r in results if r['status'] in ('found', 'downloaded')])}")
    print(f"Downloaded: {len([r for r in results if r['status'] == 'downloaded'])}")
    print(f"Not found: {len([r for r in results if r['status'] == 'not_found'])}")
    print(f"Failed: {len([r for r in results if r['status'] == 'download_failed'])}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Galaxy Flakes primary images from Pentacolor")
    parser.add_argument("--csv", default="data/output/farbe_metafields_galaxy_flakes.csv",
                      help="Path to Galaxy Flakes CSV with SKUs and barcodes")
    parser.add_argument("--output", default="data/supplier_images/galaxy_flakes",
                      help="Output directory for images")
    parser.add_argument("--dry-run", action="store_true",
                      help="Search only, don't download images")
    parser.add_argument("--test", action="store_true",
                      help="Test mode: only scrape first product")

    args = parser.parse_args()

    # Convert relative paths to absolute
    csv_path = os.path.abspath(args.csv)
    output_dir = os.path.abspath(args.output)

    print(f"CSV: {csv_path}")
    print(f"Output: {output_dir}")
    print(f"Dry run: {args.dry_run}")

    if args.test:
        print("\n⚠️  TEST MODE: Only scraping first product\n")
        # For test, just use the scraper directly
        scraper = PentacolorScraper(headless=False)  # Show browser in test mode
        try:
            result = scraper.search_product(
                sku="37047",
                barcode="5997412761122",
                product_name="Galaxy Flakes Jupiter white"
            )
            print(f"\nTest result: {result}")
        finally:
            scraper.close()
    else:
        scrape_galaxy_flakes_images(csv_path, output_dir, dry_run=args.dry_run)
