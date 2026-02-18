import os
import time
import argparse
import logging
import re
import pandas as pd
import requests
from urllib.parse import urlparse
import mimetypes
import json
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

# --- Configuration --- #
from src.core.paths import SCRAPED_IMAGES_DIR, PUSH_PROOF_CSV
BASE_URL = os.getenv("SHOPIFY_STORE_URL")
OUTPUT_DIR = SCRAPED_IMAGES_DIR

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Product List --- #
# Each tuple contains (product_name_for_folder, sku)
products_to_scrape = [
    ("Buntstifte", "1111111"),
    ("Bleistifte", "2222222"),
    ("Filzstifte", "3333333"),
    ("Aquarellfarben", "4444444"),
    ("Acrylfarben", "5555555"),
    ("Pinsel-Set", "6666666"),
    ("Leinwand", "7777777"),
    ("Skizzenbuch", "8888888"),
    ("Modelliertonerde", "9999999"),
    ("Sprühfarben", "1010101"),
    ("Ölfarbe Filz", "2211122")
]

# --- Helper Functions --- #
def get_valid_filename(s, max_length=200):
    """
    Sanitize a string to create a valid, SEO-friendly filename.

    Args:
        s: String to sanitize
        max_length: Maximum filename length (default 200, excluding extension)

    Returns:
        Sanitized filename string
    """
    s = str(s).strip().replace(' ', '_')
    # Remove invalid characters
    s = re.sub(r'(?u)[^-\w.]', '', s)
    # Convert to lowercase for consistency
    s = s.lower()
    # Limit length (reserve space for extension)
    if len(s) > max_length:
        s = s[:max_length]
    return s


def clean_product_name(title):
    """
    Clean product name for alt text - remove UUIDs, HS codes, and technical patterns.

    This function improves SEO and accessibility by removing technical identifiers
    from product titles before using them as alt text or filenames.

    Args:
        title: Product title string to clean

    Returns:
        Cleaned title string suitable for alt text, or None if input is None
    """
    if not title:
        return None

    # Remove UUID patterns (e.g., _8a4d9e6f-1234-5678-9012-abcdef123456)
    cleaned = re.sub(r'_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '', title)

    # Remove HS Code patterns (e.g., HS code 48021000, (HS: 12345))
    cleaned = re.sub(r'\(?\s*HS\s*(?:code)?\s*[:\s]*\d+\s*\)?', '', cleaned, flags=re.IGNORECASE)

    # Remove SKU patterns from title if present (e.g., ... R0530, TAG123)
    cleaned = re.sub(r'\s+[R|TAG]\d+[a-zA-Z]*$', '', cleaned)

    # Remove multiple spaces and normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned


def validate_alt_text(alt_text, max_length=512, target_length=125):
    """
    Validate and optionally truncate alt text to meet best practices.

    Args:
        alt_text: Alt text string to validate
        max_length: Hard maximum length (Shopify allows ~512)
        target_length: Recommended target length for SEO

    Returns:
        Tuple of (validated_alt_text, warning_message)
    """
    if not alt_text:
        return "", "Alt text is empty"

    # Remove redundant phrases like "image of", "picture of"
    redundant_phrases = [
        r'^image of\s+',
        r'^picture of\s+',
        r'^photo of\s+',
        r'^screenshot of\s+'
    ]
    for pattern in redundant_phrases:
        alt_text = re.sub(pattern, '', alt_text, flags=re.IGNORECASE)

    alt_text = alt_text.strip()

    warning = None
    if len(alt_text) > max_length:
        alt_text = alt_text[:max_length].rsplit(' ', 1)[0] + '...'
        warning = f"Alt text truncated to {max_length} characters"
    elif len(alt_text) > target_length:
        warning = f"Alt text is {len(alt_text)} chars (target: {target_length})"

    return alt_text, warning


def setup_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode (without GUI)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Fix for newer Chrome versions and WebDriverManager
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Use ChromeDriverManager to automatically manage the driver executable
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60) # Set a 60-second timeout for page loads
    return driver


def save_progress(current_product_index, filename="progress.json"):
    with open(filename, 'w') as f:
        json.dump({"last_scraped_index": current_product_index}, f)


