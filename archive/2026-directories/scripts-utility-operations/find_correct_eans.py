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

# CONFIGURATION
MAX_RETRIES = 1
RETRY_DELAY = 1.0
MAX_LINKS_PER_SEARCH = 3 

def requests_get_with_retry(url, headers=None, timeout=15, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
    return None

def extract_ean(soup, raw_text):
    """Specific extractor for ITD EANs."""
    # 1. Look for .pinfo-ean class
    ean_elem = soup.select_one('.pinfo-ean span') or soup.select_one('.pinfo-ean')
    if ean_elem:
        ean_text = re.sub(r'\D', '', ean_elem.get_text())
        if len(ean_text) >= 13:
            return ean_text
    
    # 2. Broad regex on raw HTML text (handles cases where soup parsing might miss it)
    # EAN-13 search: 13 digits, typically starts with 590 (Poland)
    ean_matches = re.findall(r'\b(590\d{10})\b', raw_text)
    if ean_matches:
        # Return the first one found
        return ean_matches[0]
        
    return None

def find_ean_for_sku(sku):
    if not sku or pd.isna(sku): return None

    sku = str(sku).strip()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Variations: Original and stripped leading zeros
    variations = [sku]
    match = re.match(r'^([A-Za-z]*)(\d+)(.*)$', sku)
    if match:
        prefix, number, suffix = match.groups()
        if number:
            num_str = number
            while num_str.startswith('0') and len(num_str) > 1:
                num_str = num_str[1:]
                variations.append(f"{prefix}{num_str}{suffix}")
    
    seen = set()
    variations = [v for v in variations if v and not (v in seen or seen.add(v))]

    for sku_try in variations:
        try:
            search_url = f"https://www.itdcollection.com/q/?keywords={sku_try}"
            resp = requests_get_with_retry(search_url, headers=headers)
            if not resp: continue
            
            # Check if direct redirect to product page
            if 'q/' not in resp.url and 'szukaj' not in resp.url:
                ean = extract_ean(BeautifulSoup(resp.text, 'html.parser'), resp.text)
                if ean: return ean

            # Search Results links
            soup = BeautifulSoup(resp.text, 'html.parser')
            all_links = soup.find_all('a', href=True)
            for link in all_links[:15]: 
                href = link['href']
                if sku_try.lower() in href.lower() and not any(x in href.lower() for x in ['/q/', '/c/', '/r/', '/szukaj']):
                    full_url = f"https://www.itdcollection.com{href if href.startswith('/') else '/' + href}"
                    r_prod = requests_get_with_retry(full_url, headers=headers)
                    if not r_prod: continue
                    ean = extract_ean(BeautifulSoup(r_prod.text, 'html.parser'), r_prod.text)
                    if ean: return ean
        except:
            continue
    return None

def main():
    csv_file = 'itd_short_eans.csv'
    if not os.path.exists(csv_file):
        print("Error: itd_short_eans.csv not found")
        return

    df = pd.read_csv(csv_file)
    print(f"Searching for correct EANs for {len(df)} products...")

    results = []
    found_count = 0

    for idx, row in df.iterrows():
        sku = row['SKU']
        handle = row['Handle']
        print(f"[{idx+1}/{len(df)}] Searching for {sku}... ", end="", flush=True)
        
        ean = find_ean_for_sku(sku)
        
        if ean:
            print(f"✓ Found: {ean}")
            found_count += 1
            results.append({
                "Handle": handle,
                "SKU": sku,
                "OldBarcode": row['Barcode'],
                "ScrapedSKU": ean, # Script expectations: push_metadata_only reads ScrapedSKU
                "Success": "YES",
                "Vendor": "ITD Collection",
                "Country": "PL"
            })
        else:
            print("✗ Not found")
            results.append({
                "Handle": handle,
                "SKU": sku,
                "OldBarcode": row['Barcode'],
                "ScrapedSKU": None,
                "Success": "NO",
                "Vendor": "ITD Collection",
                "Country": "PL"
            })

        # Slower rate for reliability
        time.sleep(0.5)

    final_df = pd.DataFrame(results)
    final_df.to_csv('itd_ean_repaired.csv', index=False)
    print(f"\nDone! Found {found_count}/{len(df)} new EANs.")
    print("Saved to itd_ean_repaired.csv")

if __name__ == "__main__":
    main()
