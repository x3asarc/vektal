import re


def slugify(text):
    if not text:
        return ""
    text = text.lower()
    text = text.replace("??", "ae").replace("??", "oe").replace("??", "ue").replace("??", "ss")
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text.strip("-")


def build_diff_and_plan(product, scraped, mode="cli"):
    fields_to_update = {}
    fields_to_scrape = []
    variant_updates = {}
    inventory_updates = {}

    def _is_placeholder_title(title):
        if not title:
            return False
        title = title.strip()
        lower = title.lower()
        if lower.startswith("product "):
            tail = lower.replace("product ", "", 1).strip()
            if tail.isdigit():
                return True
        return bool(re.match(r"^Product\\s+\\d+$", title))

    if not product:
        return {
            "fields_to_update": {},
            "fields_to_scrape": [],
            "requires_approval": {},
            "redirects_to_create": [],
        }, {
            "update_fields": {},
            "update_variants": {},
            "update_images": {"action": "skip"},
            "update_handle": {"enabled": False, "new_handle": None},
            "create_redirects": [],
            "update_inventory": {},
        }

    # Compute fields to update based on scraped data
    scraped_title = scraped.get("title")
    proposed_title = None
    if scraped_title and not _is_placeholder_title(scraped_title) and scraped_title != product.get("title"):
        proposed_title = scraped_title

    if scraped.get("tags"):
        tags = scraped.get("tags")
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        if tags and tags != product.get("tags"):
            fields_to_update["tags"] = tags

    if scraped.get("product_type") and scraped.get("product_type") != product.get("product_type"):
        fields_to_update["productType"] = scraped.get("product_type")

    seo_update = {}
    seo_fields = {}
    if scraped.get("seo_title") and scraped.get("seo_title") != product.get("seo_title"):
        seo_update["title"] = scraped.get("seo_title")
        seo_fields["seo_title"] = scraped.get("seo_title")
    if scraped.get("seo_description") and scraped.get("seo_description") != product.get("seo_description"):
        seo_update["description"] = scraped.get("seo_description")
        seo_fields["seo_description"] = scraped.get("seo_description")
    if scraped.get("description_html") and scraped.get("description_html") != product.get("description_html"):
        seo_fields["description_html"] = scraped.get("description_html")


    # Missing fields summary
    missing_fields = []
    current_fields = {
        "sku": (product.get("primary_variant") or {}).get("sku"),
        "barcode": (product.get("primary_variant") or {}).get("barcode"),
        "price": (product.get("primary_variant") or {}).get("price"),
        "weight": (product.get("primary_variant") or {}).get("weight"),
        "weight_unit": (product.get("primary_variant") or {}).get("weight_unit"),
        "description_html": product.get("description_html"),
        "seo_title": product.get("seo_title"),
        "seo_description": product.get("seo_description"),
        "hs_code": (product.get("primary_variant") or {}).get("inventory_hs_code"),
        "country": (product.get("primary_variant") or {}).get("inventory_country"),
    }

    for key, value in current_fields.items():
        if value in (None, "", []):
            missing_fields.append(key)
    # Variant updates
    if scraped.get("sku"):
        scraped_sku = str(scraped.get("sku"))
        current_sku = (product.get("primary_variant") or {}).get("sku")
        if scraped_sku and scraped_sku != current_sku:
            variant_updates["sku"] = scraped_sku

    if scraped.get("price") is not None:
        variant_updates["price"] = str(scraped.get("price"))

    if scraped.get("weight") is not None:
        current_weight = (product.get("primary_variant") or {}).get("weight")
        if current_weight is None or float(scraped.get("weight")) != float(current_weight):
            variant_updates["weight"] = float(scraped.get("weight"))

    # Treat scraped_sku as barcode if barcode missing or different
    if scraped.get("scraped_sku"):
        scraped_barcode = str(scraped.get("scraped_sku"))
        current_barcode = (product.get("primary_variant") or {}).get("barcode")
        if scraped_barcode and scraped_barcode != current_barcode:
            variant_updates["barcode"] = scraped_barcode

    # Inventory updates (country and HS code)
    if scraped.get("country"):
        current_country = (product.get("primary_variant") or {}).get("inventory_country")
        if not current_country or str(scraped.get("country")) != str(current_country):
            inventory_updates["country_code_of_origin"] = scraped.get("country")
    # HS code updates are approval-gated and handled by pipeline

    # Decide missing fields to scrape (best-effort)
    if not scraped.get("image_url") and not product.get("media"):
        fields_to_scrape.append("image_url")
    if not scraped.get("title") and not product.get("title"):
        fields_to_scrape.append("title")

    # Handle change proposal
    proposed_handle = None
    if proposed_title:
        proposed_handle = slugify(proposed_title)
        if proposed_handle == product.get("handle"):
            proposed_handle = None

    # Image policy
    image_url = scraped.get("image_url")
    image_count = len(product.get("media") or [])
    image_status = "skip"
    image_action = "skip"

    if image_url:
        if image_count == 0:
            image_status = "auto"
            image_action = "auto_add"
        else:
            image_status = "needs_approval"
            image_action = "replace"

    requires_approval = {
        "handle_change": {
            "proposed_handle": proposed_handle,
            "approved": False,
        },
        "title_change": {
            "proposed_title": proposed_title,
            "approved": False,
        },
        "image_replace": {
            "status": image_status,
            "current_image_1": (product.get("media") or [{}])[0].get("url") if image_count else None,
            "scraped_image_1": image_url,
            "approved": False,
            "apply_to_batch": False,
        },
    }

    if seo_update or seo_fields.get("description_html"):
        proposed_fields = {}
        if seo_update:
            proposed_fields["seo"] = seo_update
        if seo_fields.get("description_html"):
            proposed_fields["descriptionHtml"] = seo_fields.get("description_html")
        requires_approval["seo_change"] = {
            "proposed_fields": proposed_fields,
            "proposed_seo_title": seo_fields.get("seo_title"),
            "proposed_seo_description": seo_fields.get("seo_description"),
            "proposed_description_html": seo_fields.get("description_html"),
            "fallback": bool(scraped.get("seo_fallback")),
            "error": scraped.get("seo_error"),
            "approved": False,
        }

    redirects_to_create = []
    if proposed_handle:
        redirects_to_create.append({
            "from": f"/products/{product.get('handle')}",
            "to": f"/products/{proposed_handle}",
            "approved": False,
        })

    diff = {
        "fields_to_update": fields_to_update,
        "fields_to_scrape": fields_to_scrape,
        "requires_approval": requires_approval,
        "redirects_to_create": redirects_to_create,
        "missing_fields": missing_fields,
        "current_fields": current_fields,
    }

    apply_plan = {
        "update_fields": fields_to_update,
        "update_variants": variant_updates,
        "update_images": {
            "action": image_action,
            "target_position": 1,
            "source_url": image_url,
        },
        "update_handle": {
            "enabled": False,
            "new_handle": proposed_handle,
        },
        "create_redirects": [
            {"from": r["from"], "to": r["to"], "enabled": False} for r in redirects_to_create
        ],
        "update_inventory": inventory_updates,
    }

    return diff, apply_plan
