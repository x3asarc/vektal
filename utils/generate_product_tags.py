"""
Generate product tags using AI based on product data.

Usage:
    python utils/generate_product_tags.py --sku "ABC123"
"""

import os
import sys
import argparse
import re
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo.seo_generator import ShopifyClient, SEOContentGenerator


BLACKLIST_TAGS = {"appstle_bundle", "appstel_bundle"}
HTML_LIKE_PATTERN = re.compile(r"&lt;|&gt;|<br|&quot;|&amp;|\\n", re.IGNORECASE)


def _normalize_tag(tag):
    return re.sub(r"\\s+", " ", str(tag).strip().lower())


def _clean_tags(tags):
    cleaned = []
    seen = set()
    removed = []
    for tag in tags or []:
        t = _normalize_tag(tag)
        if not t:
            continue
        if t in BLACKLIST_TAGS or HTML_LIKE_PATTERN.search(t):
            removed.append(t)
            continue
        if t not in seen:
            cleaned.append(t)
            seen.add(t)
    return cleaned, removed


def _load_min_tag_count(vendor):
    default_min = 3
    config_path = Path(__file__).resolve().parents[1] / "config" / "product_quality_rules.yaml"
    if not config_path.exists():
        return default_min
    try:
        with config_path.open("r", encoding="utf-8") as f:
            rules = yaml.safe_load(f) or {}
        required = rules.get("required_fields", {})
        default_min = int((required.get("tags") or {}).get("min_count", default_min))
        vendor_rules = (rules.get("vendor_rules") or {}).get(vendor or "", {})
        vendor_min = (vendor_rules.get("tags") or {}).get("min_count")
        if vendor_min:
            return int(vendor_min)
    except Exception:
        return default_min
    return default_min


def _ensure_decoupage_tags(tags):
    if "decoupage" in tags:
        if "reispapier" not in tags:
            tags.append("reispapier")
        if "reis papier" not in tags:
            tags.append("reis papier")
    return tags


def generate_tags(sku):
    """Generate tags for product."""
    print(f"Generating tags for: {sku}")

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
    current_tags = node.get("tags", [])
    cleaned_tags, removed = _clean_tags(current_tags)
    cleaned_tags = _ensure_decoupage_tags(cleaned_tags)
    min_tags_required = _load_min_tag_count(node.get("vendor", ""))

    print(f"   Product: {node['title']}")
    print(f"   Current tags: {len(current_tags)} (cleaned: {len(cleaned_tags)})")
    if removed:
        print(f"   Removed blacklisted/invalid tags: {', '.join(removed[:5])}{'...' if len(removed) > 5 else ''}")

    if len(cleaned_tags) >= min_tags_required:
        print("   [OK] Product already has sufficient tags")
        return True

    # Generate tags using AI
    try:
        generator = SEOContentGenerator()

        prompt = f"""Generate 5-7 relevant product tags for this product.

Product Title: {node['title']}
Vendor: {node.get('vendor', '')}
Product Type: {node.get('productType', '')}
Description: {node.get('descriptionHtml', '')[:500]}

Return only a comma-separated list of tags in German. Tags should be:
- Relevant keywords
- Category names
- Material types
- Use cases
- Brand/vendor name

Example: farbe, acryl, basteln, dekoration, pentart"""

        response = generator.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.7}
        )

        tags_text = response.text.strip()
        new_tags = [_normalize_tag(tag) for tag in tags_text.split(",") if tag.strip()]

        # Combine with existing tags
        all_tags = cleaned_tags + new_tags
        # De-dupe while preserving order
        deduped = []
        seen = set()
        for tag in all_tags:
            t = _normalize_tag(tag)
            if not t or t in BLACKLIST_TAGS or HTML_LIKE_PATTERN.search(t):
                continue
            if t not in seen:
                deduped.append(t)
                seen.add(t)
        all_tags = _ensure_decoupage_tags(deduped)

        print(f"   Generated {len(new_tags)} new tags: {', '.join(new_tags[:5])}")

        # Update product
        mutation = """
        mutation UpdateProduct($input: ProductInput!) {
          productUpdate(input: $input) {
            product {
              id
              tags
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
                "tags": all_tags
            }
        }

        result = shopify.execute_graphql(mutation, variables)
        if result and "data" in result:
            errors = result["data"]["productUpdate"].get("userErrors", [])
            if errors:
                print(f"   [ERROR] {errors}")
                return False
            print(f"   [OK] Updated tags (total: {len(all_tags)})")
            return True

    except Exception as e:
        print(f"   [ERROR] Failed to generate tags: {e}")
        return False

    return False


def main():
    parser = argparse.ArgumentParser(description="Generate product tags")
    parser.add_argument("--sku", required=True, help="Product SKU")
    args = parser.parse_args()

    success = generate_tags(args.sku)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
