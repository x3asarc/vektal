import argparse
import os
import re
import sys
import time
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# Add project root to path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.image_scraper import ShopifyClient, clean_product_name
from src.core.shopify_resolver import ShopifyResolver


STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "for", "with", "in", "on", "to",
    "set", "pack", "pcs", "piece", "pieces", "x", "by",
    "ml", "l", "g", "kg", "oz", "lb", "cm", "mm", "m", "inch", "inches",
}

COLOR_WORDS = {
    "black", "white", "red", "green", "blue", "yellow", "orange", "pink",
    "purple", "violet", "brown", "gray", "grey", "silver", "gold", "beige",
    "ivory", "turquoise", "navy", "teal",
}

UNIT_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?\s*(ml|l|g|kg|oz|lb|cm|mm|m|in|inch|inches)\b")
MULTIPACK_PATTERN = re.compile(r"\b\d+\s*[xX]\s*\d+\b")


def normalize_title(title):
    if not title:
        return []
    cleaned = clean_product_name(title) or title
    cleaned = cleaned.lower()
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = MULTIPACK_PATTERN.sub(" ", cleaned)
    cleaned = UNIT_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", cleaned)
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    filtered = []
    for token in tokens:
        if token.isdigit():
            continue
        if token in STOPWORDS or token in COLOR_WORDS:
            continue
        if len(token) < 3:
            continue
        filtered.append(token)
    return filtered


def build_query(tokens, vendor=None, max_keywords=4):
    keywords = tokens[:max_keywords] if tokens else []
    terms = [f"title:*{kw}*" for kw in keywords]
    if vendor:
        vendor_value = f"\"{vendor}\"" if " " in vendor else vendor
        terms.append(f"vendor:{vendor_value}")
    return " ".join(terms).strip()


