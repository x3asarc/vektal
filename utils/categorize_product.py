"""
Categorize product by setting product_type based on title, description, and vendor.

Usage:
    python utils/categorize_product.py --sku "ABC123"
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo.seo_generator import ShopifyClient


# Common product categories in German
CATEGORIES = [
    "Farbe", "Papier", "Kleber", "Pinsel", "Stoff", "Holz",
    "Deko", "Bastelmaterial", "Servietten", "Wachs", "Lack",
    "Schablone", "Stempel", "Glitzer", "Perlen", "Draht",
    "Werkzeug", "Set", "Buch", "Anleitung"
]


def categorize_product(sku):
    """Categorize product."""
    print(f"Categorizing product: {sku}")

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
            descriptionHtml
            vendor
            productType
            tags
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
    current_type = node.get("productType", "")

    print(f"   Product: {node['title']}")
    print(f"   Current type: {current_type or '(empty)'}")

    if current_type:
        print("   [OK] Product already has type")
        return True

    # Determine category from title and tags
    title_lower = node['title'].lower()
    tags_lower = [t.lower() for t in node.get('tags', [])]

    matched_category = None

    for category in CATEGORIES:
        if category.lower() in title_lower:
            matched_category = category
            break

    # Try tags if no match in title
    if not matched_category:
        for tag in tags_lower:
            for category in CATEGORIES:
                if category.lower() in tag:
                    matched_category = category
                    break
            if matched_category:
                break

    # Default to vendor name if no match
    if not matched_category:
        matched_category = node.get('vendor', 'Bastelmaterial')

    print(f"   Suggested type: {matched_category}")

    # Update product
    mutation = """
    mutation UpdateProduct($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          productType
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "input": {
            "id": node["id"],
            "productType": matched_category
        }
    }

    result = shopify.execute_graphql(mutation, variables)
    if result and "data" in result:
        errors = result["data"]["productUpdate"].get("userErrors", [])
        if errors:
            print(f"   [ERROR] {errors}")
            return False
        print(f"   [OK] Set product type to: {matched_category}")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Categorize product")
    parser.add_argument("--sku", required=True, help="Product SKU")
    args = parser.parse_args()

    success = categorize_product(args.sku)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
