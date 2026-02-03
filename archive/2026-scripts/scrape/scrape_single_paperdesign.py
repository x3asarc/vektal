import requests
from bs4 import BeautifulSoup
import time
import json

def scrape_paperdesigns_product(sku):
    """Scrape a single product from Paperdesigns with proper headers and delays"""

    search_url = f"https://paperdesigns.it/en/search?controller=search&s={sku}"
    print(f"Fetching: {search_url}")

    # Wait to avoid rate limiting
    time.sleep(2)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    })

    try:
        response = session.get(search_url, timeout=20)
        print(f"Status code: {response.status_code}")

        if response.status_code == 429:
            print("Rate limited. Waiting 10 seconds...")
            time.sleep(10)
            response = session.get(search_url, timeout=20)

        response.raise_for_status()

        # Save HTML for inspection
        with open(f"paperdesigns_{sku}_search.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"Saved HTML to paperdesigns_{sku}_search.html")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for products in search results
        products = soup.select('article.product-miniature')
        print(f"Found {len(products)} product(s) in search results")

        if not products:
            # Try alternative selectors
            products = soup.select('.product-item')
            print(f"Alternative search: Found {len(products)} product(s)")

        if not products:
            # Check if there's a direct product page
            if "product" in response.url:
                print("Redirected to product page directly")
                products = [soup]  # Treat whole page as product

        results = []
        for idx, product in enumerate(products):
            print(f"\nProduct {idx + 1}:")

            # Extract product link
            link_elem = product.select_one('a.product-thumbnail, a.product_img_link, h2 a, h3 a')
            product_url = None
            if link_elem:
                product_url = link_elem.get('href', '')
                if product_url and not product_url.startswith('http'):
                    product_url = f"https://paperdesigns.it{product_url}"
                print(f"  URL: {product_url}")

            # Extract title
            title_elem = product.select_one('h2.h3, h3, .product-title, h1')
            title = title_elem.get_text().strip() if title_elem else None
            print(f"  Title: {title}")

            # Extract image
            img_elem = product.select_one('img')
            image_url = img_elem.get('src', '') if img_elem else None
            if image_url and not image_url.startswith('http'):
                image_url = f"https://paperdesigns.it{image_url}"
            print(f"  Image: {image_url}")

            # Extract price
            price_elem = product.select_one('.price, .product-price')
            price = price_elem.get_text().strip() if price_elem else None
            print(f"  Price: {price}")

            results.append({
                "sku": sku,
                "title": title,
                "url": product_url,
                "image_url": image_url,
                "price": price
            })

        # Save results
        if results:
            with open(f"paperdesigns_{sku}_results.json", "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\nSaved results to paperdesigns_{sku}_results.json")

        return results

    except Exception as e:
        print(f"Error: {e}")
        return None

# Test with views_0009
if __name__ == "__main__":
    sku = "views_0009"
    results = scrape_paperdesigns_product(sku)

    if results:
        print(f"\n{'='*70}")
        print(f"Successfully scraped {len(results)} product(s)")
        print('='*70)
