"""
Update three resin tint products with auto-approval
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver
from src.core.pipeline import process_identifier, apply_payload_with_context

# SKUs to process
SKUS = [
    "5996546033389",  # Harztönung Jade 20 ml
    "5997412742664",  # Unknown - will discover
    "5997412709667",  # Unknown - will discover
]

def auto_approve_all(payload):
    """Auto-approve all changes in the payload"""
    diff = payload.get("diff", {})
    apply_plan = payload.get("apply_plan", {})

    # Auto-approve title change
    title_req = diff.get("requires_approval", {}).get("title_change", {})
    if title_req.get("proposed_title"):
        title_req["approved"] = True
        apply_plan.setdefault("update_fields", {})
        apply_plan["update_fields"]["title"] = title_req.get("proposed_title")

    # Auto-approve SEO changes
    seo_req = diff.get("requires_approval", {}).get("seo_change", {})
    if seo_req.get("proposed_fields"):
        seo_req["approved"] = True
        apply_plan.setdefault("update_fields", {})
        for key, value in (seo_req.get("proposed_fields") or {}).items():
            apply_plan["update_fields"][key] = value

    # Auto-approve image replace
    image_req = diff.get("requires_approval", {}).get("image_replace", {})
    if image_req.get("status") == "needs_approval":
        image_req["approved"] = True

    # Auto-approve handle change
    handle_req = diff.get("requires_approval", {}).get("handle_change", {})
    if handle_req.get("proposed_handle"):
        handle_req["approved"] = True
        apply_plan["update_handle"]["enabled"] = True
        for redirect in apply_plan.get("create_redirects", []):
            redirect["enabled"] = True

    # Auto-approve HS code
    hs_req = diff.get("requires_approval", {}).get("hs_code_change", {})
    if hs_req.get("proposed_hs_code"):
        hs_req["approved"] = True
        apply_plan.setdefault("update_inventory", {})
        apply_plan["update_inventory"]["harmonized_system_code"] = hs_req.get("proposed_hs_code")

    payload["apply_plan"] = apply_plan
    return payload

def process_sku(sku, resolver, context):
    """Process a single SKU"""
    print(f"\n{'='*70}")
    print(f"Processing SKU: {sku}")
    print(f"{'='*70}")

    identifier = {"kind": "sku", "value": sku}

    # Add corrections to fix SKU/EAN mismatches automatically
    # The analyzer will detect if SKU is actually an EAN and propose corrections
    context["corrections"] = []  # We'll handle this in the pipeline

    try:
        # Process through pipeline
        payload = process_identifier(identifier, mode="cli", context=context)

        if payload.get("errors"):
            print(f"ERROR: {', '.join(payload['errors'])}")
            return None

        product = payload.get("product", {})
        print(f"Product: {product.get('title')}")
        print(f"Handle: {product.get('handle')}")

        # Auto-approve all changes
        payload = auto_approve_all(payload)

        # Apply changes
        print("Applying changes...")
        apply_result = apply_payload_with_context(payload, context=context)

        if apply_result:
            print(f"✓ Successfully updated {sku}")
            return True
        else:
            print(f"⚠ No changes applied for {sku}")
            return False

    except Exception as e:
        print(f"✗ Error processing {sku}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("UPDATING THREE RESIN TINT PRODUCTS")
    print("="*70)

    # Initialize resolver
    print("\nInitializing Shopify client...")
    resolver = ShopifyResolver()

    context = {
        "resolver": resolver,
        "shop_domain": resolver.shop_domain,
        "access_token": resolver.client.access_token,
        "api_version": resolver.api_version,
    }

    results = []
    for sku in SKUS:
        result = process_sku(sku, resolver, context)
        results.append((sku, result))

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for sku, result in results:
        status = "✓ SUCCESS" if result else ("✗ FAILED" if result is False else "⚠ SKIPPED")
        print(f"{sku}: {status}")

    print(f"\n{'='*70}")
    print("ALL PRODUCTS PROCESSED")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
