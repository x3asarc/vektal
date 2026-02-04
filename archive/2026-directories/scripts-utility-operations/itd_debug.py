import os
import sys
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re
import urllib3
urllib3.disable_warnings()

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# OPTIMIZED CONFIGURATION
MAX_RETRIES = 1
RETRY_DELAY = 0.5
MAX_LINKS_PER_SEARCH = 5
SEARCH_TIMEOUT = 10

def requests_get_with_retry(url, headers=None, timeout=10, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    return None

def parse_price(price_str):
    if not price_str:
        return None
    try:
        is_pln = 'PLN' in str(price_str).upper() or 'ZŁ' in str(price_str).upper()
        clean = re.sub(r'[€$£PLNzłZŁ\s]', '', str(price_str), flags=re.IGNORECASE)
        clean = clean.replace(',', '.').strip()
        amount = float(clean)
        if is_pln:
            amount = round(amount * 0.23, 2)
        return amount
    except:
        return None

def is_valid_product_page(soup, url):
    if any(x in url.lower() for x in ['/q/', '/c/', '/r/', '/szukaj', 'basket', 'cart', 'login']):
        return False
    title = soup.find('h1')
    if not title:
        return False
    title_text = title.get_text(strip=True).lower()
    if len(title_text) < 5 or any(x in title_text for x in ['search', 'koszyk', 'cart', 'unavailable']):
        return False
    return True

def extract_product_data(soup, url):
    result = {"image_url": None, "scraped_sku": None, "price": None, "title": None, "country": "PL"}
    title_elem = soup.find('h1')
    if title_elem:
        result["title"] = title_elem.get_text(strip=True)
    
    # Image extraction - prioritize product images
    images = []
    for img in soup.find_all('img', src=True):
        src = img['src']
        if '/products/' in src or '/templates/images/products/' in src:
            if any(skip in src.lower() for skip in ['logo', 'banner', 'icon', '180/78']):
                continue
            # Normalize URL
            if not src.startswith('http'):
                base = 'itdcollection.com' if 'itd' in url else 'redcart.pl'
                src = f"https://www.{base}{src if src.startswith('/') else '/' + src}"
            
            # Simple scoring based on dimensions in URL
            score = 0
            dims = re.findall(r'/(\d+)/(\d+)/', src)
            if dims:
                score = int(dims[0][0]) * int(dims[0][1])
            else:
                score = 500 * 500 # Assume decent size
            
            images.append((score, src))
    
    if images:
        images.sort(key=lambda x: x[0], reverse=True)
        result["image_url"] = images[0][1]

    # SKU/EAN
    page_text = soup.get_text()
    ean_match = re.search(r'EAN[:\s]+(\d{8,})', page_text, re.IGNORECASE)
    if ean_match:
        result["scraped_sku"] = ean_match.group(1)

    # Price
    price_match = re.search(r'(?:Cena|Price)[:\s]+([0-9,.\s]+)\s*(?:PLN|zł|EUR|€)', page_text, re.IGNORECASE)
    if price_match:
        result["price"] = parse_price(price_match.group(1))

    return result

def optimized_sku_search(sku, handle, vendor):
    print(f"\n  Checking SKU: {sku}")
    result = {"image_url": None, "scraped_sku": None, "price": None, "title": None, "country": "PL", "method": "V4 Optimized"}
    
    if not sku or pd.isna(sku):
        return result

    sku = str(sku).strip()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Variations
    variations = [sku]
    match = re.match(r'^([A-Za-z]*)(\d+)(.*)$', sku)
    if match:
        prefix, number, suffix = match.groups()
        # Strip leading zeros one by one
        # R0088 -> R088, R88, 0088, 088, 88
        variations.append(number)
        num_str = number
        while num_str.startswith('0') and len(num_str) > 1:
            num_str = num_str[1:]
            variations.append(f"{prefix}{num_str}{suffix}")
            variations.append(num_str)
    
    # Remove duplicates
    seen = set()
    variations = [x for x in variations if x and not (x in seen or seen.add(x))]
    print(f"  Testing variations: {variations}")

    for sku_var in variations:
        search_url = f"https://www.itdcollection.com/q/?keywords={sku_var}"
        print(f"    Searching {sku_var}: ", end="", flush=True)
        
        resp = requests_get_with_retry(search_url, headers=headers)
        if not resp:
            print("timeout")
            continue
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # If redirect to product page
        if is_valid_product_page(soup, resp.url):
            data = extract_product_data(soup, resp.url)
            if data["image_url"]:
                print("✓ Found (Redirect)")
                result.update(data)
                result["method"] = f"V4 Redirect ({sku_var})"
                return result

        # Check search results
        links = soup.find_all('a', href=True)
        candidates = []
        for l in links:
            href = l['href']
            text = l.get_text(strip=True).lower()
            if any(x in href.lower() for x in ['/q/', '/c/', '/r/', '/szukaj', 'basket', 'cart']):
                continue
            
            # Match score
            score = 0
            if sku_var.lower() in href.lower(): score += 10
            if sku_var.lower() in text: score += 10
            if score > 0:
                candidates.append((score, href))
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, href in candidates[:MAX_LINKS_PER_SEARCH]:
            full_url = href if href.startswith('http') else f"https://www.itdcollection.com{href if href.startswith('/') else '/' + href}"
            r_prod = requests_get_with_retry(full_url, headers=headers)
            if not r_prod: continue
            
            soup_prod = BeautifulSoup(r_prod.text, 'html.parser')
            if is_valid_product_page(soup_prod, full_url):
                data = extract_product_data(soup_prod, full_url)
                if data["image_url"]:
                    print(f"✓ Found via link: {full_url}")
                    result.update(data)
                    result["method"] = f"V4 Search ({sku_var})"
                    return result
        
        print("✗")
    
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="debug_test.csv")
    args = parser.parse_args()
    
    df = pd.read_csv(args.csv)
    results = []
    
    for _, row in df.iterrows():
        sku = row.get("SKU")
        handle = row.get("Handle")
        vendor = row.get("Vendor")
        
        print(f"\nProcessing {handle}...")
        res = optimized_sku_search(sku, handle, vendor)
        
        entry = {
            "Handle": handle,
            "SKU": sku,
            "Success": "YES" if res["image_url"] else "NO",
            "Title": res["title"],
            "ImageURL": res["image_url"],
            "Method": res["method"]
        }
        results.append(entry)
    
    pd.DataFrame(results).to_csv("debug_results.csv", index=False)
    print("\nDone! Results saved to debug_results.csv")

if __name__ == "__main__":
    main()
