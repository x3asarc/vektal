import requests
from bs4 import BeautifulSoup
import time
import json

missing_skus = ["views_0167", "views_0084", "rc003"]

def search_paperdesigns(sku):
    """Try to find product by searching the site"""
    search_url = f"https://paperdesigns.it/en/search?controller=search&s={sku}"

    print(f"\nSearching for: {sku}")
    print(f"URL: {search_url}")
    print("Waiting 6 seconds...")
    time.sleep(6)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        response = session.get(search_url, timeout=20)
        print(f"Status: {response.status_code}")

        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for product links
        products = soup.select('article.product-miniature')
        print(f"Found {len(products)} products")

        if products:
            for product in products[:3]:  # Show first 3
                link_elem = product.select_one('a.product-thumbnail, h2 a, h3 a')
                if link_elem:
                    url = link_elem.get('href', '')
                    title_elem = product.select_one('h2, h3, .product-title')
                    title = title_elem.get_text().strip() if title_elem else "No title"
                    print(f"  - {title}")
                    print(f"    {url}")

                    # Try to extract image
                    img_elem = product.select_one('img')
                    if img_elem:
                        img_url = img_elem.get('src', img_elem.get('data-src', ''))
                        print(f"    Image: {img_url}")

                    return {"url": url, "title": title}

        return None

    except Exception as e:
        print(f"Error: {e}")
        return None

print("="*70)
print("Searching for remaining products on Paperdesigns")
print("="*70)

results = {}
for sku in missing_skus:
    result = search_paperdesigns(sku)
    if result:
        results[sku] = result
    time.sleep(3)  # Extra delay between searches

print("\n" + "="*70)
print("RESULTS")
print("="*70)
for sku, data in results.items():
    print(f"\n{sku}:")
    print(f"  URL: {data.get('url')}")
    print(f"  Title: {data.get('title')}")

if results:
    with open("remaining_products_found.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: remaining_products_found.json")
