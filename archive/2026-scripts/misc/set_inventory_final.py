import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import ShopifyClient
from src.core.shopify_resolver import ShopifyResolver

# SKU to quantity mapping
inventory_updates = {
    "grottesche-0026": 1,
    "views_0142-3": 8,
    "views-0238": 8,
    "views-0154": 3,
    "views-0111": 3,
    "tiles_0040-3": 8,
    "time_0028": 8,
}

print("Initializing Shopify connection...")
client = ShopifyClient()
client.authenticate()
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

# Get default location
location_id = client.get_default_location()
if not location_id:
    print("[ERROR] Could not get default location")
    sys.exit(1)

print(f"Using location: {location_id}\n")

print("Setting inventory levels...\n")

for sku, quantity in inventory_updates.items():
    print(f"--- Processing {sku} (target qty: {quantity}) ---")

    # Find product by SKU
    identifier = {"kind": "sku", "value": sku}
    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    if not matches:
        print(f"  [ERROR] Product not found\n")
        continue

    product = matches[0]
    variant = product.get("primary_variant", {})
    inventory_item_id = variant.get("inventory_item_id")

    if not inventory_item_id:
        print(f"  [ERROR] No inventory item ID found\n")
        continue

    print(f"  Product: {product.get('title')}")
    print(f"  Inventory Item ID: {inventory_item_id}")
    print(f"  Setting quantity to: {quantity}")

    # Set inventory
    success = client.set_inventory_level(inventory_item_id, location_id, quantity)

    if success:
        print(f"  [SUCCESS] Inventory set to {quantity}\n")
    else:
        print(f"  [ERROR] Failed to set inventory\n")

print("="*70)
print("Inventory update complete!")
print("="*70)