def normalize_image_url(url):
    if not url:
        return url
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def search_products(client, query, limit=50):
    results = []
    cursor = None

    gql = """
    query SearchProducts($query: String!, $first: Int!, $after: String) {
      products(first: $first, query: $query, after: $after) {
        edges {
          node {
            id
            handle
            title
            vendor
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    while len(results) < limit:
        variables = {
            "query": query,
            "first": min(50, limit - len(results)),
            "after": cursor,
        }
        resp = client.execute_graphql(gql, variables)
        edges = resp.get("data", {}).get("products", {}).get("edges", []) if resp else []
        for edge in edges:
            node = edge.get("node") or {}
            if node:
                results.append(node)
        page_info = resp.get("data", {}).get("products", {}).get("pageInfo", {}) if resp else {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    return results


def get_product_by_id(client, product_id):
    gql = """
    query GetProduct($id: ID!) {
      product(id: $id) {
        id
        handle
        title
        vendor
      }
    }
    """
    resp = client.execute_graphql(gql, {"id": product_id})
    return resp.get("data", {}).get("product") if resp else None


def fetch_media_urls(client, product_id, limit=200):
    gql = """
    query GetProductMedia($id: ID!, $first: Int!, $after: String) {
      product(id: $id) {
        media(first: $first, after: $after) {
          edges {
            node {
              ... on MediaImage {
                image { url }
              }
            }
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """
    urls = []
    cursor = None
    while len(urls) < limit:
        variables = {
            "id": product_id,
            "first": min(50, limit - len(urls)),
            "after": cursor,
        }
        resp = client.execute_graphql(gql, variables)
        media = resp.get("data", {}).get("product", {}).get("media") if resp else None
        edges = media.get("edges", []) if media else []
        for edge in edges:
            node = edge.get("node") or {}
            img = (node.get("image") or {}).get("url")
            if img:
                urls.append(img)
        page_info = media.get("pageInfo", {}) if media else {}
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")
    return urls


def collect_candidate_images(client, candidates, max_per_product):
    image_map = {}
    for candidate in candidates:
        media_urls = fetch_media_urls(client, candidate.get("id"), limit=max_per_product)
        image_map[candidate.get("id")] = {
            "product": candidate,
            "urls": media_urls,
        }
    return image_map


def is_variant_match(ref_tokens, cand_tokens, min_overlap=2, min_ratio=0.6):
    if not ref_tokens or not cand_tokens:
        return False
    ref_set = set(ref_tokens)
    cand_set = set(cand_tokens)
    overlap = len(ref_set & cand_set)
    effective_min = min(min_overlap, len(ref_set))
    ratio = overlap / max(len(ref_set), 1)
    return overlap >= effective_min and ratio >= min_ratio


def resolve_reference_product(resolver, client, args):
    if args.product_id:
        return get_product_by_id(client, args.product_id)

    if args.sku:
        identifier = {"kind": "sku", "value": args.sku}
    elif args.handle:
        identifier = {"kind": "handle", "value": args.handle}
    elif args.title:
        identifier = {"kind": "title", "value": args.title}
    elif args.url:
        identifier = {"kind": "url", "value": args.url}
    else:
        return None

    resolved = resolver.resolve_identifier(identifier)
    matches = resolved.get("matches", [])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print("Multiple products matched the identifier. Use --handle or --product-id to disambiguate.")
        for match in matches[:5]:
            print(f"  - {match.get('title')} ({match.get('handle')})")
    else:
        print("No products matched the identifier.")
    return None


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Propagate images from variant-like products to a reference product."
    )
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--sku", help="Reference product SKU")
    id_group.add_argument("--handle", help="Reference product handle")
    id_group.add_argument("--title", help="Reference product title")
    id_group.add_argument("--url", help="Reference product URL")
    id_group.add_argument("--product-id", help="Reference product GraphQL ID")

    parser.add_argument("--shop-domain", help="Shopify shop domain override")
    parser.add_argument("--access-token", help="Shopify access token override")
    parser.add_argument("--api-version", default=os.getenv("API_VERSION", "2024-01"))
    parser.add_argument("--focus", help="Override title keywords (e.g. 'galaxy flakes') for matching/query")
    parser.add_argument("--max-keywords", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--max-images", type=int, default=50)
    parser.add_argument("--max-images-per-product", type=int, default=20)
    parser.add_argument("--min-overlap", type=int, default=2)
    parser.add_argument("--min-overlap-ratio", type=float, default=0.6)
    parser.add_argument("--require-vendor", dest="require_vendor", action="store_true")
    parser.add_argument("--no-require-vendor", dest="require_vendor", action="store_false")
    parser.set_defaults(require_vendor=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--common-only", dest="common_only", action="store_true",
                        help="Only add images that appear across all matched candidates")
    parser.add_argument("--no-common-only", dest="common_only", action="store_false")
    parser.add_argument("--report-missing", dest="report_missing", action="store_true",
                        help="Report images missing from each candidate relative to the union set")
    parser.add_argument("--no-report-missing", dest="report_missing", action="store_false")
    parser.add_argument("--report-limit", type=int, default=10,
                        help="Max missing image URLs to list per candidate")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.set_defaults(common_only=True)
    parser.set_defaults(report_missing=False)

    args = parser.parse_args()

    resolver = ShopifyResolver(
        shop_domain=args.shop_domain or os.getenv("SHOP_DOMAIN"),
        access_token=args.access_token,
        api_version=args.api_version,
    )
    client = resolver.client

    ref_product = resolve_reference_product(resolver, client, args)
    if not ref_product:
        return

    ref_title = ref_product.get("title")
    ref_tokens = normalize_title(ref_title)
    if args.focus:
        focus_tokens = normalize_title(args.focus)
        if focus_tokens:
            ref_tokens = focus_tokens
            print(f"Using focus keywords: {' '.join(ref_tokens)}")
    if not ref_tokens:
        print("Could not extract keywords from reference title.")
        return

    vendor = ref_product.get("vendor") if args.require_vendor else None
    query = build_query(ref_tokens, vendor=vendor, max_keywords=args.max_keywords)
    if not query:
        print("Search query is empty after keyword extraction.")
        return

    print(f"Reference product: {ref_title} ({ref_product.get('handle')})")
    print(f"Search query: {query}")

    candidates = search_products(client, query, limit=args.max_candidates)
    filtered = []
    for candidate in candidates:
        if candidate.get("id") == ref_product.get("id"):
            continue
        if args.require_vendor and (candidate.get("vendor") or "").lower() != (ref_product.get("vendor") or "").lower():
            continue
        cand_tokens = normalize_title(candidate.get("title"))
        if not is_variant_match(ref_tokens, cand_tokens, args.min_overlap, args.min_overlap_ratio):
            continue
        filtered.append(candidate)

    if not filtered:
        print("No related products matched the variant criteria.")
        return

    print(f"Matched {len(filtered)} candidate products.")

    existing_urls = fetch_media_urls(client, ref_product.get("id"), limit=200)
    existing_norm = {normalize_image_url(u) for u in existing_urls if u}

    candidate_images = collect_candidate_images(client, filtered, args.max_images_per_product)
    usable_candidates = []
    for entry in candidate_images.values():
        if len(entry["urls"]) > 1:
            usable_candidates.append(entry)
    if not usable_candidates:
        print("No candidate products had more than 1 image.")
        return

    print("Candidate image counts:")
    for entry in usable_candidates:
        product = entry["product"]
        print(f"  - {product.get('title')} ({product.get('handle')}): {len(entry['urls'])} images")

    common_set = None
    union_norm = set()
    norm_to_url = {}
    candidate_norms = {}
    for entry in usable_candidates:
        normalized = {normalize_image_url(u) for u in entry["urls"] if u}
        candidate_norms[entry["product"].get("id")] = normalized
        if common_set is None:
            common_set = normalized
        else:
            common_set = common_set & normalized
        for url in entry["urls"]:
            norm = normalize_image_url(url)
            if not norm:
                continue
            union_norm.add(norm)
            if norm not in norm_to_url:
                norm_to_url[norm] = url

    common_set = common_set or set()
    if args.common_only:
        selected_norm = common_set
    else:
        selected_norm = set(union_norm)

    selected_norm = {u for u in selected_norm if u and u not in existing_norm}
    if not selected_norm:
        print("No new images found to add after filtering.")
        if args.report_missing:
            print("Missing image report (relative to union set):")
            for entry in usable_candidates:
                product = entry["product"]
                cand_norm = candidate_norms.get(product.get("id"), set())
                missing = union_norm - cand_norm
                print(f"  - {product.get('title')} ({product.get('handle')}): missing {len(missing)}")
                if args.report_limit > 0:
                    for url in sorted(missing)[:args.report_limit]:
                        print(f"      {norm_to_url.get(url, url)}")
        return

    # Preserve original URLs where possible for upload
    unique_urls = []
    seen = set(existing_norm)
    for norm in selected_norm:
        url = norm_to_url.get(norm, norm)
        if norm not in seen:
            seen.add(norm)
            unique_urls.append(url)

    to_add = unique_urls[:args.max_images]
    print(f"Prepared {len(to_add)} images to add (of {len(unique_urls)} found).")

    if args.report_missing:
        print("Missing image report (relative to union set):")
        for entry in usable_candidates:
            product = entry["product"]
            cand_norm = candidate_norms.get(product.get("id"), set())
            missing = union_norm - cand_norm
            print(f"  - {product.get('title')} ({product.get('handle')}): missing {len(missing)}")
            if args.report_limit > 0:
                for url in sorted(missing)[:args.report_limit]:
                    print(f"      {norm_to_url.get(url, url)}")

    if args.dry_run:
        for url in to_add:
            print(f"  [dry-run] {url}")
        return

    added = 0
    for url in to_add:
        result = client.update_product_media(ref_product.get("id"), url, alt_text=ref_title)
        errors = result.get("data", {}).get("productCreateMedia", {}).get("userErrors") if result else None
        if errors:
            print(f"  Failed to add image: {errors}")
        else:
            added += 1
        time.sleep(args.sleep)

    print(f"Added {added} images to reference product.")


if __name__ == "__main__":
    main()
