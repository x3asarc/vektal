"""
Assign product to appropriate collections based on product data.

Usage:
    python utils/assign_collections.py --sku "ABC123"
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo.seo_generator import ShopifyClient


def assign_collections(sku):
    """Assign product to collections."""
    print(f"Assigning collections for: {sku}")

    shopify = ShopifyClient()
    if not shopify.authenticate():
        return False

    # Fetch product
    query = """
    query GetProduct($query: String!) {
      products(first: 1, query: $query) {
        edges {
          node {
            id
            title
            vendor
            productType
            tags
            collections(first: 10) {
              edges {
                node {
                  id
                  title
                }
              }
            }
          }
        }
      }
    }
    """

    result = shopify.execute_graphql(query, {"query": f"sku:{sku}"})
    if not result or not result["data"]["products"]["edges"]:
        print("[ERROR] Product not found")
        return False

    node = result["data"]["products"]["edges"][0]["node"]
    current_collections = [c["node"] for c in node.get("collections", {}).get("edges", [])]

    print(f"   Product: {node['title']}")
    print(f"   Current collections: {len(current_collections)}")

    if current_collections:
        print(f"   Collections: {', '.join([c['title'] for c in current_collections])}")
        print("   [OK] Product already has collections")
        return True

    # TODO: Implement smart collection assignment logic
    # For now, just assign to a default "All Products" collection if it exists

    # Fetch available collections
    collections_query = """
    query GetCollections {
      collections(first: 50) {
        edges {
          node {
            id
            title
            handle
          }
        }
      }
    }
    """

    collections_result = shopify.execute_graphql(collections_query)
    if not collections_result:
        print("   [WARNING] Could not fetch collections")
        return False

    all_collections = [c["node"] for c in collections_result["data"]["collections"]["edges"]]

    # Simple matching logic
    vendor = node.get("vendor", "").lower()
    product_type = node.get("productType", "").lower()
    tags = [t.lower() for t in node.get("tags", [])]

    matched_collections = []

    for collection in all_collections:
        handle = collection["handle"].lower()
        title = collection["title"].lower()

        # Match by vendor
        if vendor and vendor in handle:
            matched_collections.append(collection["id"])

        # Match by product type
        elif product_type and product_type in handle:
            matched_collections.append(collection["id"])

        # Match by tags
        elif any(tag in handle or tag in title for tag in tags):
            matched_collections.append(collection["id"])

    if not matched_collections:
        print("   [WARNING] No matching collections found")
        print("   [TIP] Create collections or update collection rules")
        return False

    print(f"   Matched {len(matched_collections)} collection(s)")

    # Update product (add to collections)
    # Note: This requires the collectionsToJoin field
    mutation = """
    mutation UpdateProduct($id: ID!, $collections: [ID!]!) {
      productUpdate(input: {id: $id, collectionsToJoin: $collections}) {
        product {
          id
          collections(first: 10) {
            edges {
              node {
                title
              }
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

    variables = {
        "id": node["id"],
        "collections": matched_collections[:3]  # Limit to 3 collections
    }

    result = shopify.execute_graphql(mutation, variables)
    if result and "data" in result:
        errors = result["data"]["productUpdate"].get("userErrors", [])
        if errors:
            print(f"   [ERROR] {errors}")
            return False
        print(f"   [OK] Added to {len(matched_collections[:3])} collection(s)")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Assign product to collections")
    parser.add_argument("--sku", required=True, help="Product SKU")
    args = parser.parse_args()

    success = assign_collections(args.sku)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
