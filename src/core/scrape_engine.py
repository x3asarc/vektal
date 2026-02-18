import os
import importlib.util

import re

from src.core.image_scraper import scrape_product_info, DEFAULT_COUNTRY_OF_ORIGIN


def _load_v4_fallback():
    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
        "not_found_finder_v4_optimized.py",
    )
    if not os.path.exists(script_path):
        return None

    spec = importlib.util.spec_from_file_location("not_found_finder_v4_optimized", script_path)
    if not spec or not spec.loader:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _try_pentart_db(sku=None, ean=None, db_path=None, include_title=False):
    """
    Lookup product in Pentart database.
    
    Args:
        sku: Article number to search for
        ean: EAN barcode to search for
        db_path: Optional path to database file
        include_title: If True, include DB description as title (for corrections)
        
    Returns:
        Dictionary with product data from Pentart DB
    """
    try:
        from utils.pentart_db import PentartDatabase
    except Exception:
        return {}

    try:
        db = PentartDatabase(db_path)
    except Exception:
        return {}

    record = None
    if ean:
        record = db.get_by_ean(ean)
    if not record and sku:
        record = db.get_by_article_number(sku)

    if not record:
        return {}

    result = {
        "scraped_sku": record.get("ean"),
        "sku": record.get("article_number"),
        "weight": record.get("product_weight"),
        "country": "HU",
    }
    
    # Include title when corrections require it
    if include_title:
        result["title"] = record.get("description")
    
    return result


def scrape_missing_fields(identifier, product=None, vendor=None, corrections=None):
    """
    Scrape missing fields for a product.
    
    Args:
        identifier: {"kind": "sku"|"ean"|"handle", "value": "..."}
        product: Normalized Shopify product data
        vendor: Product vendor override
        corrections: List of corrections from ProductAnalyzer to apply
        
    Returns:
        Dictionary with scraped data
    """
    sku = None
    ean = None
    corrections = corrections or []

    if identifier.get("kind") in ("sku", "ean"):
        if identifier.get("kind") == "sku":
            sku = identifier.get("value")
        else:
            ean = identifier.get("value")

    if not sku and product:
        sku = (product.get("primary_variant") or {}).get("sku")
    if not ean and product:
        ean = (product.get("primary_variant") or {}).get("barcode")
    if not sku:
        sku = identifier.get("value")

    vendor = vendor or (product.get("vendor") if product else None)
    vendor_lower = (vendor or "").lower()
    is_pentart = "pentart" in vendor_lower
    
    # Check if corrections require title from DB
    needs_title = any(c.get("type") == "title_fix" for c in corrections)

    scraped = {}

    # Pentart database enrichment
    if is_pentart:
        scraped.update(_try_pentart_db(sku=sku, ean=ean, include_title=needs_title))
    
    # Apply SKU corrections from analyzer
    for correction in corrections:
        if correction.get("type") == "sku_fix" and correction.get("value"):
            scraped["sku"] = correction.get("value")
        if correction.get("type") == "title_fix" and correction.get("value"):
            scraped["title"] = correction.get("value")

    try:
        base_scrape = scrape_product_info(sku, vendor) or {}
        scraped = _merge_scrape(scraped, base_scrape)
    except Exception:
        pass

    # Fallback to v4 optimized search if image_url missing
    if not scraped.get("image_url"):
        module = _load_v4_fallback()
        if module and hasattr(module, "optimized_sku_search"):
            try:
                handle = product.get("handle") if product else None
                result = module.optimized_sku_search(sku, handle, vendor)
                if result:
                    if is_pentart:
                        # Ignore HS code values from local Pentart context
                        result.pop("hs_code", None)
                    scraped = _merge_scrape(scraped, result)
            except Exception:
                pass

    # Drop placeholder titles from stub scrapers
    if _is_placeholder_title(scraped.get("title")):
        scraped["title"] = None

    # Do not keep HS code from Pentart local sources (unreliable)
    if is_pentart and scraped.get("hs_code"):
        scraped["hs_code"] = None
    if not scraped.get("country"):
        scraped["country"] = DEFAULT_COUNTRY_OF_ORIGIN

    return scraped


def _merge_scrape(primary, fallback):
    merged = dict(primary)
    for key, value in (fallback or {}).items():
        if merged.get(key) in (None, "", []):
            merged[key] = value
    return merged


def _is_placeholder_title(title):
    if not title:
        return False
    title = title.strip()
    lower = title.lower()
    if lower.startswith("product "):
        tail = lower.replace("product ", "", 1).strip()
        if tail.isdigit():
            return True
    return False
