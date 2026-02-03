"""
Test script for product creation feature.
This script tests the new ShopifyClient methods.

IMPORTANT: This is for TESTING ONLY. Use with caution in production.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.image_scraper import ShopifyClient

load_dotenv()

def test_client_initialization():
    """Test 1: Initialize ShopifyClient"""
    print("\n=== Test 1: Client Initialization ===")
    try:
        client = ShopifyClient()
        client.authenticate()
        print("✅ Client initialized and authenticated")
        return client
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

def test_get_default_location(client):
    """Test 2: Get default location"""
    print("\n=== Test 2: Get Default Location ===")
    try:
        location_id = client.get_default_location()
        if location_id:
            print(f"✅ Default location: {location_id}")
            return location_id
        else:
            print("❌ No default location found")
            return None
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

def test_product_exists(client, sku):
    """Test 3: Check if product exists"""
    print(f"\n=== Test 3: Check Product Exists (SKU: {sku}) ===")
    try:
        product_id, variant_id, barcode = client.get_product_by_sku(sku)
        if product_id:
            print(f"✅ Product exists:")
            print(f"   Product ID: {product_id}")
            print(f"   Variant ID: {variant_id}")
            print(f"   Barcode: {barcode}")
            return True
        else:
            print(f"ℹ️  Product does not exist (ready for creation)")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None

def test_create_product(client):
    """Test 4: Create a test product"""
    print("\n=== Test 4: Create Test Product ===")
    print("⚠️  This will create a REAL product in Shopify!")
    print("    Product will be created as DRAFT first.")

    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Skipped")
        return None, None, None

    try:
        # Create test product
        test_sku = f"TEST-{os.urandom(4).hex().upper()}"
        print(f"Creating product with SKU: {test_sku}")

        product_id, variant_id, inventory_item_id = client.create_product(
            title=f"Test Product {test_sku}",
            vendor="Test Vendor",
            sku=test_sku,
            barcode="1234567890123",
            price=19.99,
            weight=500,
            country="SI",
            hs_code="9999.00",
            category="Test Category"
        )

        if product_id:
            print(f"✅ Product created:")
            print(f"   Product ID: {product_id}")
            print(f"   Variant ID: {variant_id}")
            print(f"   Inventory Item ID: {inventory_item_id}")
            print(f"   Status: DRAFT (not yet active)")
            return product_id, variant_id, inventory_item_id
        else:
            print("❌ Product creation failed")
            return None, None, None
    except Exception as e:
        print(f"❌ Failed: {e}")
        return None, None, None

def test_set_inventory(client, inventory_item_id, location_id):
    """Test 5: Set inventory level"""
    print("\n=== Test 5: Set Inventory Level ===")
    if not inventory_item_id or not location_id:
        print("⚠️  Skipped (missing inventory item or location)")
        return False

    try:
        print(f"Setting inventory to 0 units...")
        success = client.set_inventory_level(inventory_item_id, location_id, 0)
        if success:
            print("✅ Inventory set successfully")
            return True
        else:
            print("❌ Inventory set failed")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def test_activate_product(client, product_id):
    """Test 6: Activate product"""
    print("\n=== Test 6: Activate Product ===")
    if not product_id:
        print("⚠️  Skipped (no product ID)")
        return False

    try:
        print(f"Activating product...")
        success = client.activate_product(product_id)
        if success:
            print("✅ Product activated (status: ACTIVE)")
            return True
        else:
            print("❌ Activation failed")
            return False
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def cleanup_test_product(client, product_id):
    """Optional: Delete test product"""
    print("\n=== Cleanup: Delete Test Product ===")
    if not product_id:
        print("⚠️  No product to delete")
        return

    response = input(f"Delete test product {product_id}? (yes/no): ")
    if response.lower() != 'yes':
        print("Test product kept in Shopify (you can delete it manually)")
        return

    try:
        mutation = """
        mutation deleteProduct($input: ProductDeleteInput!) {
          productDelete(input: $input) {
            deletedProductId
            userErrors { field message }
          }
        }
        """
        variables = {"input": {"id": product_id}}
        result = client.execute_graphql(mutation, variables)

        if result and result.get("data", {}).get("productDelete"):
            product_delete = result["data"]["productDelete"]
            if product_delete.get("userErrors"):
                print(f"❌ Deletion failed: {product_delete['userErrors']}")
            else:
                print("✅ Test product deleted")
        else:
            print("❌ Deletion failed")
    except Exception as e:
        print(f"❌ Failed: {e}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("PRODUCT CREATION FEATURE - TEST SUITE")
    print("=" * 60)
    print("\nThis script will test the new product creation methods.")
    print("Some tests will create REAL products in Shopify.")
    print("\nMake sure you're connected to the correct Shopify store!")

    # Initialize client
    client = test_client_initialization()
    if not client:
        print("\n❌ Cannot continue without authenticated client")
        return

    # Get default location
    location_id = test_get_default_location(client)

    # Test with a known SKU (update this to test with your own SKU)
    print("\n" + "=" * 60)
    print("EXISTING PRODUCT TEST")
    print("=" * 60)
    test_sku = input("Enter a SKU to test (or press Enter to skip): ").strip()
    if test_sku:
        test_product_exists(client, test_sku)

    # Create new product
    print("\n" + "=" * 60)
    print("NEW PRODUCT CREATION TEST")
    print("=" * 60)
    product_id, variant_id, inventory_item_id = test_create_product(client)

    # Set inventory
    if product_id and inventory_item_id and location_id:
        test_set_inventory(client, inventory_item_id, location_id)

        # Activate product
        test_activate_product(client, product_id)

        # Cleanup
        cleanup_test_product(client, product_id)

    print("\n" + "=" * 60)
    print("TESTS COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the results above")
    print("2. Check your Shopify admin for created products")
    print("3. Run the safety audit: sqlite3 data/scraper.db < safety_audit.sql")
    print("4. Test with a real CSV file via the Flask app")

if __name__ == "__main__":
    main()
