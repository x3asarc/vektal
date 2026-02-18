"""
Enrich product with logistics data: Country of Origin, HS Code, Weight

Fetches logistics data from vendor configs or external sources and updates product.

Usage:
    python utils/enrich_product_logistics.py --sku "ABC123"
"""

import os
import sys
import argparse
import yaml

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seo.seo_generator import ShopifyClient


def load_vendor_logistics_data():
    """Load vendor-specific logistics defaults from config."""
    config_path = "config/vendor_configs.yaml"
    if not os.path.exists(config_path):
        # Fallback to root directory
        config_path = "vendor_configs.yaml"
        if not os.path.exists(config_path):
            return {}

    with open(config_path, 'r', encoding='utf-8') as f:
        configs = yaml.safe_load(f)

    logistics = {}
    for vendor_name, config in configs.items():
        if isinstance(config, dict):
            logistics[vendor_name] = {
                "country_of_origin": config.get("country_of_origin", ""),
                "default_hs_code": config.get("hs_code_default", ""),  # Match YAML key name
                "default_weight": config.get("default_weight", 0.1)
            }

    return logistics


def enrich_product(sku):
    """Enrich product with logistics data."""
    print(f"Enriching product: {sku}")

    # Connect to Shopify
    shopify = ShopifyClient()
    if not shopify.authenticate():
        print("[ERROR] Failed to authenticate")
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
            variants(first: 1) {
              edges {
                node {
                  id
                  sku
                }
              }
            }
          }
        }
      }
    }
    """

    result = shopify.execute_graphql(query, {"query": f"sku:{sku}"})
    if not result or "data" not in result:
        print("[ERROR] Product not found")
        return False

    edges = result["data"]["products"]["edges"]
    if not edges:
        print("[ERROR] Product not found")
        return False

    node = edges[0]["node"]
    product_id = node["id"]
    vendor = node.get("vendor", "")
    variant_id = node["variants"]["edges"][0]["node"]["id"] if node["variants"]["edges"] else None

    print(f"   Product: {node['title']}")
    print(f"   Vendor: {vendor}")

    # Load vendor logistics data
    all_vendor_data = load_vendor_logistics_data()

    # Try exact match first
    vendor_data = all_vendor_data.get(vendor, {})

    # If no exact match, try lowercase and with underscores
    if not vendor_data:
        vendor_key = vendor.lower().replace(" ", "_")
        vendor_data = all_vendor_data.get(vendor_key, {})

    # If still no match, try lowercase without underscores
    if not vendor_data:
        vendor_key = vendor.lower()
        vendor_data = all_vendor_data.get(vendor_key, {})

    if not vendor_data:
        print(f"   [WARNING] No logistics data for vendor: {vendor}")
        print(f"   [TIP] Add logistics defaults to vendor_configs.yaml")
        print(f"   [DEBUG] Available vendors: {list(all_vendor_data.keys())}")
        return False

    # Prepare updates
    metafields = []

    if vendor_data.get("country_of_origin"):
        metafields.append({
            "namespace": "custom",
            "key": "country_of_origin",
            "value": vendor_data["country_of_origin"],
            "type": "single_line_text_field"
        })
        print(f"   > Country of Origin: {vendor_data['country_of_origin']}")

    if vendor_data.get("default_hs_code"):
        metafields.append({
            "namespace": "custom",
            "key": "hs_code",
            "value": vendor_data["default_hs_code"],
            "type": "single_line_text_field"
        })
        print(f"   > HS Code: {vendor_data['default_hs_code']}")

    # Update product
    mutation = """
    mutation UpdateProduct($input: ProductInput!) {
      productUpdate(input: $input) {
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
        "input": {
            "id": product_id,
            "metafields": metafields
        }
    }

    result = shopify.execute_graphql(mutation, variables)

    if result and "data" in result:
        errors = result["data"]["productUpdate"].get("userErrors", [])
        if errors:
            print(f"   [ERROR] {errors}")
            return False

        print("   [OK] Updated metafields")

        # Note: Weight update not supported in this API version
        # Weight can be managed via metafields if needed:
        # - Add weight to metafields in config/product_quality_rules.yaml
        # - Store as custom.weight metafield

        return True

    print("[ERROR] Failed to update product")
    return False


def main():
    parser = argparse.ArgumentParser(description="Enrich product with logistics data")
    parser.add_argument("--sku", required=True, help="Product SKU")
    args = parser.parse_args()

    success = enrich_product(args.sku)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
