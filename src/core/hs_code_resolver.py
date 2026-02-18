import csv
import os
import re


def _load_map(map_path):
    if not map_path or not os.path.exists(map_path):
        return []
    rows = []
    with open(map_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("hs_code"):
                continue
            rows.append(row)
    return rows


def _keywords_match(text, keywords):
    if not text or not keywords:
        return False
    text = text.lower()
    for kw in keywords:
        if kw and kw.lower() in text:
            return True
    return False


def _match_from_map(product, map_rows):
    title = (product.get("title") or "").lower()
    tags = " ".join(product.get("tags") or []).lower()
    vendor = (product.get("vendor") or "").lower()
    product_type = (product.get("product_type") or "").lower()

    scored = []
    for row in map_rows:
        rvendor = (row.get("vendor") or "").lower().strip()
        rtype = (row.get("product_type") or "").lower().strip()
        keywords = [k.strip() for k in (row.get("keywords") or "").split(";") if k.strip()]

        score = 0
        if rvendor and rvendor == vendor:
            score += 3
        if rtype and rtype == product_type:
            score += 2
        if keywords and (_keywords_match(title, keywords) or _keywords_match(tags, keywords)):
            score += 1

        if score > 0:
            scored.append((score, row))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]
    return {
        "hs_code": best.get("hs_code"),
        "confidence": float(best.get("confidence") or 0.6),
        "source": best.get("source") or "map",
    }


def _extract_hs_from_tags(tags):
    for tag in tags or []:
        match = re.search(r"\bHS[:\s-]?(\d{4,10})\b", tag, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _extract_hs_from_metafields(metafields):
    for mf in metafields or []:
        if mf.get("key") == "hs_code":
            return mf.get("value")
    return None


def _consensus_from_shopify(product, resolver, min_count=3, min_ratio=0.7):
    vendor = product.get("vendor")
    product_type = product.get("product_type")

    if not vendor and not product_type:
        return None

    query_parts = []
    if vendor:
        query_parts.append(f'vendor:"{vendor}"')
    if product_type:
        query_parts.append(f'product_type:"{product_type}"')

    query = " ".join(query_parts)

    gql = """
    query FindHsCandidates($query: String!, $first: Int!) {
      products(first: $first, query: $query) {
        edges {
          node {
            id
            title
            tags
            metafields(first: 10, namespace: "custom") {
              edges {
                node {
                  key
                  value
                }
              }
            }
          }
        }
      }
    }
    """

    result = resolver.client.execute_graphql(gql, {"query": query, "first": 25})
    if not result or not result.get("data", {}).get("products", {}).get("edges"):
        return None

    counts = {}
    total = 0

    for edge in result["data"]["products"]["edges"]:
        node = edge.get("node") or {}
        tags = node.get("tags") or []
        metafields = [mf.get("node") for mf in node.get("metafields", {}).get("edges", [])]
        code = _extract_hs_from_metafields(metafields) or _extract_hs_from_tags(tags)
        if code:
            counts[code] = counts.get(code, 0) + 1
            total += 1

    if not counts or total == 0:
        return None

    top_code, top_count = sorted(counts.items(), key=lambda x: x[1], reverse=True)[0]
    ratio = top_count / total

    if top_count >= min_count and ratio >= min_ratio:
        return {
            "hs_code": top_code,
            "confidence": round(ratio, 2),
            "source": "consensus",
            "sample_size": total,
        }

    return None


def resolve_hs_code(product, resolver, map_path=None):
    # Only propose if HS code missing
    current_hs = (product.get("primary_variant") or {}).get("inventory_hs_code")
    if current_hs:
        return None

    if map_path is None:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        map_path = os.path.join(root, "data", "hs_code_map.csv")

    map_rows = _load_map(map_path)
    map_candidate = _match_from_map(product, map_rows)
    consensus_candidate = _consensus_from_shopify(product, resolver)

    if map_candidate and consensus_candidate:
        if map_candidate["hs_code"] == consensus_candidate["hs_code"]:
            return {
                "hs_code": map_candidate["hs_code"],
                "confidence": max(map_candidate.get("confidence", 0.6), consensus_candidate.get("confidence", 0.7)),
                "source": "map+consensus",
            }

    if consensus_candidate:
        return consensus_candidate

    if map_candidate:
        return map_candidate

    return None
