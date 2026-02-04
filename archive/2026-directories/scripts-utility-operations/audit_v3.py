import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from PIL import Image
import imagehash
import numpy as np
import yaml

# Third-party ML stack (Phase A)
import open_clip
import torch
from sklearn.cluster import AgglomerativeClustering

# Add project root to path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.shopify_resolver import ShopifyResolver
from src.core.image_scraper import clean_product_name


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

LABEL_SETS = {
    "basic": {
        "prompts": [
            "a product bottle packshot on white background",
            "a close-up macro texture of paint or glitter",
            "a technical label with text and ingredients",
            "a lifestyle photo showing the product used on an object",
            "a color swatch or paint sample",
            "a group shot of multiple product variants",
        ],
        "short_labels": [
            "packshot",
            "texture",
            "label",
            "lifestyle",
            "swatch",
            "group_shot",
        ],
    },
    "extended": {
        "prompts": [
            "a product bottle packshot on white background",
            "a product jar packshot on white background",
            "a product packshot on colored background",
            "a close-up macro texture of paint or glitter",
            "a close-up detail of glitter flakes or pigment",
            "a technical label with text and ingredients",
            "a back-of-package label with barcode",
            "a lifestyle photo showing the product used on an object",
            "a step-by-step application photo",
            "a color swatch or paint sample",
            "a group shot of multiple product variants",
            "a close-up detail of the container cap or lid",
            "a scale reference photo showing product size in hand",
        ],
        "short_labels": [
            "packshot_white_bottle",
            "packshot_white_jar",
            "packshot_color_bg",
            "texture_macro",
            "texture_detail",
            "label_front",
            "label_back",
            "lifestyle",
            "application_step",
            "swatch",
            "group_shot",
            "detail_cap",
            "in_hand_scale",
        ],
    },
}


def slugify(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


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


def is_variant_match(ref_tokens, cand_tokens, min_overlap=2, min_ratio=0.6):
    if not ref_tokens or not cand_tokens:
        return False
    ref_set = set(ref_tokens)
    cand_set = set(cand_tokens)
    overlap = len(ref_set & cand_set)
    effective_min = min(min_overlap, len(ref_set))
    ratio = overlap / max(len(ref_set), 1)
    return overlap >= effective_min and ratio >= min_ratio


def gid_to_numeric(gid):
    if not gid:
        return None
    return str(gid).split("/")[-1]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path


def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_image(session, url, dest_path):
    if os.path.exists(dest_path):
        return True
    try:
        resp = session.get(url, stream=True, timeout=20)
        resp.raise_for_status()
        ensure_dir(os.path.dirname(dest_path))
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"  Download failed: {url} ({e})")
        return False


def load_clip(model_name="ViT-B-32", pretrained="laion2b_s34b_b79k"):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    model.to(device)
    model.eval()
    tokenizer = open_clip.get_tokenizer(model_name)
    return model, preprocess, tokenizer, device


def compute_image_embedding(model, preprocess, device, image_path):
    image = Image.open(image_path).convert("RGB")
    image_input = preprocess(image).unsqueeze(0).to(device)
    with torch.no_grad():
        emb = model.encode_image(image_input)
    emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy().flatten()


def compute_text_embeddings(model, tokenizer, device, prompts):
    tokens = tokenizer(prompts).to(device)
    with torch.no_grad():
        emb = model.encode_text(tokens)
    emb = emb / emb.norm(dim=-1, keepdim=True)
    return emb.cpu().numpy()


def cosine_similarity(vec, mat):
    return np.dot(mat, vec) / (np.linalg.norm(vec) * np.linalg.norm(mat, axis=1) + 1e-8)


def resolve_reference_product(resolver, args):
    if args.product_id:
        gql = """
        query GetProductById($id: ID!) {
          product(id: $id) {
            id
            handle
            title
            vendor
          }
        }
        """
        resp = resolver.client.execute_graphql(gql, {"id": args.product_id})
        product = resp.get("data", {}).get("product") if resp else None
        return resolver._normalize_product(product) if product else None

    if args.ean:
        identifier = {"kind": "ean", "value": args.ean}
    elif args.sku:
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