def load_progress(filename="progress.json"):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get("last_scraped_index", -1)
    return -1

def download_image(image_url, save_path, session):
    try:
        response = session.get(image_url, stream=True, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors

        # Infer file extension from Content-Type header if possible
        content_type = response.headers.get('Content-Type')
        extension = mimetypes.guess_extension(content_type) if content_type else '.jpg'
        if not extension:
            extension = os.path.splitext(urlparse(image_url).path)[1] or '.jpg'
        
        # Ensure the extension starts with a dot
        if not extension.startswith('.'):
            extension = '.' + extension

        final_save_path = f"{save_path}{extension}"

        with open(final_save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        logging.info(f"Downloaded: {image_url} to {final_save_path}")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {image_url}: {e}")
        return False


def scrape_product_images(driver, product_name, sku, output_dir, session):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

    search_url = f"{BASE_URL}/search?q={sku}"
    logging.info(f"Navigating to search URL: {search_url}")
    
    product_output_dir = os.path.join(output_dir, get_valid_filename(product_name))
    os.makedirs(product_output_dir, exist_ok=True)

    try:
        driver.get(search_url)
        
        # Wait for search results to load. Adjust locator if needed.
        # This assumes search results have a link to the product page.
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-card a"))
        )
        
        # Click on the first product card link found
        product_link_element = driver.find_element(By.CSS_SELECTOR, "div.product-card a")
        product_page_url = product_link_element.get_attribute('href')
        logging.info(f"Found product link for {product_name}: {product_page_url}")
        
        driver.get(product_page_url)
        
        # Wait for the main product image or image container to be present
        # This selector might need adjustment based on your Shopify theme
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product__media-gallery img"))
        )
        
        # Find all image elements. This selector is common, but may vary.
        # Look for img tags within a common parent for product images.
        image_elements = driver.find_elements(By.CSS_SELECTOR, "div.product__media-gallery img")
        
        if not image_elements:
            logging.warning(f"No image elements found for {product_name} using primary selector. Trying fallback.")
            # Fallback selector: common for main product image on many themes
            image_elements = driver.find_elements(By.CSS_SELECTOR, "img.product-featured-media__img")

        if not image_elements:
            logging.warning(f"No image elements found for {product_name} after fallback. Skipping.")
            return False
            
        downloaded_count = 0
        for i, img_element in enumerate(image_elements):
            src = img_element.get_attribute('src')
            srcset = img_element.get_attribute('srcset')
            
            image_url = src
            if srcset: # Prefer higher resolution image from srcset if available
                # Simple approach: take the last URL in srcset (usually highest res)
                srcset_urls = srcset.split(',')
                if srcset_urls:
                    # Extract URL, remove 'w' descriptor if present
                    image_url = srcset_urls[-1].strip().split(' ')[0]
            
            if image_url:
                # Construct a descriptive filename
                filename = f"{get_valid_filename(product_name)}_{sku}_{i+1}"
                save_path = os.path.join(product_output_dir, filename)
                if download_image(image_url, save_path, session):
                    downloaded_count += 1
            else:
                logging.warning(f"Could not get image URL for an element of {product_name}")
                
        logging.info(f"Successfully scraped {downloaded_count} images for {product_name} (SKU: {sku})")
        return True

    except TimeoutException:
        logging.error(f"Timeout while loading search results or product page for SKU: {sku}")
    except NoSuchElementException as e:
        logging.error(f"Could not find expected element for SKU: {sku}. Error: {e}")
    except WebDriverException as e:
        logging.error(f"WebDriver error for SKU: {sku}. Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred for SKU: {sku}. Error: {e}")
    return False


# --- Additional Configuration for app.py compatibility --- #
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")
API_VERSION = os.getenv("API_VERSION", "2024-01")
SHOP_DOMAIN = os.getenv("SHOP_DOMAIN")
TOKEN_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/oauth/access_token" if SHOP_DOMAIN else None
GRAPHQL_ENDPOINT = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json" if SHOP_DOMAIN else None

