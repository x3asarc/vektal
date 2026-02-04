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
MAX_LINKS_PER_SEARCH = 3 
SEARCH_TIMEOUT = 10

def requests_get_with_retry(url, headers=None, timeout=10, max_retries=MAX_RETRIES):
    """Optimized retry wrapper."""
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
    """Parse price to EUR."""
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
    """Validation - updated for ITD pretty URLs."""
    # Fast URL check - skip generic pages
    if any(x in url.lower() for x in ['/q/', '/c/', '/r/', '/szukaj', 'basket', 'cart', 'login']):
        return False

    # Quick title check
    title = soup.find('h1')
    if not title:
        return False
        
    title_text = title.get_text(strip=True).lower()
    if len(title_text) < 5:
        return False

    # Quick generic title check
    if any(x in title_text for x in ['search', 'koszyk', 'cart', 'unavailable', 'produkty w schowku']):
        return False

    return True

def extract_product_data(soup, url):
    """Extraction - optimized for Redcart/ITD."""
    result = {"image_url": None, "scraped_sku": None, "price": None, "title": None, "country": "PL", "product_url": url}

    # Title
    title_elem = soup.find('h1')
    if title_elem:
        result["title"] = title_elem.get_text(strip=True)

    # Image - prioritize high res and product shots
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
                
            # Score by dimensions in URL or presence in product gallery
            score = 0
            dims = re.findall(r'/(\d+)/(\d+)/', src)
            if dims:
                score = int(dims[0][0]) * int(dims[0][1])
            else:
                score = 500 * 500 # Default for non-dimensioned URLs
            
            images.append((score, src))
    
    if images:
        images.sort(key=lambda x: x[0], reverse=True)
        result["image_url"] = images[0][1]

    # EAN/SKU - Site specific + General regex
    # 1. Search for pinfo-ean class (ITD specific)
    ean_elem = soup.select_one('.pinfo-ean span') or soup.select_one('.pinfo-ean')
    if ean_elem:
        ean_text = re.sub(r'\D', '', ean_elem.get_text())
        if len(ean_text) >= 8:
            result["scraped_sku"] = ean_text
            
    # 2. Fallback to general regex if still missing
    if not result["scraped_sku"]:
        page_text = soup.get_text()
        ean_match = re.search(r'EAN[:\s]+(\d{8,})', page_text, re.IGNORECASE)
        if ean_match:
            result["scraped_sku"] = ean_match.group(1)

    # 3. Producer Code (fallback SKU)
    code_elem = soup.select_one('.pinfo-code span') or soup.select_one('.pinfo-code')
    if code_elem and not result["scraped_sku"]:
        code_text = code_elem.get_text().replace('Kod producenta:', '').replace('Producer code:', '').strip()
        if code_text:
            result["scraped_sku"] = code_text

    # Price
    price_match = re.search(r'(?:Cena|Price)[:\s]+([0-9,.\s]+)\s*(?:PLN|zł|EUR|€)', soup.get_text(), re.IGNORECASE)
    if price_match:
        result["price"] = parse_price(price_match.group(1))

    return result

def optimized_sku_search(sku, handle, vendor):
    """V4 UPDATED: Handles zero-stripping and pretty URL matching."""
    result = {"image_url": None, "scraped_sku": None, "price": None, "title": None, "country": "PL", "method": "V4 Optimized"}
    
    if not sku or pd.isna(sku):
        return result

    sku = str(sku).strip()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Variations: Original, Numbers only, and stripped leading zeros
    variations = [sku]
    match = re.match(r'^([A-Za-z]*)(\d+)(.*)$', sku)
    if match:
        prefix, number, suffix = match.groups()
        if number:
            variations.append(number)
            # Add zero-stripped versions: R0088 -> R088, R88, 088, 88
            num_str = number
            while num_str.startswith('0') and len(num_str) > 1:
                num_str = num_str[1:]
                variations.append(f"{prefix}{num_str}{suffix}")
                variations.append(num_str)
    
    # Unique variations
    seen = set()
    variations = [v for v in variations if v and not (v in seen or seen.add(v))]
    
    print(f"  Testing {len(variations)} variations: {variations}")

    for sku_try in variations:
        try:
            search_url = f"https://www.itdcollection.com/q/?keywords={sku_try}"
            print(f"    {sku_try}: ", end="", flush=True)
            
            resp = requests_get_with_retry(search_url, headers=headers)
            if not resp:
                print("✗ timeout")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Check if redirected to product page
            if is_valid_product_page(soup, resp.url):
                data = extract_product_data(soup, resp.url)
                if data["image_url"]:
                    print("✓ (Direct)")
                    result.update(data)
                    result["method"] = f"V4 Redirect ({sku_try})"
                    return result

            # 2. Check search results
            all_links = soup.find_all('a', href=True)
            candidates = []
            for link in all_links:
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                if any(x in href.lower() for x in ['/q/', '/c/', '/r/', '/szukaj', 'basket', 'cart', 'login', 'register']):
                    continue
                
                score = 0
                if sku_try.lower() in href.lower(): score += 10
                if sku_try.lower() in text: score += 10
                
                if score > 0:
                    candidates.append((score, href))
            
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            # Limit checking to top candidates
            for _, href in candidates[:MAX_LINKS_PER_SEARCH]:
                full_url = href if href.startswith('http') else f"https://www.itdcollection.com{href if href.startswith('/') else '/' + href}"
                r_prod = requests_get_with_retry(full_url, headers=headers)
                if not r_prod: continue
                
                soup_prod = BeautifulSoup(r_prod.text, 'html.parser')
                if is_valid_product_page(soup_prod, full_url):
                    data = extract_product_data(soup_prod, full_url)
                    if data["image_url"]:
                        print(f"✓ ({sku_try})")
                        result.update(data)
                        result["method"] = f"V4 Search ({sku_try})"
                        return result
            
            print("✗")
        except:
            print("!")
            continue

    return result

