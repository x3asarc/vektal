import os
import yaml


def load_rules(rules_path=None):
    if rules_path is None:
        from src.core.paths import PRODUCT_QUALITY_RULES_PATH
        rules_path = PRODUCT_QUALITY_RULES_PATH

    if not os.path.exists(rules_path):
        return {}

    with open(rules_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def evaluate_quality(product, scraped=None, rules=None):
    product = product or {}
    scraped = scraped or {}
    rules = rules or load_rules()

    required = (rules.get("required_fields") or {})
    vendor_rules = (rules.get("vendor_rules") or {})

    vendor_name = (product.get("vendor") or "").strip()
    vendor_overrides = vendor_rules.get(vendor_name, {}) if vendor_name else {}

    # Normalize fields
    primary_variant = product.get("primary_variant") or {}
    images = product.get("media") or product.get("images") or []

    fields = {
        "sku": primary_variant.get("sku"),
        "barcode": primary_variant.get("barcode"),
        "country_of_origin": primary_variant.get("inventory_country"),
        "hs_code": primary_variant.get("inventory_hs_code"),
        "weight": primary_variant.get("weight"),
        "vendor": product.get("vendor"),
        "product_type": product.get("product_type"),
        "title": product.get("title"),
        "description_html": product.get("description_html"),
        "images": images,
        "seo_title": product.get("seo_title"),
        "seo_description": product.get("seo_description"),
        "tags": product.get("tags"),
        "collections": product.get("collections"),
    }

    missing_required = []
    suggested_repairs = []

    for field_key, meta in required.items():
        required_flag = meta.get("required", False)
        if not required_flag:
            continue

        min_count = meta.get("min_count") or vendor_overrides.get(field_key, {}).get("min_count")

        value = fields.get(field_key)
        missing = False

        if field_key == "images":
            count = len(value) if value else 0
            if min_count and count < min_count:
                missing = True
        elif field_key in ("tags", "collections"):
            count = len(value) if value else 0
            if min_count and count < min_count:
                missing = True
        else:
            if value in (None, "", []):
                missing = True

        if missing:
            missing_required.append(field_key)
            repair_script = meta.get("repair_script")
            repair_args = meta.get("repair_args")
            if repair_script:
                suggested_repairs.append({
                    "field": field_key,
                    "description": meta.get("description"),
                    "script": repair_script,
                    "args": repair_args,
                })

    return {
        "missing_required": missing_required,
        "suggested_repairs": suggested_repairs,
        "vendor": vendor_name,
    }