DEFAULT_COUNTRY_OF_ORIGIN = os.getenv("DEFAULT_COUNTRY_OF_ORIGIN", "SI")

# Basic HS code mapping
HS_CODE_MAP = {
    "paper": "4823.90",
    "paint": "3210.00",
    "brush": "9603.30",
    "canvas": "5210.11",
    "default": "9999.00"
}


def load_processed_skus(proof_file=None):
    """Load SKUs that have already been successfully processed from push_proof.csv."""
    if proof_file is None:
        proof_file = PUSH_PROOF_CSV
    processed = set()
    if os.path.exists(proof_file):
        try:
            df = pd.read_csv(proof_file)
            success_rows = df[df["Status"] == "Success"]
            processed = set(success_rows["SKU"].astype(str).tolist())
            print(f"Loaded {len(processed)} already-processed SKUs from {proof_file}")
        except Exception as e:
            print(f"Warning: Could not load {proof_file}: {e}")
    return processed


def clean_sku(sku):
    """Remove 'AC' suffix from SKU."""
    if isinstance(sku, str):
        return sku.replace("AC", "").strip()
    return str(sku).strip()


def get_hs_code(product_title):
    """Determine HS code based on product title/category."""
    if not product_title:
        return HS_CODE_MAP["default"]

    title_lower = product_title.lower()

    for keyword, hs_code in HS_CODE_MAP.items():
        if keyword != "default" and keyword in title_lower:
            return hs_code

    return HS_CODE_MAP["default"]


def scrape_product_info(sku, vendor):
    """
    Stub scraper function for app.py compatibility.
    Returns basic product info structure.

    Note: Full scraping logic should be implemented based on vendor requirements.
    """
    return {
        "image_url": None,
        "scraped_sku": None,
        "price": None,
        "title": f"Product {sku}",
        "country": DEFAULT_COUNTRY_OF_ORIGIN,
        "hs_code": None
    }


