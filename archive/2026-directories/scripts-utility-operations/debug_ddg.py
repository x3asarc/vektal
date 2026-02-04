import requests
from bs4 import BeautifulSoup
import urllib.parse

def debug_ddg(query):
    url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    print(f"Requesting: {url}")
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        with open("ddg_debug.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
        print("\nSaved full HTML to ddg_debug.html")
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Print first 1000 chars of body
        print("\n--- HTML Snippet (First 1000 chars) ---")
        print(resp.text[:1000])
        
        # Try finding links
        links = soup.select('a.result__a')
        print(f"\nFound {len(links)} links with selector 'a.result__a'")
        for link in links[:3]:
            print(f" - {link.get('href')}")
            
        links_v2 = soup.find_all('a', class_='result__url')
        print(f"Found {len(links_v2)} links with class 'result__url'")
        for link in links_v2[:3]:
            print(f" - {link.get_text(strip=True)}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_ddg("Stamperia KFT450")