def manual_url_fallback(sku, handle, vendor, manual_url):
    """Manual URL override."""
    print(f"\n  === FALLBACK: Manual URL ===")
    result = {"image_url": None, "scraped_sku": None, "price": None, "title": None, "country": "PL", "method": "Manual URL"}
    if not manual_url or pd.isna(manual_url) or str(manual_url).strip() == "":
        return result

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests_get_with_retry(manual_url, headers=headers)
        if not response: return result
        soup = BeautifulSoup(response.text, 'html.parser')
        if is_valid_product_page(soup, manual_url):
            data = extract_product_data(soup, manual_url)
            if data["image_url"]:
                print(f"    ✓ SUCCESS")
                result.update(data)
                result["method"] = "Manual URL"
    except Exception as e:
        print(f"    ✗ Error: {e}")
    return result

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--csv", default="data/not_found.csv")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    print("=" * 80)
    print(f"NOT FOUND FINDER V4.1 - {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 80)

    if not os.path.exists(args.csv):
        print(f"ERROR: {args.csv} not found!")
        return

    df = pd.read_csv(args.csv)
    if args.limit: df = df.head(args.limit)

    results = []
    success_count = 0
    start_time = time.time()

    for index, row in df.iterrows():
        handle, sku, vendor = row.get("Handle"), row.get("SKU"), row.get("Vendor")
        manual_url = row.get("URL", "")

        print(f"\n[{index+1}/{len(df)}] {handle} | SKU: {sku}")
        
        # Try optimized search
        result = optimized_sku_search(sku, handle, vendor)

        # A4 Price Override Logic
        is_a4 = "a4" in handle.lower() or (result.get("title") and "a4" in result.get("title", "").lower())
        if is_a4 and vendor == "ITD Collection":
            print(f"    (A4 detected -> Setting price to 1.04)")
            result["price"] = 1.04

        # Fallback to manual URL
        if not result.get("image_url") and manual_url and str(manual_url).strip():
            result = manual_url_fallback(sku, handle, vendor, manual_url)

        # Log result
        res_entry = {
            "Handle": handle, "SKU": sku, "Vendor": vendor,
            "Method": result.get("method", "Unknown"),
            "Success": "YES" if result.get("image_url") else "NO",
            "Title": result.get("title", ""),
            "ImageURL": result.get("image_url", ""),
            "ProductURL": result.get("product_url", ""),
            "ScrapedSKU": result.get("scraped_sku", ""),
            "Price_EUR": result.get("price", ""),
            "Country": result.get("country", ""),
        }
        results.append(res_entry)

        if result.get("image_url"):
            success_count += 1
            print(f"    >>> SUCCESS ✓")
        else:
            print(f"    >>> FAILED ✗")

        # Save progress
        if (index + 1) % 10 == 0:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            mode = "dryrun" if args.dry_run else "live"
            temp = f"test_results_v4_1_{mode}_progress_{ts}.csv"
            pd.DataFrame(results).to_csv(temp, index=False)

    # Final Save
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "dryrun" if args.dry_run else "live"
    final_file = f"test_results_v4_1_{mode}_{ts}.csv"
    pd.DataFrame(results).to_csv(final_file, index=False)

    print("\n" + "=" * 80)
    print(f"COMPLETED: {success_count}/{len(df)} found ({success_count/len(df)*100:.1f}%)")
    print(f"File: {final_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
