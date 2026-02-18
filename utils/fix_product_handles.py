"""
Fix product URL handles to match product titles.

Usage:
    python utils/fix_product_handles.py --sku "ABC123"
"""

import os
import sys
import argparse
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo.seo_generator import ShopifyClient


def slugify(text):
    """Convert text to URL-safe slug."""
    text = text.lower()
    # Replace umlauts first (before removing special chars)
    text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    # Remove special characters (keep only alphanumeric, spaces, and hyphens)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace multiple spaces/hyphens with single hyphen
    text = re.sub(r'[\s-]+', '-', text)
    return text.strip('-')


def fix_handle(sku):
    """Fix product handle to match title."""
    print(f"Fixing handle for: {sku}")

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
            handle
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
    current_handle = node["handle"]
    title = node["title"]
    expected_handle = slugify(title)

    print(f"   Title: {title}")
    print(f"   Current handle: {current_handle}")
    print(f"   Expected handle: {expected_handle}")

    if current_handle == expected_handle:
        print("   [OK] Handle already matches title")
        return True

    # Update handle
    mutation = """
    mutation UpdateProduct($input: ProductInput!) {
      productUpdate(input: $input) {
        product {
          id
          handle
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
            "handle": expected_handle
        }
    }

    result = shopify.execute_graphql(mutation, variables)
    if result and "data" in result:
        errors = result["data"]["productUpdate"].get("userErrors", [])
        if errors:
            print(f"   [ERROR] {errors}")
            return False
        print(f"   [OK] Updated handle to: {expected_handle}")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Fix product URL handles")
    parser.add_argument("--sku", required=True, help="Product SKU")
    args = parser.parse_args()

    success = fix_handle(args.sku)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
