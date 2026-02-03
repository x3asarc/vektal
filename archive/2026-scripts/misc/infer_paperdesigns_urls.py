import requests
import time
from bs4 import BeautifulSoup
import json

# Target SKUs
skus = {
    "views_0167": ["views-0167", "views_0167"],
    "views_0084": ["views-0084", "views_0084"],
    "rc003": ["rc003", "rc-003"]
}

# Common description patterns for views products
view_descriptions = [
    "views-rice-paper-for-the-decoupage",
    "rice-paper-for-the-decoupage",
    "landscape-rice-paper-for-the-decoupage",
    "rice-paper",
]

# Categories to try
categories = [
    "rice-paper-landscape",
    "rice-paper-portrait",
    "rice-paper-large-format",
]

def test_url(url, sku_key):
    """Test if a URL exists and extract data"""
    print(f"  Testing: {url}")
    time.sleep(2)

    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

        response = session.get(url, timeout=15, allow_redirects=True)

        if response.status_code == 200 and "product" in response.url:
            print(f"    ✓ FOUND! {response.url}")

            # Parse page
            soup = BeautifulSoup(response.text, 'html.parser')

            data = {
                "sku": sku_key,
                "url": response.url,
            }

            # Title
            title = soup.select_one('h1.h1, h1')
            if title:
                data["title"] = title.get_text().strip()

            # Image
            img = soup.select_one('img.js-qv-product-cover, img[itemprop="image"]')
            if img:
                data["image_url"] = img.get('src', img.get('data-src', ''))
                if data["image_url"] and not data["image_url"].startswith('http'):
                    data["image_url"] = f"https://paperdesigns.it{data['image_url']}"

            # Price
            price = soup.select_one('[itemprop="price"], .current-price span')
            if price:
                data["price"] = price.get_text().strip()

            # Reference
            ref = soup.select_one('[itemprop="sku"]')
            if ref:
                data["reference"] = ref.get_text().strip()

            return data

        return None

    except Exception as e:
        return None

print("="*70)
print("Inferring Paperdesigns URLs")
print("="*70)

found = {}

# Try to construct URLs by testing different patterns
for sku_key, sku_variations in skus.items():
    print(f"\n--- Searching for: {sku_key} ---")

    # Try direct image URL pattern (often works)
    for sku_var in sku_variations:
        # Try common image IDs (increment from known pattern)
        for img_id in range(3900, 4100, 5):  # Try range around 3925
            img_url = f"https://paperdesigns.it/{img_id}-superlarge_default/{sku_var}-rice-paper-for-the-decoupage.jpg"
            try:
                r = requests.head(img_url, timeout=5)
                if r.status_code == 200:
                    print(f"  ✓ Found image: {img_url}")
                    # Now try to find product page
                    # Extract from image URL pattern
                    found[sku_key] = {"image_url": img_url, "sku": sku_key}
                    break
            except:
                pass
            time.sleep(0.5)

        if sku_key in found:
            break

    # Try constructing product URLs
    if sku_key not in found:
        for category in categories:
            for sku_var in sku_variations:
                for desc in view_descriptions:
                    # Try different product ID ranges
                    for prod_id in range(1900, 2100, 50):
                        url = f"http://paperdesigns.it/en/{category}/{prod_id}-{sku_var}-{desc}.html"
                        result = test_url(url, sku_key)
                        if result:
                            found[sku_key] = result
                            break
                    if sku_key in found:
                        break
                if sku_key in found:
                    break
            if sku_key in found:
                break

print("\n" + "="*70)
print(f"RESULTS: Found {len(found)}/{len(skus)} products")
print("="*70)

for sku, data in found.items():
    print(f"\n{sku}:")
    for key, value in data.items():
        print(f"  {key}: {value}")

if found:
    with open("inferred_paperdesigns_products.json", "w", encoding="utf-8") as f:
        json.dump(found, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: inferred_paperdesigns_products.json")
