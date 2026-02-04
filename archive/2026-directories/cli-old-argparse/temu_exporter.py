import os
import csv
import json
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
# Path to your Chrome User Data. 
# FIND IT HERE: chrome://version/ -> "Profile Path"
# Example: C:\Users\Hp\AppData\Local\Google\Chrome\User Data
CHROME_USER_DATA_DIR = r"C:\Users\Hp\AppData\Local\Google\Chrome\User Data" 
PROFILE_DIRECTORY = "Default"  # Or "Profile 1", "Profile 2" if you have multiple

OUTPUT_CSV = "data/temu_export.csv"

def get_driver():
    """Launch Chrome with specific User Data to reuse login session."""
    options = Options()
    # options.add_argument("--headless") # Don't run headless yet, to verify login
    options.add_argument(f"user-data-dir={CHROME_USER_DATA_DIR}")
    options.add_argument(f"profile-directory={PROFILE_DIRECTORY}")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    
    # Crucial for not being blocked as a bot instantly
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    return driver

def scrape_temu_orders():
    driver = get_driver()
    try:
        print("Opening Temu Orders Page...")
        # Note: You must be logged in for this to work.
        driver.get("https://www.temu.com/your-orders.html") 
        time.sleep(5) # Wait for load

        if "login" in driver.current_url:
            print("❌ Not logged in! Please log in within the browser window manually.")
            print("Script will wait 60 seconds for you to login...")
            time.sleep(60)

        input("✅ Press ENTER in terminal once you are on the 'All Orders' page and it is fully loaded...")

        # Find all order items (this selector implies the page structure, might need tuning)
        # Temu dynamic classes are tricky. We might need to look for specific textual markers.
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Prototype extractor - User will likely need to adjust selectors based on actual DOM
        products = []
        
        # Generalized strategy: Look for order cards
        # This is a PLACEHOLDER selector strategy as Temu obfuscates classes.
        # We look for image containers and title containers nearby.
        
        # Better strategy: Get all links that look like product links
        links = soup.find_all('a', href=True)
        for l in links:
            href = l['href']
            # Temu product links usually have 'goods.html' or specific ID patterns
            if 'goods_id=' in href or '/goods' in href:
                title = l.get_text(strip=True)
                if len(title) > 5: # likely a product title
                    img_tag = l.find('img')
                    img_url = img_tag['src'] if img_tag else None
                    
                    products.append({
                        "Handle": title[:50].replace(" ", "-").lower(), # simple handle
                        "Title": title,
                        "Product URL": f"https://www.temu.com{href}" if not href.startswith('http') else href,
                        "Image URL": img_url,
                        "Vendor": "Temu"
                    })
        
        print(f"Found {len(products)} potential products.")
        
        # Save to CSV
        keys = ["Handle", "Title", "Product URL", "Image URL", "Vendor"]
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(products)
            
        print(f"Exported to {OUTPUT_CSV}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_temu_orders()
