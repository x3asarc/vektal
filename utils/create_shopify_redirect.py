"""
Create Shopify URL redirect to preserve old URLs when handles change.

Usage:
    python utils/create_shopify_redirect.py --old-path "/products/old-handle" --new-path "/products/new-handle"
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo.seo_generator import ShopifyClient


def create_redirect(old_path, new_path):
    """Create a URL redirect in Shopify."""
    print(f"Creating redirect: {old_path} -> {new_path}")

    shopify = ShopifyClient()
    if not shopify.authenticate():
        print("[ERROR] Failed to authenticate")
        return False

    # Create redirect
    mutation = """
    mutation CreateRedirect($redirect: UrlRedirectInput!) {
      urlRedirectCreate(urlRedirect: $redirect) {
        urlRedirect {
          id
          path
          target
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "redirect": {
            "path": old_path,
            "target": new_path
        }
    }

    result = shopify.execute_graphql(mutation, variables)

    if result and "data" in result:
        errors = result["data"]["urlRedirectCreate"].get("userErrors", [])
        if errors:
            print(f"   [ERROR] {errors}")
            return False

        redirect = result["data"]["urlRedirectCreate"]["urlRedirect"]
        print(f"   [OK] Redirect created: {redirect['path']} -> {redirect['target']}")
        return True

    print("[ERROR] Failed to create redirect")
    return False


def main():
    parser = argparse.ArgumentParser(description="Create Shopify URL redirect")
    parser.add_argument("--old-path", required=True, help="Old URL path (e.g., /products/old-handle)")
    parser.add_argument("--new-path", required=True, help="New URL path (e.g., /products/new-handle)")
    args = parser.parse_args()

    success = create_redirect(args.old_path, args.new_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
