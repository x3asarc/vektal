"""
Quick script to add specific Pentart products with inventory levels
"""
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import (
    scrape_product_info, ShopifyClient, clean_sku,
    DEFAULT_COUNTRY_OF_ORIGIN, get_hs_code
)
from utils.pentart_db import PentartDatabase
from src.core.paths import DB_PATH

# Load environment
load_dotenv()

# Products to add: (SKU, inventory_quantity)
PRODUCTS = [
    ("5997412709667", 6),
    ("5997412742664", 5),
    ("5997412761139", 5),
    ("5996546033389", 1),
]

def main():
    """Create Pentart products with specified inventory levels."""

    # Initialize Shopify client
    shopify = ShopifyClient()
    shopify.authenticate()

    # Get default location for inventory
    default_location_id = shopify.get_default_location()
    if not default_location_id:
        print("ERROR: Could not get default location ID")
        return

    print(f"Default location ID: {default_location_id}")
    print("=" * 60)

    # Initialize Pentart database
    pentart_db = None
    try:
        pentart_db = PentartDatabase(DB_PATH)
        print("Pentart database initialized\n")
    except Exception as e:
        print(f"Warning: Could not initialize Pentart database: {e}\n")

    vendor = "Pentart"

    for raw_sku, inventory_qty in PRODUCTS:
        print(f"\nProcessing: {raw_sku} (Inventory: {inventory_qty})")
        print("-" * 60)

        try:
            # Clean SKU
            clean = clean_sku(raw_sku)

            # Check if product already exists
            existing_product_id, existing_variant_id, current_barcode = shopify.get_product_by_sku(raw_sku)

            if existing_product_id:
                print(f"[WARN]  Product already exists (ID: {existing_product_id})")
                print(f"   Variant ID: {existing_variant_id}")

                # Ask if we should update inventory anyway
                response = input("   Update inventory level? (y/n): ").strip().lower()
                if response == 'y' and existing_variant_id:
                    # Get inventory item ID from variant
                    variant_query = f"""
                    query {{
                      productVariant(id: "{existing_variant_id}") {{
                        inventoryItem {{
                          id
                        }}
                      }}
                    }}
                    """
                    result = shopify.execute_graphql(variant_query)
                    inventory_item_id = result.get("data", {}).get("productVariant", {}).get("inventoryItem", {}).get("id")

                    if inventory_item_id and shopify.set_inventory_level(inventory_item_id, default_location_id, inventory_qty):
                        print(f"[OK] Inventory updated to {inventory_qty} units")
                    else:
                        print("[ERROR] Failed to update inventory")
                continue

            # Try database lookup first for Pentart products
            scrape_data = None
            db_hit = False

            if pentart_db:
                try:
                    # Try lookup by EAN barcode first (since raw_sku is often a barcode)
                    db_product = pentart_db.get_by_ean(raw_sku)

                    # If not found by EAN, try by article number
                    if not db_product:
                        db_product = pentart_db.get_by_article_number(clean)

                    if db_product:
                        print(f"[OK] Found in Pentart database: {db_product.get('description')}")
                        print(f"  Article Number: {db_product.get('article_number')}")
                        print(f"  EAN: {db_product.get('ean')}")
                        print(f"  Weight: {db_product.get('product_weight')}g")
                        db_hit = True
                        scrape_data = {
                            "image_url": None,
                            "scraped_sku": db_product.get("ean"),
                            "price": None,
                            "title": db_product.get("description"),
                            "country": "HU",
                            "weight": db_product.get("product_weight")
                        }
                except Exception as e:
                    print(f"  Database lookup error: {e}")

            # Fallback to web scraping if not in database
            if not db_hit:
                print(f"  Scraping product info...")
                scrape_data = scrape_product_info(clean, vendor)

            # Extract data
            image_url = scrape_data.get("image_url")
            scraped_barcode = scrape_data.get("scraped_sku")
            scraped_price = scrape_data.get("price")
            product_title = scrape_data.get("title")
            hs_code = scrape_data.get("hs_code") or get_hs_code(product_title)
            product_weight = scrape_data.get("weight")

            if not (image_url or product_title):
                print(f"[ERROR] No product data found - skipping")
                continue

            print(f"  Title: {product_title}")
            if image_url:
                print(f"  Image: {image_url[:50]}...")
            if scraped_price:
                print(f"  Price: {scraped_price}")

            # Create product as DRAFT
            new_product_id, new_variant_id, inventory_item_id = shopify.create_product(
                title=product_title or f"Product {raw_sku}",
                vendor=vendor,
                sku=raw_sku,
                barcode=scraped_barcode,
                price=scraped_price,
                weight=product_weight,
                country=scrape_data.get("country", DEFAULT_COUNTRY_OF_ORIGIN),
                hs_code=hs_code,
                category=None
            )

            if not new_product_id:
                print(f"[ERROR] Failed to create product")
                continue

            print(f"[OK] Product created (ID: {new_product_id})")

            # Upload image if available
            if image_url:
                from src.core.image_scraper import clean_product_name
                alt_text = clean_product_name(product_title)
                res = shopify.update_product_media(new_product_id, image_url, alt_text)

                if res and not res.get("data", {}).get("productCreateMedia", {}).get("userErrors"):
                    print(f"[OK] Image uploaded")
                else:
                    print(f"[WARN]  Image upload warning")

            # Set inventory level
            if inventory_item_id and shopify.set_inventory_level(inventory_item_id, default_location_id, inventory_qty):
                print(f"[OK] Inventory set to {inventory_qty} units")
            else:
                print(f"[ERROR] Failed to set inventory")

            # Activate product
            if shopify.activate_product(new_product_id):
                print(f"[OK] Product activated")

            print(f"[OK] COMPLETED: {raw_sku}")

        except Exception as e:
            print(f"[ERROR] ERROR: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("All products processed!")

if __name__ == "__main__":
    main()
