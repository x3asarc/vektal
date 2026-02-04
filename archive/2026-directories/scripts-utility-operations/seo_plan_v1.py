import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from PIL import Image

from src.core.vision_client import VisionAIClient
from src.core.vision_cache import VisionAltTextCache, BudgetExceededError
from src.core.image_scraper import validate_alt_text


STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "for", "with", "in", "on", "to",
    "set", "pack", "pcs", "piece", "pieces", "x", "by",
}

COLOR_WORDS = {
    "black", "white", "red", "green", "blue", "yellow", "orange", "pink",
    "purple", "violet", "brown", "gray", "grey", "silver", "gold", "beige",
    "ivory", "turquoise", "navy", "teal",
}

UNIT_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?\s*(ml|l|g|kg|oz|lb|cm|mm|m|in|inch|inches)\b")
MULTIPACK_PATTERN = re.compile(r"\b\d+\s*[xX]\s*\d+\b")


def slugify(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def derive_base_name(title):
    if not title:
        return ""
    cleaned = title.lower()
    cleaned = MULTIPACK_PATTERN.sub(" ", cleaned)
    cleaned = UNIT_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    filtered = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token in COLOR_WORDS:
            continue
        if token.isdigit():
            continue
        if len(token) < 2:
            continue
        filtered.append(token)
    return slugify(" ".join(filtered))

def derive_base_name_with_units(title):
    if not title:
        return ""
    cleaned = title.lower()
    cleaned = MULTIPACK_PATTERN.sub(" ", cleaned)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    tokens = [t for t in re.split(r"\s+", cleaned) if t]
    filtered = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token in COLOR_WORDS:
            continue
        if len(token) < 2:
            continue
        filtered.append(token)
    return slugify(" ".join(filtered))

def derive_common_base_name(titles):
    cleaned = [derive_base_name_with_units(t) for t in titles if t]
    token_lists = [c.split("-") for c in cleaned if c]
    if not token_lists:
        return ""
    base = token_lists[0]
    common = [tok for tok in base if all(tok in tokens for tokens in token_lists[1:])]
    if not common:
        return "-".join(base)
    return "-".join(common)

def humanize_slug(slug):
    if not slug:
        return ""
    return slug.replace("-", " ").strip()


def derive_color(title):
    if not title:
        return ""
    lower = title.lower()
    for color in COLOR_WORDS:
        if color in lower:
            return slugify(color)
    return ""


def choose_canonical_record(records):
    best = None
    best_area = -1
    best_size = -1
    for rec in records:
        path = rec.get("local_path")
        if not path or not os.path.exists(path):
            continue
        try:
            with Image.open(path) as img:
                width, height = img.size
            area = width * height
        except Exception:
            area = 0
        size = os.path.getsize(path)
        if area > best_area or (area == best_area and size > best_size):
            best = rec
            best_area = area
            best_size = size
    return best


def build_filename(brand, base_name, color, shot_type, include_color=True):
    parts = [brand, base_name, color if include_color else "", shot_type]
    parts = [p for p in parts if p]
    if not parts:
        return ""
    return "-".join(parts) + ".jpg"


def format_alt(template, product_title, vendor, shot_type):
    return template.format(
        product_title=product_title,
        vendor=vendor,
        shot_type=shot_type,
    )


def format_alt_with_meta(template, product_title, vendor, shot_type, product_color="", product_handle=""):
    return template.format(
        product_title=product_title,
        vendor=vendor,
        shot_type=shot_type,
        product_color=product_color,
        product_handle=product_handle,
    )


def normalize_product_id(value):
    if value is None:
        return ""
    text = str(value)
    if "/" in text:
        text = text.split("/")[-1]
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="SVSE Phase B: build SEO naming + alt plan (dry-run).")
    parser.add_argument("--svse-root", help="Root folder created by audit_v3.py")
    parser.add_argument("--config", help="Path to config.yaml")
    parser.add_argument("--manifest", help="Path to audit_manifest.json")
    parser.add_argument("--output-dir", help="Output directory for reports")
    parser.add_argument("--brand", help="Override brand slug")
    parser.add_argument("--base-name", help="Override base product name slug")
    parser.add_argument("--color", help="Override color slug")
    parser.add_argument("--filename-template-primary", default="{brand}-{base_name}-{color}-{shot_type}.jpg")
    parser.add_argument("--filename-template-secondary", default="{brand}-{base_name}-{shot_type}.jpg")
    parser.add_argument("--alt-template-primary", default="{product_title} - {product_color} - {shot_type} - {vendor}")
    parser.add_argument("--alt-template-secondary", default="{product_title} - {shot_type} - {vendor}")
    parser.add_argument("--shared-alt-template", default="{product_family} - {shot_type} - {vendor}")
    parser.add_argument("--fallback-shot-type", default="detail")
    parser.add_argument("--ensure-unique-alt", action="store_true", default=True)
    parser.add_argument("--no-ensure-unique-alt", dest="ensure_unique_alt", action="store_false")
    parser.add_argument("--use-vision-alt", action="store_true", default=False,
                        help="Generate shared alt text once per cluster using Vision AI")
    parser.add_argument("--primary-shot-types",
                        default="packshot_white_bottle,packshot_white_jar,packshot_color_bg,packshot",
                        help="Comma-separated shot types treated as position 1")
    parser.add_argument("--auto-primary", action="store_true", default=True,
                        help="Auto-select a primary cluster if none match primary shot types")
    parser.add_argument("--no-auto-primary", dest="auto_primary", action="store_false")
    args = parser.parse_args()

    if not args.svse_root and not (args.config and args.manifest):
        print("Provide --svse-root or both --config and --manifest.")
        return

    root = Path(args.svse_root) if args.svse_root else Path(args.config).parent
    config_path = Path(args.config) if args.config else root / "config.yaml"
    manifest_path = Path(args.manifest) if args.manifest else root / "cache" / "audit_manifest.json"
    output_dir = Path(args.output_dir) if args.output_dir else root / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    reference = manifest.get("reference") or {}
    vendor = reference.get("vendor") or ""
    ref_title = config.get("reference_title") or reference.get("title") or ""

    brand = args.brand or config.get("brand") or slugify(vendor)
    base_name = args.base_name or config.get("base_name") or derive_base_name(ref_title)
    color = args.color or config.get("color") or derive_color(ref_title)
    shared_cache = VisionAltTextCache() if args.use_vision_alt else None
    shared_client = VisionAIClient() if args.use_vision_alt else None

    image_records = manifest.get("image_records", [])
    cluster_map = {c["cluster_id"]: c for c in manifest.get("clusters", [])}
    overrides = config.get("cluster_overrides", {})
    matched_products = manifest.get("matched_products", [])

    matched_index = {}
    for product in matched_products:
        pid = normalize_product_id(product.get("id"))
        if not pid:
            continue
        matched_index[pid] = {
            "product_title": product.get("title"),
            "product_handle": product.get("handle"),
        }

    phash_to_records = {}
    for rec in image_records:
        phash = rec.get("phash")
        if not phash:
            continue
        phash_to_records.setdefault(phash, []).append(rec)

    cluster_plan = []
    per_product = []

    primary_types = {slugify(s.strip()) for s in str(args.primary_shot_types).split(",") if s.strip()}
    cluster_meta = []

    for cluster_id, cluster in cluster_map.items():
        override = overrides.get(str(cluster_id), {})
        shot_type = override.get("shot_type") or cluster.get("label") or "unclassified_outlier"
        if shot_type == "unclassified_outlier":
            shot_type = args.fallback_shot_type
        shot_type = slugify(shot_type)

        packshot_score = 0
        packshot_label = None
        for item in cluster.get("top_labels", []) or []:
            label = item.get("label") or ""
            if label.startswith("packshot"):
                score = float(item.get("score") or 0)
                if score > packshot_score:
                    packshot_score = score
                    packshot_label = label

        cluster_meta.append({
            "cluster_id": cluster_id,
            "shot_type": shot_type,
            "coverage": cluster.get("coverage") or 0,
            "packshot_score": packshot_score,
            "packshot_label": packshot_label,
        })

    primary_cluster_id = None
    if cluster_meta:
        candidates = [c for c in cluster_meta if c["shot_type"] in primary_types]
        if not candidates and args.auto_primary:
            candidates = cluster_meta
        if candidates:
            candidates.sort(key=lambda c: (c["coverage"], c["packshot_score"], -c["cluster_id"]), reverse=True)
            primary_cluster_id = candidates[0]["cluster_id"]

    for cluster_id, cluster in cluster_map.items():
        meta = next((m for m in cluster_meta if m["cluster_id"] == cluster_id), {})
        shot_type = meta.get("shot_type") or "detail"
        is_primary = cluster_id == primary_cluster_id
        phashes = cluster.get("phashes", [])

        # Pick canonical image from any record in this cluster (best resolution)
        records = []
        for phash in phashes:
            records.extend(phash_to_records.get(phash, []))
        canonical = choose_canonical_record(records) if records else None

        products = []
        if is_primary:
            products = [normalize_product_id(p.get("id")) for p in matched_products]
        else:
            products = [normalize_product_id(pid) for pid in cluster.get("products_covered", [])]

        titles_for_cluster = []
        for product_id in products:
            title = matched_index.get(product_id, {}).get("product_title") or ref_title
            if title:
                titles_for_cluster.append(title)

        cluster_base_name = derive_common_base_name(titles_for_cluster) or base_name
        cluster_filename = build_filename(brand, cluster_base_name, color, shot_type, include_color=False)
        cluster_plan.append({
            "cluster_id": cluster_id,
            "shot_type": shot_type,
            "is_primary": is_primary,
            "label": cluster.get("label"),
            "score": cluster.get("score"),
            "packshot_score": meta.get("packshot_score") if meta else None,
            "coverage": cluster.get("coverage"),
            "canonical_src": canonical.get("src") if canonical else None,
            "canonical_local_path": canonical.get("local_path") if canonical else None,
            "proposed_filename": cluster_filename,
        })

        shared_alt = None
        if args.use_vision_alt and not is_primary and canonical and canonical.get("src"):
            common_title = humanize_slug(cluster_base_name)
            product_type = reference.get("product_type") or ""
            tags = reference.get("tags") or []
            cached_alt = shared_cache.get(canonical.get("src")) if shared_cache else None
            if cached_alt:
                shared_alt = cached_alt
            else:
                try:
                    shared_cache.ensure_within_budget()
                    alt_text = shared_client.generate_alt_text(
                        image_url=canonical.get("src"),
                        product_title=common_title or ref_title,
                        vendor=vendor,
                        product_type=product_type,
                        tags=tags,
                    )
                except BudgetExceededError:
                    alt_text = None
                if alt_text:
                    validated, _ = validate_alt_text(alt_text)
                    shared_alt = validated
                    shared_cache.set(
                        canonical.get("src"),
                        validated,
                        {
                            "title": common_title or ref_title,
                            "vendor": vendor,
                            "product_type": product_type,
                            "tags": tags,
                        },
                        shared_client.model,
                    )

        if not shared_alt and not is_primary:
            product_family = humanize_slug(cluster_base_name) or ref_title
            shared_alt = args.shared_alt_template.format(
                product_family=product_family,
                shot_type=shot_type,
                vendor=vendor,
            )

        for product_id in products:
            if not product_id:
                continue
            product_title = None
            product_handle = None
            present = False
            for rec in records:
                if normalize_product_id(rec.get("product_id")) == product_id:
                    product_title = rec.get("product_title")
                    product_handle = rec.get("product_handle")
                    present = True
                    break
            if not product_title:
                product_title = matched_index.get(product_id, {}).get("product_title") or ref_title
            if not product_handle:
                product_handle = matched_index.get(product_id, {}).get("product_handle") or ""
            product_color = derive_color(product_title)
            allow_duplicate_alt = False
            if is_primary:
                alt_template = args.alt_template_primary
                alt_text = format_alt_with_meta(
                    alt_template,
                    product_title,
                    vendor,
                    shot_type,
                    product_color=product_color if is_primary else "",
                    product_handle=product_handle or "",
                )
            else:
                alt_text = shared_alt
                allow_duplicate_alt = True

            if is_primary:
                per_product_base = derive_base_name_with_units(product_title) or base_name
                filename_shot = "" if shot_type == "detail" else shot_type
                filename = build_filename(brand, per_product_base, product_color, filename_shot, include_color=True)
            else:
                filename = cluster_filename

            per_product.append({
                "cluster_id": cluster_id,
                "product_id": product_id,
                "product_title": product_title,
                "product_handle": product_handle,
                "product_color": product_color,
                "is_primary": is_primary,
                "present": present,
                "action": "keep" if present else "add",
                "shot_type": shot_type,
                "proposed_alt": alt_text,
                "proposed_filename": filename,
                "allow_duplicate_alt": allow_duplicate_alt,
            })

    if args.ensure_unique_alt:
        alt_counts = {}
        for row in per_product:
            if row.get("allow_duplicate_alt"):
                continue
            alt = row.get("proposed_alt") or ""
            alt_counts[alt] = alt_counts.get(alt, 0) + 1
        for row in per_product:
            if row.get("allow_duplicate_alt"):
                continue
            alt = row.get("proposed_alt") or ""
            if alt and alt_counts.get(alt, 0) > 1:
                suffix = row.get("product_handle") or str(row.get("product_id"))
                row["proposed_alt"] = f"{alt} - {suffix}"

    cluster_json = output_dir / "seo_plan_clusters.json"
    cluster_csv = output_dir / "seo_plan_clusters.csv"
    per_product_json = output_dir / "seo_plan_per_product.json"
    per_product_csv = output_dir / "seo_plan_per_product.csv"

    cluster_json.write_text(json.dumps(cluster_plan, indent=2), encoding="utf-8")
    per_product_json.write_text(json.dumps(per_product, indent=2), encoding="utf-8")

    def write_csv(path, rows, headers):
        with open(path, "w", encoding="utf-8") as f:
            f.write(",".join(headers) + "\n")
            for row in rows:
                values = [str(row.get(h, "")).replace('"', '""') for h in headers]
                f.write(",".join(f"\"{v}\"" for v in values) + "\n")

    write_csv(cluster_csv, cluster_plan, [
        "cluster_id",
        "shot_type",
        "is_primary",
        "label",
        "score",
        "packshot_score",
        "coverage",
        "canonical_src",
        "canonical_local_path",
        "proposed_filename",
    ])
    write_csv(per_product_csv, per_product, [
        "cluster_id",
        "product_id",
        "product_title",
        "product_handle",
        "product_color",
        "is_primary",
        "present",
        "action",
        "shot_type",
        "proposed_alt",
        "proposed_filename",
    ])

    print(f"Cluster plan: {cluster_json}")
    print(f"Cluster CSV: {cluster_csv}")
    print(f"Per-product plan: {per_product_json}")
    print(f"Per-product CSV: {per_product_csv}")


if __name__ == "__main__":
    main()
