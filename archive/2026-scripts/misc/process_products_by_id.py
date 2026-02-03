"""
Process products by their numeric IDs
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver
from src.core.pipeline import process_identifier, apply_payload_with_context
from cli.main import apply_cli_approvals, print_payload_summary

# Product IDs to process
PRODUCT_IDS = [
    "5996546033389",
    "5997412742664",
    "5997412709667",
]

def get_product_by_id(resolver, product_id):
    """Get product details by numeric ID"""
    gid = f"gid://shopify/Product/{product_id}"

    query = """
    query GetProduct($id: ID!) {
      product(id: $id) {
        id
        handle
        title
        vendor
      }
    }
    """

    try:
        result = resolver.client.execute_graphql(query, {"id": gid})
        print(f"GraphQL Result: {result}")

        if not result:
            print(f"No result returned from GraphQL")
            return None

        if "errors" in result:
            print(f"GraphQL returned errors: {result['errors']}")
            return None

        product = result.get("data", {}).get("product")
        if not product:
            print(f"No product data in result: {result}")
        return product
    except Exception as e:
        print(f"Exception fetching product {product_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("Initializing Shopify client...")
    resolver = ShopifyResolver()

    context = {
        "resolver": resolver,
        "shop_domain": resolver.shop_domain,
        "access_token": resolver.client.access_token,
        "api_version": resolver.api_version,
    }

    for product_id in PRODUCT_IDS:
        print(f"\n{'='*70}")
        print(f"Processing Product ID: {product_id}")
        print(f"{'='*70}")

        # Look up product by ID to get handle
        product_info = get_product_by_id(resolver, product_id)

        if not product_info:
            print(f"ERROR: Could not find product {product_id}")
            continue

        handle = product_info.get("handle")
        title = product_info.get("title")
        vendor = product_info.get("vendor")

        print(f"Found: {title}")
        print(f"Handle: {handle}")
        print(f"Vendor: {vendor}")

        # Process using handle
        identifier = {"kind": "handle", "value": handle}

        print("\nProcessing with pipeline...")
        payload = process_identifier(identifier, mode="cli", context=context)

        # Print summary
        print_payload_summary(payload)

        # Auto-approve all changes
        batch_state = {
            "image_all": True,
            "handle_all": True,
            "title_all": True,
            "hs_all": True,
            "seo_all": True,
        }
        payload = apply_cli_approvals(payload, batch_state=batch_state)

        # Apply changes
        print("\nApplying changes...")
        apply_result = apply_payload_with_context(payload, context=context)

        if apply_result:
            print(f"SUCCESS: Applied changes to {handle}")
        else:
            print(f"WARNING: No changes applied to {handle}")

    print(f"\n{'='*70}")
    print("All products processed!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
