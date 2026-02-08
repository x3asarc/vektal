"""
Catalog Extraction Utilities

Extract intelligence from existing Shopify product catalogs:
- Keywords via TF-IDF
- Niche detection via category/tag analysis
- SKU pattern learning via regex inference
- Vendor extraction from product vendor fields
"""

import re
from collections import Counter
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer

# Niche definitions for classification
NICHE_KEYWORDS = {
    "arts_and_crafts": [
        "decoupage", "scrapbooking", "craft", "basteln", "diy", "handmade",
        "rice paper", "reispapier", "napkin", "serviette", "stencil", "schablone",
        "acrylic", "acryl", "paint", "farbe", "brush", "pinsel", "canvas", "leinwand"
    ],
    "automotive": [
        "car", "auto", "vehicle", "motor", "engine", "brake", "oil", "filter",
        "tire", "wheel", "battery", "exhaust", "spark plug"
    ],
    "electronics": [
        "electronic", "circuit", "resistor", "capacitor", "led", "arduino",
        "raspberry", "sensor", "component", "pcb", "chip"
    ],
    "fashion": [
        "clothing", "dress", "shirt", "pants", "shoes", "accessory", "jewelry",
        "necklace", "ring", "bracelet", "fashion"
    ],
    "home_garden": [
        "furniture", "decor", "garden", "plant", "pot", "tool", "kitchen",
        "bathroom", "bedroom", "living room"
    ]
}


def extract_keywords(
    products: list[dict],
    top_n: int = 20,
    language: str = "german"
) -> list[str]:
    """
    Extract top keywords from product titles and descriptions using TF-IDF.

    Args:
        products: List of Shopify product dicts with 'title' and 'body_html'
        top_n: Number of top keywords to return
        language: Stop words language ('german' or 'english')

    Returns:
        List of top keywords sorted by importance
    """
    if not products:
        return []

    # Combine title and description for each product
    texts = []
    for p in products:
        title = p.get('title', '') or ''
        body = p.get('body_html', '') or ''
        # Strip HTML tags from body
        body = re.sub(r'<[^>]+>', ' ', body)
        texts.append(f"{title} {body}")

    # TF-IDF extraction
    try:
        vectorizer = TfidfVectorizer(
            max_features=top_n * 2,  # Get more, filter later
            stop_words=language,
            min_df=2,  # Must appear in at least 2 products
            max_df=0.95,  # Ignore too common words
            token_pattern=r'(?u)\b[a-zA-ZäöüÄÖÜß]{3,}\b'  # 3+ letter words, including German
        )
        vectorizer.fit(texts)
        keywords = vectorizer.get_feature_names_out().tolist()

        # Filter out very short words and return top N
        keywords = [k for k in keywords if len(k) >= 3]
        return keywords[:top_n]

    except Exception:
        # Fallback: simple word frequency
        all_words = ' '.join(texts).lower().split()
        word_counts = Counter(w for w in all_words if len(w) >= 3)
        return [word for word, _ in word_counts.most_common(top_n)]


def detect_niche(
    products: list[dict],
    keywords: list[str] = None
) -> tuple[str, float, dict]:
    """
    Detect store niche from products and keywords.

    Args:
        products: List of Shopify product dicts
        keywords: Pre-extracted keywords (optional, will extract if not provided)

    Returns:
        Tuple of (niche_name, confidence, evidence_dict)
    """
    if not products:
        return "unknown", 0.0, {}

    if keywords is None:
        keywords = extract_keywords(products)

    # Collect all text for analysis
    all_text = ' '.join([
        (p.get('title', '') + ' ' +
         p.get('product_type', '') + ' ' +
         ' '.join(p.get('tags', []) if isinstance(p.get('tags'), list) else []))
        for p in products
    ]).lower()

    # Score each niche
    niche_scores = {}
    niche_evidence = {}

    for niche, niche_keywords in NICHE_KEYWORDS.items():
        score = 0
        matches = []
        for kw in niche_keywords:
            count = all_text.count(kw.lower())
            if count > 0:
                score += count
                matches.append((kw, count))

        niche_scores[niche] = score
        niche_evidence[niche] = sorted(matches, key=lambda x: -x[1])[:5]

    # Find best niche
    if not niche_scores or max(niche_scores.values()) == 0:
        return "other", 0.3, {}

    best_niche = max(niche_scores, key=niche_scores.get)
    total_score = sum(niche_scores.values())
    confidence = niche_scores[best_niche] / total_score if total_score > 0 else 0

    # Adjust confidence based on clarity
    second_best = sorted(niche_scores.values(), reverse=True)[1] if len(niche_scores) > 1 else 0
    if niche_scores[best_niche] > second_best * 2:
        confidence = min(confidence + 0.2, 0.99)

    return best_niche, round(confidence, 2), niche_evidence.get(best_niche, [])


def learn_sku_patterns(
    products: list[dict],
    min_occurrences: int = 5
) -> dict[str, dict]:
    """
    Learn SKU patterns from existing products.

    Args:
        products: List of Shopify product dicts with 'variants' containing 'sku'
        min_occurrences: Minimum SKUs matching pattern to include

    Returns:
        Dict mapping pattern -> {regex, examples, count, vendor_hint}
    """
    skus = []
    sku_vendor_map = {}

    for p in products:
        vendor = p.get('vendor', 'Unknown')
        for v in p.get('variants', []):
            sku = v.get('sku', '')
            if sku and len(sku) >= 3:
                skus.append(sku)
                sku_vendor_map[sku] = vendor

    if not skus:
        return {}

    # Common pattern templates to test
    pattern_templates = [
        (r'^[A-Z]{1,2}\d{4,6}[A-Z]?$', 'Letter prefix + digits + optional suffix'),
        (r'^[A-Z]{2,3}-\d{4,6}$', 'Letters-digits with hyphen'),
        (r'^\d{5,13}$', 'Pure numeric (barcode-like)'),
        (r'^[A-Z]{3,4}\d{3,5}$', 'Short prefix + digits'),
    ]

    patterns_found = {}

    for pattern, desc in pattern_templates:
        regex = re.compile(pattern, re.IGNORECASE)
        matches = [s for s in skus if regex.match(s)]

        if len(matches) >= min_occurrences:
            # Find most common vendor for this pattern
            vendor_counts = Counter(sku_vendor_map.get(s, 'Unknown') for s in matches)
            top_vendor = vendor_counts.most_common(1)[0][0] if vendor_counts else None

            patterns_found[pattern] = {
                'regex': pattern,
                'description': desc,
                'examples': matches[:5],
                'count': len(matches),
                'vendor_hint': top_vendor
            }

    return patterns_found


def extract_vendors(products: list[dict]) -> list[dict]:
    """
    Extract known vendors from product vendor fields.

    Args:
        products: List of Shopify product dicts with 'vendor' field

    Returns:
        List of vendor dicts with name, product_count, sample_skus
    """
    vendor_data = {}

    for p in products:
        vendor = p.get('vendor', '').strip()
        if not vendor:
            continue

        if vendor not in vendor_data:
            vendor_data[vendor] = {
                'name': vendor,
                'product_count': 0,
                'sample_skus': []
            }

        vendor_data[vendor]['product_count'] += 1

        # Collect sample SKUs
        for v in p.get('variants', []):
            sku = v.get('sku', '')
            if sku and len(vendor_data[vendor]['sample_skus']) < 5:
                vendor_data[vendor]['sample_skus'].append(sku)

    # Sort by product count
    return sorted(vendor_data.values(), key=lambda x: -x['product_count'])