# --- Shopify Client Class --- #
class ShopifyClient:
    """
    Shopify GraphQL API client for product and media management.
    Supports both OAuth and client credentials authentication.
    """

    def __init__(self):
        self.access_token = None
        self.shop_domain = SHOP_DOMAIN
        self.api_version = API_VERSION
        self.graphql_endpoint = None

    def authenticate(self):
        """Exchange Client ID/Secret for an access_token."""
        if not TOKEN_ENDPOINT:
            raise Exception("SHOP_DOMAIN not configured")

        payload = {
            "client_id": SHOPIFY_CLIENT_ID,
            "client_secret": SHOPIFY_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        try:
            response = requests.post(TOKEN_ENDPOINT, json=payload)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            print(f"Successfully authenticated with Shopify.")
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}")
            raise

    def execute_graphql(self, query, variables=None):
        """Execute a GraphQL query/mutation."""
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        if self.graphql_endpoint:
            endpoint = self.graphql_endpoint
        elif self.shop_domain:
            endpoint = f"https://{self.shop_domain}/admin/api/{API_VERSION}/graphql.json"
        else:
            endpoint = GRAPHQL_ENDPOINT

        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }

        response = requests.post(endpoint, json={"query": query, "variables": variables}, headers=headers)
        response.raise_for_status()
        result = response.json()

        if "errors" in result:
            print(f"GraphQL Errors: {result['errors']}")
            return None
        return result

    def get_product_by_sku(self, sku):
        """Fetch product ID, first Variant ID, and Current Barcode by SKU."""
        query = """
        query getProductBySku($query: String!) {
          products(first: 1, query: $query) {
            edges {
              node {
                id
                handle
                variants(first: 1) {
                  edges {
                    node {
                      id
                      sku
                      barcode
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"query": f"sku:{sku}"}
        result = self.execute_graphql(query, variables)

        if result and result.get("data", {}).get("products", {}).get("edges"):
            prod = result["data"]["products"]["edges"][0]["node"]
            prod_id = prod["id"]
            variant_id = None
            current_barcode = None
            if prod["variants"]["edges"]:
                variant_node = prod["variants"]["edges"][0]["node"]
                variant_id = variant_node["id"]
                current_barcode = variant_node.get("barcode")
            return prod_id, variant_id, current_barcode
        return None, None, None

    def check_product_has_image(self, product_id):
        """Check if product already has images and return their IDs."""
        query = """
        query getProduct($id: ID!) {
          product(id: $id) {
            id
            media(first: 10) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"id": product_id}
        result = self.execute_graphql(query, variables)

        media_ids = []
        if result and result.get("data", {}).get("product", {}).get("media", {}).get("edges"):
            for edge in result["data"]["product"]["media"]["edges"]:
                media_ids.append(edge["node"]["id"])

        return media_ids

    def get_product_media(self, product_id, first=50):
        """Fetch product media IDs and URLs."""
        query = """
        query getProductMedia($id: ID!, $first: Int!) {
          product(id: $id) {
            id
            media(first: $first) {
              edges {
                node {
                  ... on MediaImage {
                    id
                    image {
                      url
                    }
                  }
                }
              }
            }
          }
        }
        """
        variables = {"id": product_id, "first": int(first)}
        result = self.execute_graphql(query, variables)

        media = []
        edges = result and result.get("data", {}).get("product", {}).get("media", {}).get("edges") or []
        for edge in edges:
            node = edge.get("node") or {}
            image = node.get("image") or {}
            url = image.get("url")
            if url:
                media.append({"id": node.get("id"), "url": url})

        return media

    def delete_product_media(self, product_id, media_ids):
        """Delete media from product."""
        mutation = """
        mutation productDeleteMedia($productId: ID!, $mediaIds: [ID!]!) {
          productDeleteMedia(productId: $productId, mediaIds: $mediaIds) {
            deletedMediaIds
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "mediaIds": media_ids
        }
        result = self.execute_graphql(mutation, variables)
        return result

    def update_product_media(self, product_id, image_url, alt_text=None, filename=None):
        """
        Upload image to product's media gallery with alt text.
        Returns response including media ID for subsequent renaming.
        """
        mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
          productCreateMedia(productId: $productId, media: $media) {
            media {
              id
              alt
              ... on MediaImage {
                id
                image {
                  url
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        media_input = {
            "originalSource": image_url,
            "mediaContentType": "IMAGE"
        }

        if alt_text:
            # Clean and validate alt text before uploading
            cleaned_alt = clean_product_name(alt_text) or alt_text
            validated_alt, warning = validate_alt_text(cleaned_alt)
            media_input["alt"] = validated_alt
            if warning:
                print(f"  Alt text validation: {warning}")

        variables = {
            "productId": product_id,
            "media": [media_input]
        }
        result = self.execute_graphql(mutation, variables)

        # If filename is provided and upload succeeded, rename the media
        if result and filename and not result.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
            media_list = result.get("data", {}).get("productCreateMedia", {}).get("media", [])
            if media_list and len(media_list) > 0:
                media_id = media_list[0].get("id")
                if media_id:
                    try:
                        rename_result = self.rename_media_files([{
                            "id": media_id,
                            "filename": filename
                        }])
                        if rename_result and not rename_result.get("data", {}).get("fileUpdate", {}).get("userErrors"):
                            print(f"  Image renamed to: {filename}")
                    except Exception as e:
                        print(f"  Warning: Could not rename image: {e}")

        return result

    def rename_media_files(self, media_updates):
        """
        Rename uploaded media files using Shopify's fileUpdate mutation.

        Args:
            media_updates: List of dicts with 'id' and 'filename' keys
                          Example: [{"id": "gid://shopify/MediaImage/123", "filename": "product-name.jpg"}]

        Returns:
            GraphQL response with updated file info

        Note:
            - Maximum 25 files can be updated per mutation
            - Filename extension must match the original file type
            - This is called AFTER productCreateMedia to rename images for SEO
        """
        mutation = """
        mutation fileUpdate($files: [FileUpdateInput!]!) {
          fileUpdate(files: $files) {
            files {
              id
              alt
              ... on MediaImage {
                id
                image {
                  url
                }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        # Process in batches of 25 (Shopify's limit)
        batch_size = 25
        all_results = []

        for i in range(0, len(media_updates), batch_size):
            batch = media_updates[i:i + batch_size]
            result = self.execute_graphql(mutation, {"files": batch})
            all_results.append(result)

        return all_results if len(all_results) > 1 else all_results[0]

    def update_product_variants(self, product_id, variant_updates):
        """
        Update variants using productVariantsBulkUpdate.
        variant_updates: list of dicts with 'id' and fields to update (e.g. 'barcode', 'price').
        """
        mutation = """
        mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
          productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            product {
              id
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "variants": variant_updates
        }
        result = self.execute_graphql(mutation, variables)
        return result

    def create_product(self, title, vendor, sku, barcode=None, price=None,
                       weight=None, country=None, hs_code=None, category=None):
        """
        Create a new product in Shopify as DRAFT with all metadata.

        Args:
            title: Product title
            vendor: Vendor name
            sku: Stock keeping unit
            barcode: EAN/barcode (optional)
            price: Product price (optional)
            weight: Weight in grams (optional)
            country: 2-letter country code (optional)
            hs_code: Harmonized system code (optional)
            category: Product type/category (optional)

        Returns:
            Tuple of (product_id, variant_id, inventory_item_id) or (None, None, None) on error
        """
        # Step 1: Create product (without variants in input - API 2024-01+)
        mutation = """
        mutation createProduct($input: ProductInput!) {
          productCreate(input: $input) {
            product {
              id
              handle
              variants(first: 1) {
                edges {
                  node {
                    id
                    sku
                    inventoryItem { id }
                  }
                }
              }
            }
            userErrors { field message }
          }
        }
        """

        # Build product input (no variants field)
        product_input = {
            "title": title,
            "vendor": vendor,
            "status": "DRAFT"  # Create as draft first
        }

        if category:
            product_input["productType"] = category

        variables = {"input": product_input}
        result = self.execute_graphql(mutation, variables)

        if not result or not result.get("data", {}).get("productCreate"):
            return None, None, None

        product_create = result["data"]["productCreate"]

        # Check for errors
        if product_create.get("userErrors"):
            print(f"  Product creation errors: {product_create['userErrors']}")
            return None, None, None

        # Extract IDs
        product = product_create.get("product", {})
        product_id = product.get("id")

        variant_edges = product.get("variants", {}).get("edges", [])
        if not variant_edges:
            return None, None, None

        variant_node = variant_edges[0]["node"]
        variant_id = variant_node.get("id")
        inventory_item_id = variant_node.get("inventoryItem", {}).get("id")

        # Extract numeric IDs for REST API
        variant_num_id = variant_id.split('/')[-1]
        inventory_num_id = inventory_item_id.split('/')[-1]

        # Step 2: Update variant via REST API (GraphQL mutations not available in API 2024-01)
        import requests

        rest_headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }

        # Update variant (SKU, barcode, price, weight)
        if sku or barcode or price or weight:
            variant_url = f"https://{self.shop_domain}/admin/api/{self.api_version}/variants/{variant_num_id}.json"
            variant_data = {"variant": {}}

            if sku:
                variant_data["variant"]["sku"] = str(sku)
            if barcode:
                variant_data["variant"]["barcode"] = str(barcode)
            if price:
                variant_data["variant"]["price"] = str(price)
            if weight is not None:
                variant_data["variant"]["weight"] = float(weight)
                variant_data["variant"]["weight_unit"] = "g"

            try:
                resp = requests.put(variant_url, json=variant_data, headers=rest_headers, timeout=10)
                resp.raise_for_status()
            except Exception as e:
                print(f"  Warning: Variant update via REST failed: {e}")

        # Step 3: Update inventory item via REST API (country, HS code)
        if country or hs_code:
            inv_url = f"https://{self.shop_domain}/admin/api/{self.api_version}/inventory_items/{inventory_num_id}.json"
            inv_data = {"inventory_item": {}}

            if country:
                inv_data["inventory_item"]["country_code_of_origin"] = country
            if hs_code:
                inv_data["inventory_item"]["harmonized_system_code"] = str(hs_code)

            try:
                resp = requests.put(inv_url, json=inv_data, headers=rest_headers, timeout=10)
                resp.raise_for_status()
            except Exception as e:
                print(f"  Warning: Inventory item update via REST failed: {e}")

        return product_id, variant_id, inventory_item_id

    def get_default_location(self):
        """
        Get the default/primary location for inventory management.

        Returns:
            Location ID (gid://shopify/Location/...) or None
        """
        query = """
        query getDefaultLocation {
          locations(first: 1, query: "active:true") {
            edges {
              node { id }
            }
          }
        }
        """
        result = self.execute_graphql(query)

        if result and result.get("data", {}).get("locations", {}).get("edges"):
            location_edges = result["data"]["locations"]["edges"]
            if location_edges:
                return location_edges[0]["node"]["id"]

        return None

    def set_inventory_level(self, inventory_item_id, location_id, quantity):
        """
        Set inventory quantity for a product variant.

        CRITICAL: Only call for newly created products!

        Args:
            inventory_item_id: Inventory item ID (gid://shopify/InventoryItem/...)
            location_id: Location ID (gid://shopify/Location/...)
            quantity: Integer quantity to set

        Returns:
            True if successful, False otherwise
        """
        mutation = """
        mutation setInitialInventory($inventoryItemId: ID!, $locationId: ID!, $quantity: Int!) {
          inventorySetQuantities(
            input: {
              reason: "correction"
              name: "available"
              ignoreCompareQuantity: true
              quantities: [{
                inventoryItemId: $inventoryItemId
                locationId: $locationId
                quantity: $quantity
              }]
            }
          ) {
            inventoryAdjustmentGroup { createdAt reason }
            userErrors { field message }
          }
        }
        """
        variables = {
            "inventoryItemId": inventory_item_id,
            "locationId": location_id,
            "quantity": int(quantity)
        }
        result = self.execute_graphql(mutation, variables)

        if result and result.get("data", {}).get("inventorySetQuantities"):
            inv_set = result["data"]["inventorySetQuantities"]
            if inv_set.get("userErrors"):
                print(f"  Inventory set errors: {inv_set['userErrors']}")
                return False
            return True

        return False

    def activate_product(self, product_id):
        """
        Update product status from DRAFT to ACTIVE after all data is populated.

        Args:
            product_id: Product ID (gid://shopify/Product/...)

        Returns:
            True if successful, False otherwise
        """
        mutation = """
        mutation activateProduct($input: ProductInput!) {
          productUpdate(input: $input) {
            product { id status }
            userErrors { field message }
          }
        }
        """
        variables = {
            "input": {
                "id": product_id,
                "status": "ACTIVE"
            }
        }
        result = self.execute_graphql(mutation, variables)

        if result and result.get("data", {}).get("productUpdate"):
            product_update = result["data"]["productUpdate"]
            if product_update.get("userErrors"):
                print(f"  Product activation errors: {product_update['userErrors']}")
                return False
            return True

        return False


def main(resume=False):
    if not BASE_URL:
        logging.error("SHOPIFY_STORE_URL is not set in the .env file. Please configure it.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = None
    session = requests.Session()
    
    start_index = 0
    if resume:
        start_index = load_progress() + 1
        logging.info(f"Resuming scraping from index: {start_index}")
        
    if start_index >= len(products_to_scrape):
        logging.info("All products have already been scraped or resume index is out of bounds.")
        return

    try:
        driver = setup_driver()
        for i in range(start_index, len(products_to_scrape)):
            product_name, sku = products_to_scrape[i]
            logging.info(f"--- Starting to scrape images for {product_name} (SKU: {sku}) ---")
            if scrape_product_images(driver, product_name, sku, OUTPUT_DIR, session):
                save_progress(i) # Save progress after each successful product scrape
            else:
                logging.error(f"Failed to scrape images for {product_name} (SKU: {sku}). Script will continue to next product.")
            time.sleep(2) # Be kind to the server

    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
    finally:
        if driver:
            driver.quit()
        logging.info("Scraping complete or stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopify Image Scraper")
    parser.add_argument('--resume', action='store_true', help='Resume from the last saved progress point.')
    args = parser.parse_args()

    main(resume=args.resume)
