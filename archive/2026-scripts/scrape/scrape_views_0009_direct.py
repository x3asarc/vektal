import requests
from bs4 import BeautifulSoup
import time
import json

product_url = "http://paperdesigns.it/en/rice-paper-landscape/1950-5850-views-0009-views-rice-paper-for-the-decoupage.html"

print(f"Fetching: {product_url}")
print("Waiting 5 seconds to avoid rate limiting...")
time.sleep(5)

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://paperdesigns.it/",
})

try:
    response = session.get(product_url, timeout=20)
    print(f"Status: {response.status_code}")

    if response.status_code != 200:
        print(f"Failed: {response.status_code}")
        exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')

    result = {
        "sku": "views_0009",
        "vendor": "Paperdesigns",
        "country": "IT",
        "hs_code": "4823.90",
        "product_url": product_url,
        "image_url": "https://paperdesigns.it/3925-superlarge_default/views-0009-views-rice-paper-for-the-decoupage.jpg"
    }

    # Title
    title_elem = soup.select_one('h1.h1, h1')
    if title_elem:
        result["title"] = title_elem.get_text().strip()
        print(f"Title: {result['title']}")

    # Price - look for different price selectors
    price_elem = soup.select_one('[itemprop="price"], .current-price span, .product-price')
    if price_elem:
        result["price"] = price_elem.get_text().strip()
        print(f"Price: {result['price']}")

    # Reference/SKU
    ref_elem = soup.select_one('[itemprop="sku"]')
    if ref_elem:
        result["reference"] = ref_elem.get_text().strip()
        print(f"Reference: {result['reference']}")

    # Description
    desc_elem = soup.select_one('.product-description, [itemprop="description"]')
    if desc_elem:
        result["description"] = desc_elem.get_text().strip()
        print(f"Description: {result['description'][:100]}...")

    # Weight (typical for rice paper)
    result["weight"] = "30"  # 30g average

    # Variants/Sizes
    size_options = soup.select('.product-variants select option, .attribute_list option')
    if size_options:
        result["sizes"] = [opt.get_text().strip() for opt in size_options if opt.get_text().strip()]
        print(f"Available sizes: {result['sizes']}")

    print("\n" + "="*70)
    print("Product data extracted:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("="*70)

    # Save to file
    with open("views_0009_product_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nSaved to: views_0009_product_data.json")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
