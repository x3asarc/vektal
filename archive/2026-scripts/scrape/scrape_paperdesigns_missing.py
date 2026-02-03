import sys
import os
import requests
from bs4 import BeautifulSoup
import csv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Missing products with their quantities
missing_products = {
    "views_0009": 8,
    "views_0167": 11,
    "views_0084": 8,
    "rc003": 20
}

def scrape_paperdesigns(sku):
    """Scrape product data from Paperdesigns website"""
    # Clean SKU for search (remove underscores/hyphens)
    sku_clean = sku.replace('_', '').replace('-', '').lower()
    search_url = f"https://paperdesigns.it/en/search?controller=search&s={sku}"

    print(f"  Searching: {search_url}")

    # Realistic headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
    })

    try:
        # Get search results
        r = session.get(search_url, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        # Find product link
        product_link = None
        article = soup.select_one('article.product-miniature')
        if article:
            link_elem = article.select_one('a.product-thumbnail')
            if link_elem:
                product_link = link_elem.get('href')

        if not product_link:
            print(f"  [NOT FOUND] No product found for {sku}")
            return None

        if not product_link.startswith('http'):
            product_link = f"https://paperdesigns.it{product_link}"

        print(f"  Found product: {product_link}")

        # Get product details page
        r_prod = session.get(product_link, timeout=15)
        soup_prod = BeautifulSoup(r_prod.text, 'html.parser')

        # Extract data
        result = {}

        # Title
        title_elem = soup_prod.select_one('h1.h1')
        if title_elem:
            result["title"] = title_elem.get_text().strip()

        # Image
        img_elem = soup_prod.select_one('img.js-qv-product-cover')
        if img_elem:
            result["image_url"] = img_elem.get('src')
            if result["image_url"] and not result["image_url"].startswith('http'):
                result["image_url"] = f"https://paperdesigns.it{result['image_url']}"

        # Price
        price_elem = soup_prod.select_one('.product-prices .current-price span[content]')
        if price_elem:
            result["price"] = price_elem.get('content')

        # Description
        desc_elem = soup_prod.select_one('.product-description')
        if desc_elem:
            result["description"] = desc_elem.get_text().strip()

        # Barcode (might be in product details or reference)
        ref_elem = soup_prod.select_one('[itemprop="sku"]')
        if ref_elem:
            result["reference"] = ref_elem.get_text().strip()

        result["sku"] = sku
        result["vendor"] = "Paperdesigns"
        result["country"] = "IT"
        result["hs_code"] = "4823.90"  # Rice paper HS code
        result["weight"] = "30"  # 30g average for rice papers
        result["product_url"] = product_link

        return result

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Request failed: {e}")
        return None
    except Exception as e:
        print(f"  [ERROR] Scraping failed: {e}")
        return None

print("="*70)
print("Scraping missing products from Paperdesigns")
print("="*70)
print()

results = []

for sku, qty in missing_products.items():
    print(f"--- Scraping: {sku} (Quantity: {qty}) ---")
    data = scrape_paperdesigns(sku)

    if data:
        data["target_quantity"] = qty
        results.append(data)
        print(f"  [SUCCESS]")
        print(f"    Title: {data.get('title', 'N/A')}")
        print(f"    Price: {data.get('price', 'N/A')}")
        print(f"    Image: {data.get('image_url', 'N/A')[:60]}...")
    else:
        results.append({
            "sku": sku,
            "target_quantity": qty,
            "status": "NOT_FOUND",
            "vendor": "Paperdesigns"
        })

    print()

# Save results
if results:
    with open("missing_products_scraped.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sku", "title", "vendor", "price", "image_url", "description",
            "reference", "country", "hs_code", "weight", "product_url",
            "target_quantity", "status"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print("\n" + "="*70)
    print(f"Results saved to: missing_products_scraped.csv")
    print(f"Successfully scraped: {sum(1 for r in results if r.get('title'))}/{len(results)} products")
    print("="*70)
