import os
import sys
import csv
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.image_scraper import ShopifyClient


QUERY = """
query getProducts($cursor: String, $search: String!) {
  products(first: 50, query: $search, after: $cursor) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        title
        handle
        vendor
        metafield(namespace: "shopify", key: "color-pattern") {
          value
        }
        variants(first: 10) {
          edges {
            node {
              sku
              barcode
            }
          }
        }
      }
    }
  }
}
"""


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export Shopify Farbe metafields (shopify.color-pattern)")
    parser.add_argument("--vendor", default="Pentart", help="Vendor to query (default: Pentart)")
    parser.add_argument("--out", default="data/output/farbe_metafields.csv", help="Output CSV path")
    args = parser.parse_args()

    client = ShopifyClient()
    client.authenticate()

    rows = []
    cursor = None
    has_next = True
    search = f'vendor:{args.vendor}'

    while has_next:
        result = client.execute_graphql(QUERY, {"cursor": cursor, "search": search})
        if not result or "data" not in result:
            break

        products = result["data"]["products"]
        for edge in products.get("edges", []):
            node = edge["node"]
            mf = node.get("metafield") or {}
            variants = node.get("variants", {}).get("edges", [])
            sku = ""
            barcode = ""
            if variants:
                v = variants[0]["node"]
                sku = v.get("sku") or ""
                barcode = v.get("barcode") or ""

            rows.append({
                "product_id": node.get("id"),
                "handle": node.get("handle"),
                "title": node.get("title"),
                "vendor": node.get("vendor"),
                "sku": sku,
                "barcode": barcode,
                "farbe": mf.get("value") if mf else "",
            })

        page_info = products.get("pageInfo", {})
        has_next = page_info.get("hasNextPage", False)
        cursor = page_info.get("endCursor")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["product_id", "handle", "title", "vendor", "sku", "barcode", "farbe"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
