"""
Inspect pentacolor.eu product page to find correct image selectors
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup driver
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Load the product page we found
    url = "https://www.pentacolor.eu/galaxy-flakes-253844"
    print(f"Loading: {url}")
    driver.get(url)
    time.sleep(3)

    print(f"\nPage title: {driver.title}")
    print(f"Current URL: {driver.current_url}")

    # Find ALL images on the page
    print("\n" + "="*70)
    print("ALL IMAGES ON PAGE:")
    print("="*70)

    all_imgs = driver.find_elements(By.TAG_NAME, "img")
    print(f"\nFound {len(all_imgs)} total images")

    for i, img in enumerate(all_imgs, 1):
        src = img.get_attribute('src') or img.get_attribute('data-src') or "no-src"
        alt = img.get_attribute('alt') or "no-alt"
        classes = img.get_attribute('class') or "no-class"

        # Filter out obvious non-product images
        if any(skip in src.lower() for skip in ['logo', 'icon', 'banner', 'payment']):
            continue

        print(f"\n{i}. SRC: {src[:100]}...")
        print(f"   ALT: {alt}")
        print(f"   CLASS: {classes}")

    # Try to find the main product image specifically
    print("\n" + "="*70)
    print("LOOKING FOR MAIN PRODUCT IMAGE:")
    print("="*70)

    # Check page source for clues
    page_source = driver.page_source
    if 'og:image' in page_source:
        print("\nFound Open Graph image meta tag")
        og_img = driver.find_element(By.CSS_SELECTOR, "meta[property='og:image']")
        if og_img:
            print(f"OG Image: {og_img.get_attribute('content')}")

finally:
    driver.quit()
