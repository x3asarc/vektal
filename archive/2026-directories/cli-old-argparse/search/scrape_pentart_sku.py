import requests
from bs4 import BeautifulSoup
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import json

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver

def search_pentart_website(barcode, product_name):
    """Search Pentart website for the product using barcode and product name"""

    # Pentart website (common domain for Pentart products)
    pentart_domains = [
        "https://www.pentart.hu",
        "https://pentart.hu"
    ]

    driver = setup_driver()

    try:
        for base_url in pentart_domains:
            print(f"\n{'='*60}")
            print(f"Trying {base_url}...")

            try:
                # Try to access the main page first
                driver.get(base_url)
                time.sleep(2)
                print(f"Successfully accessed {base_url}")
                print(f"Page title: {driver.title}")

                # Look for search box
                search_selectors = [
                    "input[type='search']",
                    "input[name='s']",
                    "input[name='search']",
                    "input.search-field",
                    "#search",
                    ".search-input"
                ]

                search_box = None
                for selector in search_selectors:
                    try:
                        search_box = driver.find_element(By.CSS_SELECTOR, selector)
                        if search_box:
                            print(f"Found search box with selector: {selector}")
                            break
                    except:
                        continue

                if search_box:
                    # Try searching with barcode first
                    print(f"\nSearching for barcode: {barcode}")
                    search_box.clear()
                    search_box.send_keys(barcode)
                    search_box.submit()
                    time.sleep(3)

                    # Check if we found results
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')

                    # Look for product information
                    print("\n--- Page Content Analysis ---")
                    print(f"Page URL: {driver.current_url}")
                    print(f"Page title: {driver.title}")

                    # Look for SKU patterns in the page
                    sku_patterns = soup.find_all(text=lambda text: text and ('SKU' in text.upper() or 'Art.' in text or 'Artikel' in text))

                    if sku_patterns:
                        print("\nFound potential SKU information:")
                        for pattern in sku_patterns[:5]:
                            print(f"  - {pattern.strip()}")

                    # Try searching with product name if barcode didn't work
                    if "no results" in driver.page_source.lower() or "keine ergebnisse" in driver.page_source.lower():
                        print(f"\nNo results for barcode. Trying product name search...")
                        search_terms = [
                            "Mixed Media Tinte Blau",
                            "Mixed Media Blue",
                            "5997412772012"
                        ]

                        for term in search_terms:
                            print(f"\nSearching for: {term}")
                            try:
                                search_box = driver.find_element(By.CSS_SELECTOR, search_selectors[0])
                                search_box.clear()
                                search_box.send_keys(term)
                                search_box.submit()
                                time.sleep(3)

                                page_source = driver.page_source
                                if "no results" not in page_source.lower():
                                    print(f"Found results for: {term}")
                                    print(f"Current URL: {driver.current_url}")
                                    break
                            except Exception as e:
                                print(f"Error searching for {term}: {e}")
                                continue

                    # Save the page source for manual inspection
                    with open("pentart_search_results.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print("\nSaved page source to pentart_search_results.html")

                else:
                    print("Could not find search box. Saving homepage...")
                    with open("pentart_homepage.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    print("Saved homepage to pentart_homepage.html")

            except Exception as e:
                print(f"Error accessing {base_url}: {e}")
                continue

    finally:
        driver.quit()

def try_direct_barcode_lookup(barcode):
    """Try looking up the barcode in online databases"""
    print(f"\n{'='*60}")
    print("Trying barcode lookup services...")

    # Try UPC database
    try:
        url = f"https://www.ean-search.org/?q={barcode}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            print(f"\nEAN Search results:")
            print(f"URL: {url}")

            # Look for product information
            product_info = soup.find('div', class_='detaillist')
            if product_info:
                print("\nProduct Information Found:")
                print(product_info.get_text(strip=True))

            # Save results
            with open("barcode_lookup_results.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("\nSaved barcode lookup results to barcode_lookup_results.html")

    except Exception as e:
        print(f"Error with barcode lookup: {e}")

if __name__ == "__main__":
    barcode = "5997412772012"
    product_name = "Pentart Mixed Media Tinte 20ml - Blau"

    print(f"Searching for product:")
    print(f"  Name: {product_name}")
    print(f"  Barcode: {barcode}")

    # Try barcode lookup first
    try_direct_barcode_lookup(barcode)

    # Try Pentart website
    search_pentart_website(barcode, product_name)

    print("\n" + "="*60)
    print("Search complete. Check the saved HTML files for manual review.")
