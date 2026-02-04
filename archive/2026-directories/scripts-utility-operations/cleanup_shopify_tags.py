"""
Normalize and clean Shopify product tags.

Rules:
 - lowercase, trim, collapse multiple spaces
 - remove blacklisted tags (APPSTLE_BUNDLE / APPSTEL_BUNDLE)
 - remove HTML/escaped artifacts
 - if "decoupage" is present, ensure "reispapier" and "reis papier"

Usage:
  python scripts/cleanup_shopify_tags.py --dry-run
  python scripts/cleanup_shopify_tags.py --apply --sleep 0.25
"""

import os
import sys
import json
import time
import argparse
import re
from datetime import datetime
from collections import Counter

from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath("."))
from seo.seo_generator import ShopifyClient


BLACKLIST_TAGS = {"appstle_bundle", "appstel_bundle"}
HTML_LIKE_PATTERN = re.compile(r"&lt;|&gt;|<br|&quot;|&amp;|\\n", re.IGNORECASE)


def _normalize_tag(tag):
    return re.sub(r"\\s+", " ", str(tag).strip().lower())


def _dedupe_preserve(tags):
    seen = set()
    deduped = []
    for tag in tags:
        if tag not in seen:
            deduped.append(tag)
            seen.add(tag)
    return deduped


def _clean_tags(tags):
    cleaned = []
    removed = []
    for tag in tags or []:
        t = _normalize_tag(tag)
        if not t:
            continue
        if t in BLACKLIST_TAGS or HTML_LIKE_PATTERN.search(t):
            removed.append(t)
            continue
        cleaned.append(t)
    cleaned = _dedupe_preserve(cleaned)
    return cleaned, removed


def _ensure_decoupage_tags(tags):
    if "decoupage" in tags:
        if "reispapier" not in tags:
            tags.append("reispapier")
        if "reis papier" not in tags:
            tags.append("reis papier")
    return tags


def fetch_page(client, cursor=None):
    query = """
    query GetProducts($first: Int!, $after: String) {
      products(first: $first, after: $after) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            title
            handle
            vendor
            tags
          }
        }
      }
    }
    """
    variables = {"first": 250, "after": cursor}
    result = client.execute_graphql(query, variables)
    if not result or "data" not in result:
        raise RuntimeError("GraphQL query failed")
    edges = result["data"]["products"]["edges"]
    page = result["data"]["products"]["pageInfo"]
    return edges, page


def update_tags(client, product_id, tags):
    mutation = """
    mutation UpdateProductTags($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id tags }
        userErrors { field message }
      }
    }
    """
    variables = {"input": {"id": product_id, "tags": tags}}
    result = client.execute_graphql(mutation, variables)
    if not result:
        return False, ["mutation_failed"]
    errors = result["data"]["productUpdate"].get("userErrors") or []
    if errors:
        return False, errors
    return True, []


def main():
    parser = argparse.ArgumentParser(description="Cleanup Shopify product tags")
    parser.add_argument("--apply", action="store_true", help="Apply updates to Shopify")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between updates (seconds)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of products processed")
    parser.add_argument("--report", default=None, help="Write JSON report to this path")
    parser.add_argument("--start-cursor", default=None, help="Resume from a Shopify pagination cursor")
    parser.add_argument("--cursor-file", default=None, help="Read/write pagination cursor to this file")
    args = parser.parse_args()

    load_dotenv(os.path.join(os.getcwd(), ".env"))
    client = ShopifyClient()
    if not client.authenticate():
        print("AUTH_FAILED")
        return 1

    processed = 0
    updated = 0
    skipped = 0
    errors = 0

    tag_counts = Counter()
    removed_counts = Counter()
    decoupage_added = 0

    changes = []

    cursor = args.start_cursor
    if not cursor and args.cursor_file and os.path.exists(args.cursor_file):
        with open(args.cursor_file, "r", encoding="utf-8") as f:
            cursor = f.read().strip() or None

    while True:
        edges, page = fetch_page(client, cursor)
        for edge in edges:
            node = edge["node"]
            product = {
                "id": node.get("id"),
                "title": node.get("title") or "",
                "handle": node.get("handle") or "",
                "vendor": node.get("vendor") or "",
                "tags": node.get("tags") or [],
            }

            processed += 1
            current_tags = product.get("tags") or []
            cleaned, removed = _clean_tags(current_tags)
            cleaned = _ensure_decoupage_tags(cleaned)

            if "decoupage" in cleaned:
                if "reispapier" in cleaned and "reis papier" in cleaned:
                    if "reispapier" not in current_tags or "reis papier" not in current_tags:
                        decoupage_added += 1

            proposed = cleaned
            if proposed != current_tags:
                if args.apply:
                    ok, errs = update_tags(client, product["id"], proposed)
                    if not ok:
                        errors += 1
                        changes.append({
                            "status": "error",
                            "id": product["id"],
                            "handle": product["handle"],
                            "title": product["title"],
                            "errors": errs,
                        })
                    else:
                        updated += 1
                        changes.append({
                            "status": "updated",
                            "id": product["id"],
                            "handle": product["handle"],
                            "title": product["title"],
                            "before": current_tags,
                            "after": proposed,
                        })
                        time.sleep(args.sleep)
                else:
                    updated += 1
                    changes.append({
                        "status": "would_update",
                        "id": product["id"],
                        "handle": product["handle"],
                        "title": product["title"],
                        "before": current_tags,
                        "after": proposed,
                    })
            else:
                skipped += 1

            for t in proposed:
                tag_counts[t] += 1
            for r in removed:
                removed_counts[r] += 1

            if args.limit and processed >= args.limit:
                break

        if args.cursor_file:
            os.makedirs(os.path.dirname(args.cursor_file) or ".", exist_ok=True)
            with open(args.cursor_file, "w", encoding="utf-8") as f:
                f.write(page.get("endCursor") or "")

        if processed % 250 == 0:
            print(f"Processed {processed} products... updated={updated} skipped={skipped} errors={errors}")

        if args.limit and processed >= args.limit:
            break

        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "processed": processed,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "decoupage_added_products": decoupage_added,
        "removed_tags": removed_counts.most_common(50),
        "top_tags": tag_counts.most_common(50),
        "changes_sample": changes[:50],
    }

    print(json.dumps(report, ensure_ascii=False))

    if args.report:
        os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