def fetch_product_images(session, shop_domain, api_version, access_token, product_id):
    url = f"https://{shop_domain}/admin/api/{api_version}/products/{product_id}/images.json"
    headers = {"X-Shopify-Access-Token": access_token}
    params = {"limit": 250}
    resp = session.get(url, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json().get("images", [])


def build_thumbnail(src_path, dest_path, max_size=256):
    if os.path.exists(dest_path):
        return
    image = Image.open(src_path).convert("RGB")
    image.thumbnail((max_size, max_size))
    ensure_dir(os.path.dirname(dest_path))
    image.save(dest_path, format="JPEG", quality=85)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="SVSE Phase A: Visual audit and clustering.")
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument("--sku", help="Reference product SKU")
    id_group.add_argument("--ean", help="Reference product EAN")
    id_group.add_argument("--handle", help="Reference product handle")
    id_group.add_argument("--title", help="Reference product title")
    id_group.add_argument("--url", help="Reference product URL")
    id_group.add_argument("--product-id", help="Reference product handle (manual override)")

    parser.add_argument("--shop-domain", help="Shopify shop domain override")
    parser.add_argument("--access-token", help="Shopify access token override")
    parser.add_argument("--api-version", default=os.getenv("API_VERSION", "2024-01"))
    parser.add_argument("--focus", help="Override title keywords (e.g. 'galaxy flakes') for matching/query")
    parser.add_argument("--max-keywords", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=40)
    parser.add_argument("--min-overlap", type=int, default=2)
    parser.add_argument("--min-overlap-ratio", type=float, default=0.6)
    parser.add_argument("--require-vendor", dest="require_vendor", action="store_true")
    parser.add_argument("--no-require-vendor", dest="require_vendor", action="store_false")
    parser.set_defaults(require_vendor=True)

    parser.add_argument("--cache-dir", default="data/svse")
    parser.add_argument("--phash-size", type=int, default=8)
    parser.add_argument("--cluster-threshold", type=float, default=0.2)
    parser.add_argument("--score-threshold", type=float, default=0.6)
    parser.add_argument("--max-thumbs", type=int, default=4)
    parser.add_argument("--label-set", choices=sorted(LABEL_SETS.keys()), default="extended")
    parser.add_argument("--config-path", help="Override path for config.yaml")

    args = parser.parse_args()

    shop_domain = args.shop_domain or os.getenv("SHOP_DOMAIN")
    access_token = args.access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")
    if not shop_domain:
        print("Missing SHOP_DOMAIN. Provide --shop-domain or set SHOP_DOMAIN in env.")
        return

    resolver = ShopifyResolver(
        shop_domain=shop_domain,
        access_token=access_token,
        api_version=args.api_version,
    )
    if not access_token:
        access_token = resolver.client.access_token
    if not access_token:
        print("Could not obtain Shopify access token. Provide --access-token or set SHOPIFY_ACCESS_TOKEN.")
        return

    ref_product = resolve_reference_product(resolver, args)
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

    candidates = resolver._query_products(query, first=min(50, args.max_candidates))
    filtered = []
    product_lookup = {}
    for candidate in candidates:
        if candidate.get("id") == ref_product.get("id"):
            continue
        if args.require_vendor and (candidate.get("vendor") or "").lower() != (ref_product.get("vendor") or "").lower():
            continue
        cand_tokens = normalize_title(candidate.get("title"))
        if not is_variant_match(ref_tokens, cand_tokens, args.min_overlap, args.min_overlap_ratio):
            continue
        filtered.append(candidate)
        numeric_id = gid_to_numeric(candidate.get("id"))
        if numeric_id:
            product_lookup[numeric_id] = f"{candidate.get('title')} ({candidate.get('handle')})"

    if not filtered:
        print("No related products matched the variant criteria.")
        return

    print(f"Matched {len(filtered)} candidate products.")

    run_id = slugify(ref_title) or "svse"
    root = ensure_dir(os.path.join(args.cache_dir, run_id))
    images_dir = ensure_dir(os.path.join(root, "images"))
    thumbs_dir = ensure_dir(os.path.join(root, "reports", "thumbs"))
    cache_dir = ensure_dir(os.path.join(root, "cache"))
    report_path = os.path.join(root, "reports", "audit_report.html")
    ensure_dir(os.path.dirname(report_path))
    config_path = args.config_path or os.path.join(root, "config.yaml")

    label_set = LABEL_SETS.get(args.label_set)
    prompts = label_set["prompts"]
    short_labels = label_set["short_labels"]
    if len(prompts) != len(short_labels):
        print("Label set configuration error: prompt/label mismatch.")
        return

    print("Loading CLIP model...")
    model, preprocess, tokenizer, device = load_clip()
    prompt_embeddings = compute_text_embeddings(model, tokenizer, device, prompts)

    session = requests.Session()
    image_records = []
    phash_groups = defaultdict(list)

    print("Fetching product images...")
    for product in filtered:
        product_gid = product.get("id")
        product_id = gid_to_numeric(product_gid)
        if not product_id:
            continue
        images = fetch_product_images(session, shop_domain, args.api_version, access_token, product_id)
        for img in images:
            src = img.get("src")
            if not src:
                continue
            image_id = img.get("id")
            filename = os.path.basename(urlparse(src).path) or f"{image_id}.jpg"
            product_folder = ensure_dir(os.path.join(images_dir, str(product_id)))
            local_path = os.path.join(product_folder, filename)

            if not download_image(session, src, local_path):
                continue

            sha = compute_sha256(local_path)

            try:
                pil_image = Image.open(local_path).convert("RGB")
                phash = str(imagehash.phash(pil_image, hash_size=args.phash_size))
            except Exception:
                phash = None

            record = {
                "product_id": product_id,
                "product_gid": product_gid,
                "product_handle": product.get("handle"),
                "product_title": product.get("title"),
                "image_id": image_id,
                "src": src,
                "alt": img.get("alt"),
                "position": img.get("position"),
                "variant_ids": img.get("variant_ids") or [],
                "local_path": local_path,
                "sha256": sha,
                "phash": phash,
            }
            image_records.append(record)
            if phash:
                phash_groups[phash].append(record)

    if not image_records:
        print("No images found.")
        return

    print(f"Downloaded {len(image_records)} images across {len(filtered)} products.")

    # Embedding cache
    embeddings_index_path = os.path.join(cache_dir, "embeddings_index.json")
    embeddings_path = os.path.join(cache_dir, "embeddings.npy")
    embedding_index = {}
    embeddings = []

    if os.path.exists(embeddings_index_path) and os.path.exists(embeddings_path):
        with open(embeddings_index_path, "r", encoding="utf-8") as f:
            embedding_index = json.load(f)
        embeddings = list(np.load(embeddings_path))

    def store_embedding(phash, vector):
        embedding_index[phash] = len(embeddings)
        embeddings.append(vector)

    print("Computing CLIP embeddings...")
    for phash, records in phash_groups.items():
        if phash in embedding_index:
            continue
        sample_path = records[0]["local_path"]
        try:
            emb = compute_image_embedding(model, preprocess, device, sample_path)
            store_embedding(phash, emb)
        except Exception as e:
            print(f"  Embedding failed for {sample_path}: {e}")

    np.save(embeddings_path, np.array(embeddings))
    with open(embeddings_index_path, "w", encoding="utf-8") as f:
        json.dump(embedding_index, f, indent=2)

    # Build matrix for clustering
    phashes = [p for p in phash_groups.keys() if p in embedding_index]
    if not phashes:
        print("No embeddings available for clustering.")
        return

    vectors = np.array([embeddings[embedding_index[p]] for p in phashes])

    print("Clustering embeddings...")
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=args.cluster_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(vectors)

    cluster_map = defaultdict(list)
    for phash, label in zip(phashes, labels):
        cluster_map[int(label)].append(phash)

    cluster_summaries = []
    for cluster_id, phash_list in cluster_map.items():
        cluster_vectors = np.array([embeddings[embedding_index[p]] for p in phash_list])
        cluster_vec = cluster_vectors.mean(axis=0)
        scores = cosine_similarity(cluster_vec, prompt_embeddings)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        if best_score >= args.score_threshold:
            label = short_labels[best_idx]
            label_prompt = prompts[best_idx]
        else:
            label = "unclassified_outlier"
            label_prompt = "unclassified_outlier"

        top_indices = np.argsort(scores)[::-1][:3]
        top_labels = [
            {
                "label": short_labels[i],
                "prompt": prompts[i],
                "score": float(scores[i]),
            }
            for i in top_indices
        ]

        products_covered = set()
        for phash in phash_list:
            for rec in phash_groups[phash]:
                products_covered.add(rec["product_id"])

        cluster_summaries.append({
            "cluster_id": cluster_id,
            "label": label,
            "label_prompt": label_prompt,
            "score": best_score,
            "top_labels": top_labels,
            "phashes": phash_list,
            "products_covered": sorted(products_covered),
            "coverage": len(products_covered),
        })

    cluster_summaries.sort(key=lambda x: (-x["coverage"], x["cluster_id"]))

    # Build thumbnails + report
    print("Generating audit report...")
    thumb_map = {}
    for cluster in cluster_summaries:
        cluster_thumbs = []
        for phash in cluster["phashes"][: args.max_thumbs]:
            record = phash_groups[phash][0]
            thumb_name = f"{phash}.jpg"
            thumb_path = os.path.join(thumbs_dir, thumb_name)
            build_thumbnail(record["local_path"], thumb_path)
            cluster_thumbs.append(os.path.relpath(thumb_path, os.path.dirname(report_path)))
        thumb_map[cluster["cluster_id"]] = cluster_thumbs

    report = []
    report.append("<html><head><meta charset='utf-8'><title>SVSE Audit Report</title>")
    report.append("<style>")
    report.append("body{font-family:Arial,sans-serif;margin:20px;color:#111;}")
    report.append(".cluster{border:1px solid #ddd;padding:12px;margin-bottom:16px;border-radius:8px;}")
    report.append(".thumbs img{width:120px;height:120px;object-fit:cover;margin-right:8px;border:1px solid #ccc;}")
    report.append(".meta{font-size:12px;color:#444;}")
    report.append("</style></head><body>")
    report.append(f"<h1>SVSE Audit Report</h1>")
    report.append(f"<p>Generated: {datetime.now().isoformat()}</p>")
    report.append(f"<p>Reference: {ref_title}</p>")
    report.append(f"<p>Matched products: {len(filtered)}</p>")
    report.append("<hr/>")

    for cluster in cluster_summaries:
        thumbs = thumb_map.get(cluster["cluster_id"], [])
        report.append("<div class='cluster'>")
        report.append(f"<h3>Cluster {cluster['cluster_id']} - Coverage {cluster['coverage']}/{len(filtered)}</h3>")
        report.append(f"<div class='meta'>Label: {cluster['label']} (score {cluster['score']:.2f})</div>")
        if cluster.get("label_prompt"):
            report.append(f"<div class='meta'>Prompt: {cluster['label_prompt']}</div>")
        if cluster.get("top_labels"):
            top_preview = ", ".join(
                f"{item['label']} ({item['score']:.2f})" for item in cluster["top_labels"]
            )
            report.append(f"<div class='meta'>Top matches: {top_preview}</div>")
        coverage_list = [product_lookup.get(pid, str(pid)) for pid in cluster["products_covered"]]
        if coverage_list:
            report.append("<div class='meta'>Coverage:</div>")
            report.append("<div class='meta'>" + ", ".join(coverage_list) + "</div>")
        report.append("<div class='thumbs'>")
        for thumb in thumbs:
            report.append(f"<img src='{thumb}' />")
        report.append("</div>")
        report.append("</div>")

    report.append("</body></html>")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "reference": ref_product,
        "matched_products": filtered,
        "image_records": image_records,
        "clusters": cluster_summaries,
    }
    with open(os.path.join(cache_dir, "audit_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    config = {
        "reference_title": ref_title,
        "reference_handle": ref_product.get("handle"),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "label_set": args.label_set,
        "label_prompts": prompts,
        "short_labels": short_labels,
        "cluster_overrides": {
            str(c["cluster_id"]): {
                "label": c["label"],
                "label_prompt": c.get("label_prompt"),
                "score": c["score"],
                "shot_type": c["label"],
                "notes": "",
            }
            for c in cluster_summaries
        },
    }
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False)

    print(f"Audit report written to: {report_path}")
    print(f"Manifest written to: {os.path.join(cache_dir, 'audit_manifest.json')}")
    print(f"Config scaffold written to: {config_path}")


if __name__ == "__main__":
    main()
