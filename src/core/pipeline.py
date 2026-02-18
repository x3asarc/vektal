import uuid
from datetime import datetime

from src.core.shopify_resolver import ShopifyResolver
from src.core.diff_engine import build_diff_and_plan
from src.core.scrape_engine import scrape_missing_fields
from src.core.shopify_apply import apply_payload
from src.core.quality_assessor import evaluate_quality
from src.core.hs_code_resolver import resolve_hs_code
from src.core.seo_engine import generate_seo_fields
from src.core.vision_engine import generate_vision_alt_text, generate_vision_metadata
from src.core.image_framework import get_framework


def build_payload(identifier, product, scraped, diff, apply_plan, mode="cli"):
    run_id = str(uuid.uuid4())
    payload = {
        "run_id": run_id,
        "mode": mode,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "input": {
            "kind": identifier.get("kind"),
            "value": identifier.get("value"),
        },
        "product": product,
        "diff": diff,
        "scrape": {
            "sources": [],
            "results": scraped,
            "not_found": False,
        },
        "apply_plan": apply_plan,
        "approve": {
            "finalized": False,
            "approved_by": None,
            "approved_at": None,
        },
        "errors": [],
    }
    return payload


def process_identifier(identifier, mode="cli", context=None):
    context = context or {}
    resolver = context.get("resolver") or ShopifyResolver(
        shop_domain=context.get("shop_domain"),
        access_token=context.get("access_token"),
        api_version=context.get("api_version"),
    )

    resolved = resolver.resolve_identifier(identifier)
    matches = resolved.get("matches", [])

    if not matches:
        payload = build_payload(identifier, None, {}, {}, {}, mode=mode)
        payload["errors"].append("no product found")
        return payload

    # Get corrections from analyzer (if present in context)
    corrections = context.get("corrections", [])

    if len(matches) > 1:
        scraped = {}
        if identifier.get("kind") in ("sku", "ean"):
            # Vendor lookup hint when SKU/EAN resolves to multiple products
            try:
                scraped = scrape_missing_fields(
                    identifier, 
                    product=matches[0], 
                    vendor=matches[0].get("vendor"),
                    corrections=corrections
                )
            except Exception:
                scraped = {}

        payload = build_payload(identifier, None, scraped, {}, {}, mode=mode)
        payload["errors"].append("multiple products found")
        payload["candidates"] = matches
        return payload

    product = matches[0]

    scraped = scrape_missing_fields(
        identifier, 
        product=product, 
        vendor=product.get("vendor"),
        corrections=corrections
    )

    # Image Framework: Comprehensive image processing with all rules codified
    # Handles: vision AI, hybrid naming, transformations, upload strategy, positioning
    if scraped.get("image_url"):
        try:
            framework = get_framework()
            image_result = framework.process_image(
                product=product,
                image_url=scraped["image_url"],
                image_role="primary",  # Default to primary for main pipeline
                vendor=product.get("vendor")
            )

            # Store framework results in scraped data
            scraped["image_type"] = image_result["image_type"]
            scraped["suggested_filename"] = image_result["filename"]
            scraped["alt_text"] = image_result["alt_text"]
            scraped["image_transformations"] = image_result["transformations"]
            scraped["image_upload_strategy"] = image_result["upload_strategy"]
            scraped["image_position"] = image_result["position"]
            scraped["image_framework_metadata"] = image_result["metadata"]

        except Exception as e:
            # Fallback to legacy vision_metadata if framework fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Image framework failed, using fallback: {e}")

            vision_metadata = generate_vision_metadata(product, scraped, vendor=product.get("vendor"))
            if vision_metadata:
                scraped["alt_text"] = vision_metadata.get("alt_text")
                if vision_metadata.get("image_type"):
                    scraped["image_type"] = vision_metadata["image_type"]
                if vision_metadata.get("filename"):
                    scraped["suggested_filename"] = vision_metadata["filename"]

    seo_fields, seo_meta = generate_seo_fields(product, scraped, model_id=context.get("seo_model_id"))
    if seo_fields:
        for key, value in seo_fields.items():
            if scraped.get(key) in (None, "", []):
                scraped[key] = value
    if seo_meta:
        scraped["seo_fallback"] = seo_meta.get("fallback")
        scraped["seo_error"] = seo_meta.get("error")
    diff, apply_plan = build_diff_and_plan(product, scraped, mode=mode)

    payload = build_payload(identifier, product, scraped, diff, apply_plan, mode=mode)
    if seo_meta:
        payload["seo_generation"] = seo_meta
    payload["quality"] = evaluate_quality(product, scraped)

    hs_candidate = resolve_hs_code(product, resolver)
    if hs_candidate:
        payload["diff"].setdefault("requires_approval", {})["hs_code_change"] = {
            "proposed_hs_code": hs_candidate.get("hs_code"),
            "confidence": hs_candidate.get("confidence"),
            "source": hs_candidate.get("source"),
            "approved": False,
        }
    return payload


def apply_payload_with_context(payload, context=None):
    context = context or {}
    return apply_payload(payload, context=context)


def process_with_product(identifier, product, mode="cli", context=None):
    context = context or {}
    resolver = context.get("resolver") or ShopifyResolver(
        shop_domain=context.get("shop_domain"),
        access_token=context.get("access_token"),
        api_version=context.get("api_version"),
    )
    
    # Get corrections from analyzer (if present in context)
    corrections = context.get("corrections", [])

    scraped = scrape_missing_fields(
        identifier, 
        product=product, 
        vendor=product.get("vendor"),
        corrections=corrections
    )
    seo_fields, seo_meta = generate_seo_fields(product, scraped, model_id=context.get("seo_model_id"))
    if seo_fields:
        for key, value in seo_fields.items():
            if scraped.get(key) in (None, "", []):
                scraped[key] = value
    if seo_meta:
        scraped["seo_fallback"] = seo_meta.get("fallback")
        scraped["seo_error"] = seo_meta.get("error")
    diff, apply_plan = build_diff_and_plan(product, scraped, mode=mode)
    payload = build_payload(identifier, product, scraped, diff, apply_plan, mode=mode)
    if seo_meta:
        payload["seo_generation"] = seo_meta
    payload["quality"] = evaluate_quality(product, scraped)

    hs_candidate = resolve_hs_code(product, resolver)
    if hs_candidate:
        payload["diff"].setdefault("requires_approval", {})["hs_code_change"] = {
            "proposed_hs_code": hs_candidate.get("hs_code"),
            "confidence": hs_candidate.get("confidence"),
            "source": hs_candidate.get("source"),
            "approved": False,
        }
    return payload
