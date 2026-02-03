import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
resolver = ShopifyResolver()
print("Successfully authenticated with Shopify.\n")

print("Setting inventory levels...\n")

for sku, quantity in inventory_updates.items():
    print(f"--- Processing {sku} (target qty: {quantity}) ---")

    # Find product by SKU
    identifier = {"kind": "sku", "value": sku}
    result = resolver.resolve_identifier(identifier)
    matches = result.get("matches", [])

    if not matches:
        print(f"  [ERROR] Product not found")
        continue

    product = matches[0]
    variant = product.get("primary_variant", {})
    inventory_item_id = variant.get("inventory_item_id")

    if not inventory_item_id:
        print(f"  [ERROR] No inventory item ID found")
        continue

    print(f"  Product: {product.get('title')}")
    print(f"  Variant ID: {variant.get('id')}")
    print(f"  Inventory Item ID: {inventory_item_id}")

    # Get inventory levels
    query_inventory = """
    query GetInventoryLevels($inventoryItemId: ID!) {
      inventoryItem(id: $inventoryItemId) {
        id
        inventoryLevels(first: 10) {
          edges {
            node {
              id
              location {
                id
                name
              }
              quantities(names: ["available"]) {
                name
                quantity
              }
            }
          }
        }
      }
    }
    """

    inv_result = resolver.client.execute_graphql(query_inventory, {
        "inventoryItemId": inventory_item_id
    })

    if not inv_result or not inv_result.get("data"):
        print(f"  [ERROR] Could not fetch inventory levels")
        continue

    inventory_item = inv_result["data"].get("inventoryItem", {})
    levels = inventory_item.get("inventoryLevels", {}).get("edges", [])

    if not levels:
        print(f"  [ERROR] No inventory locations found")
        continue

    # Use first location
    location = levels[0]["node"]
    location_id = location["location"]["id"]
    location_name = location["location"]["name"]
    quantities = location.get("quantities", [])
    current_available = next((q["quantity"] for q in quantities if q["name"] == "available"), 0)

    print(f"  Location: {location_name} ({location_id})")
    print(f"  Current inventory: {current_available}")
    print(f"  Setting to: {quantity}")

    # Set inventory level
    mutation = """
    mutation SetInventoryLevel($inventoryItemId: ID!, $locationId: ID!, $available: Int!) {
      inventorySetQuantities(
        input: {
          reason: "correction"
          name: "available"
          quantities: [
            {
              inventoryItemId: $inventoryItemId
              locationId: $locationId
              quantity: $available
            }
          ]
        }
      ) {
        inventoryAdjustmentGroup {
          reason
          changes {
            name
            delta
            quantityAfterChange
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    set_result = resolver.client.execute_graphql(mutation, {
        "inventoryItemId": inventory_item_id,
        "locationId": location_id,
        "available": quantity
    })

    if set_result and set_result.get("data"):
        user_errors = set_result["data"]["inventorySetQuantities"]["userErrors"]
        if user_errors:
            print(f"  [ERROR] {user_errors}")
        else:
            changes = set_result["data"]["inventorySetQuantities"]["inventoryAdjustmentGroup"]["changes"]
            if changes:
                new_qty = changes[0]["quantityAfterChange"]
                delta = changes[0]["delta"]
                print(f"  [SUCCESS] Inventory updated: {current_available} -> {new_qty} (delta: {delta})")
            else:
                print(f"  [SUCCESS] Inventory level set to {quantity}")
    else:
        print(f"  [ERROR] Failed to set inventory")

    print()

print("\n" + "="*70)
print("Inventory update complete!")
print("="*70)
