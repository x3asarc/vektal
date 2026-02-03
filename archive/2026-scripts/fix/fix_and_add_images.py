"""
Fix SKU/barcode AND add supplier images for 3 Pentart products
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.shopify_resolver import ShopifyResolver
from src.core.pipeline import process_identifier, apply_payload_with_context
from src.core.product_analyzer import ProductAnalyzer

# Barcodes (currently incorrectly stored in SKU field)
BARCODES = [
    "5996546033389",  # Harztönung Jade 20 ml -> actual SKU: 40070
    "5997412742664",  # Dekofolie Bronze
    "5997412709667",  # Textilkleber 80 ml
]

def auto_approve_all_with_corrections(payload, corrections):
    """Auto-approve all changes including analyzer corrections"""
    diff = payload.get("diff", {})
    apply_plan = payload.get("apply_plan", {})

    # Apply analyzer corrections (SKU/barcode fixes)
    if corrections:
        print(f"  Applying {len(corrections)} corrections:")
        for correction in corrections:
            corr_type = correction.get("type")
            field = correction.get("field")
            proposed = correction.get("proposed")

            print(f"    - {corr_type}: {field} -> {proposed}")

            if field == "sku":
                apply_plan.setdefault("update_variants", {})
                apply_plan["update_variants"]["sku"] = proposed
            elif field == "barcode":
                apply_plan.setdefault("update_variants", {})
                apply_plan["update_variants"]["barcode"] = proposed

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

    # Auto-approve image replace/add
    image_req = diff.get("requires_approval", {}).get("image_replace", {})
    if image_req.get("status") == "needs_approval":
        image_req["approved"] = True
        # Enable image upload
        if apply_plan.get("update_images"):
            apply_plan["update_images"]["action"] = "replace"

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

def process_barcode(barcode, resolver, context):
    """Process a product by barcode, fixing SKU and adding images"""
    print(f"\n{'='*70}")
    print(f"Processing Barcode: {barcode}")
    print(f"{'='*70}")

    identifier = {"kind": "sku", "value": barcode}  # Using SKU kind since barcode is stored in SKU field

    try:
        # Step 1: Analyze product to detect SKU/barcode issues
        print("\n1. Analyzing product...")

        resolve_result = resolver.resolve_identifier(identifier)
        matches = resolve_result.get("matches", [])

        if not matches:
            print(f"  ERROR Product not found")
            return False

        product = matches[0]
        print(f"  OK Found: {product.get('title')}")
        print(f"  Handle: {product.get('handle')}")

        # Run analyzer to detect SKU/barcode mismatch
        analyzer = ProductAnalyzer(context)
        analysis = analyzer.analyze(product, identifier, product.get("vendor"))

        corrections = []
        if analysis.has_issues():
            corrections = analysis.corrections
            print(f"\n2. Issues detected - {len(corrections)} corrections will be applied")

        # Step 2: Process through pipeline with corrections
        print(f"\n3. Processing through pipeline...")
        context["corrections"] = corrections

        payload = process_identifier(identifier, mode="cli", context=context)

        if payload.get("errors"):
            print(f"  ERROR Errors: {', '.join(payload['errors'])}")
            return False

        # Check if images were scraped
        scraped = payload.get("scrape", {}).get("results", {})
        image_url = scraped.get("image_url")

        print(f"\n4. Image status:")
        if image_url:
            print(f"  OK Supplier image found: {image_url[:80]}...")
        else:
            print(f"  WARNING No supplier image found")

        # Step 3: Auto-approve all changes
        print(f"\n5. Auto-approving all changes...")
        payload = auto_approve_all_with_corrections(payload, corrections)

        # Step 4: Apply changes
        print(f"\n6. Applying changes to Shopify...")
        apply_result = apply_payload_with_context(payload, context=context)

        if apply_result:
            print(f"\nOK Successfully updated {barcode}")
            print(f"  - SKU fixed: {corrections[0].get('proposed') if corrections else 'N/A'}")
            print(f"  - Image: {'Added' if image_url else 'Not found'}")
            return True
        else:
            print(f"\nWARNING No changes applied for {barcode}")
            return False

    except Exception as e:
        print(f"\nERROR Error processing {barcode}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("FIX SKU/BARCODE + ADD SUPPLIER IMAGES")
    print("3 Pentart Products")
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
    for barcode in BARCODES:
        result = process_barcode(barcode, resolver, context)
        results.append((barcode, result))

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    for barcode, result in results:
        status = "OK SUCCESS" if result else ("ERROR FAILED" if result is False else "WARNING SKIPPED")
        print(f"{barcode}: {status}")

    successful = sum(1 for _, r in results if r is True)
    print(f"\n{successful}/{len(BARCODES)} products updated successfully")

    print(f"\n{'='*70}")
    print("COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
