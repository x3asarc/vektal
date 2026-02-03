import requests
from bs4 import BeautifulSoup

def verify_pentart_search(barcode):
    # Try different common search patterns
    patterns = [
        f"https://pentart.eu/search?q={barcode}",
        f"https://pentart.eu/en/search?q={barcode}",
        f"https://pentacolor.eu/search?q={barcode}",
        f"https://pentacolor.eu/en/search?q={barcode}",
        f"https://pentart.eu/products?query={barcode}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Testing search for barcode: {barcode}")
    
    for url in patterns:
        print(f"Checking {url}...")
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Check if we found results
                if "no products found" not in soup.text.lower():
                     print(f"  Posible match on {url}")
                     # Try to find product links
                     links = soup.find_all('a', href=True)
                     for link in links:
                         href = link['href']
                         if '/product' in href or '/item' in href:
                             print(f"    Found product link: {href}")
        except Exception as e:
            print(f"  Error: {e}")

if __name__ == "__main__":
    verify_pentart_search("5997412772012")
