import requests
from bs4 import BeautifulSoup
import time
import json
import re

target_skus = {"views_0167", "views_0084", "rc003", "views_0009"}  # Including 0009 to verify

def scrape_category_page(url, session, found_products):
    """Scrape a single category page for products"""
    print(f"\nScraping: {url}")
    time.sleep(3)

    try:
        response = session.get(url, timeout=20)
        if response.status_code != 200:
            print(f"  Failed: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        products = soup.select('article.product-miniature')
        print(f"  Found {len(products)} products on page")

        for product in products:
            # Get product link
            link_elem = product.select_one('a.product-thumbnail, h2 a, h3 a')
            if not link_elem:
                continue

            product_url = link_elem.get('href', '')
            if not product_url.startswith('http'):
                product_url = f"https://paperdesigns.it{product_url}"

            # Extract SKU from URL or title
            # URL format: .../1950-5850-views-0009-views-rice-paper...
            url_parts = product_url.split('/')[-1]
            matches = re.findall(r'(views[_-]\d+|tiles[_-]\d+|time[_-]\d+|rc\d+)', url_parts, re.IGNORECASE)

            if matches:
                sku = matches[0].lower().replace('-', '_')
                print(f"    Found SKU: {sku}")

                if sku in target_skus:
                    # Get title
                    title_elem = product.select_one('h2, h3, .product-title')
                    title = title_elem.get_text().strip() if title_elem else ""

                    # Get image
                    img_elem = product.select_one('img')
                    image_url = img_elem.get('src', img_elem.get('data-src', '')) if img_elem else ""
                    if image_url and not image_url.startswith('http'):
                        image_url = f"https://paperdesigns.it{image_url}"

                    found_products[sku] = {
                        "sku": sku,
                        "title": title,
                        "url": product_url,
                        "image_url": image_url
                    }
                    print(f"      ✓ MATCH FOUND: {title}")

        # Check for next page
        next_page = soup.select_one('a.next, .pagination a[rel="next"]')
        if next_page:
            next_url = next_page.get('href', '')
            if next_url and not next_url.startswith('http'):
                next_url = f"https://paperdesigns.it{next_url}"
            return [next_url]

        return []

    except Exception as e:
        print(f"  Error: {e}")
        return []

# Main script
print("="*70)
print("Browsing Paperdesigns catalog for target products")
print("="*70)
print(f"Looking for: {target_skus}")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
})

found_products = {}

# Start with rice paper landscape category (where views products are)
categories_to_check = [
    "https://paperdesigns.it/en/56-rice-paper-landscape",
    "https://paperdesigns.it/en/58-rice-paper-portrait",
    "https://paperdesigns.it/en/rice-paper",
]

for category_url in categories_to_check:
    if len(found_products) >= len(target_skus):
        break  # Found all

    pages_to_scrape = [category_url]
    visited = set()

    while pages_to_scrape and len(found_products) < len(target_skus):
        current_url = pages_to_scrape.pop(0)

        if current_url in visited:
            continue
        visited.add(current_url)

        next_pages = scrape_category_page(current_url, session, found_products)
        pages_to_scrape.extend([p for p in next_pages if p not in visited])

        # Limit pages per category
        if len(visited) >= 5:  # Max 5 pages per category
            break

print("\n" + "="*70)
print(f"RESULTS: Found {len(found_products)}/{len(target_skus)} products")
print("="*70)

for sku, data in found_products.items():
    print(f"\n{sku}:")
    print(f"  Title: {data['title']}")
    print(f"  URL: {data['url']}")
    print(f"  Image: {data['image_url']}")

if found_products:
    with open("paperdesigns_catalog_results.json", "w", encoding="utf-8") as f:
        json.dump(found_products, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: paperdesigns_catalog_results.json")

# Show missing
missing = target_skus - set(found_products.keys())
if missing:
    print(f"\nStill missing: {missing}")
