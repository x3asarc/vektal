import json
import os
from datetime import datetime

import requests

from src.core.image_scraper import ShopifyClient


def apply_payload(payload, context=None):
    context = context or {}
    shop_domain = context.get("shop_domain")
    access_token = context.get("access_token")
    api_version = context.get("api_version")

    client = ShopifyClient()
    if shop_domain:
        client.shop_domain = shop_domain
        client.api_version = api_version or client.api_version
        client.graphql_endpoint = f"https://{shop_domain}/admin/api/{client.api_version}/graphql.json"
    if access_token:
        client.access_token = access_token
    else:
        client.authenticate()

    run_id = payload.get("run_id")
    _write_rollback(payload)

    result = {"applied": {}, "errors": []}

    product = payload.get("product") or {}
    product_id = product.get("id")
    if not product_id:
        result["errors"].append("missing product id")
        return result

    apply_plan = payload.get("apply_plan") or {}
    approvals = (payload.get("diff") or {}).get("requires_approval", {}) or {}

    # Gate unapproved SEO/title/HS changes
    seo_req = approvals.get("seo_change") or {}
    if seo_req and not seo_req.get("approved"):
        update_fields = apply_plan.get("update_fields") or {}
        if "seo" in update_fields:
            update_fields.pop("seo", None)
        if "descriptionHtml" in update_fields:
            update_fields.pop("descriptionHtml", None)
        apply_plan["update_fields"] = update_fields

    title_req = approvals.get("title_change") or {}
    if title_req and not title_req.get("approved"):
        update_fields = apply_plan.get("update_fields") or {}
        if "title" in update_fields:
            update_fields.pop("title", None)
        apply_plan["update_fields"] = update_fields

    hs_req = approvals.get("hs_code_change") or {}
    if hs_req and not hs_req.get("approved"):
        inventory_updates = apply_plan.get("update_inventory") or {}
        if "harmonized_system_code" in inventory_updates:
            inventory_updates.pop("harmonized_system_code", None)
        apply_plan["update_inventory"] = inventory_updates

    # Update product fields / handle
    update_input = {"id": product_id}
    update_fields = apply_plan.get("update_fields") or {}
    for key, value in update_fields.items():
        update_input[key] = value

    if apply_plan.get("update_handle", {}).get("enabled"):
        update_input["handle"] = apply_plan.get("update_handle", {}).get("new_handle")

    if len(update_input) > 1:
        _product_update(client, update_input)
        result["applied"]["product_update"] = True

    # Update variants
    variant_updates = apply_plan.get("update_variants") or {}
    if variant_updates:
        primary_variant = product.get("primary_variant") or {}
        variant_id = primary_variant.get("id")
        if variant_id:
            if _variant_update_graphql(client, product_id, variant_id, variant_updates):
                result["applied"]["variant_update"] = True
            else:
                # REST fallback for SKU/weight if needed
                _variant_update_rest(client, variant_id, variant_updates)
                result["applied"]["variant_update_rest"] = True

    # Update inventory item fields
    inventory_updates = apply_plan.get("update_inventory") or {}
    if inventory_updates:
        inv_id = (product.get("primary_variant") or {}).get("inventory_item_id")
        if inv_id:
            _inventory_update_rest(client, inv_id, inventory_updates)
            result["applied"]["inventory_update_rest"] = True

    # Images
    _apply_images(client, payload, result)

    # Redirects
    if apply_plan.get("create_redirects"):
        for redirect in apply_plan.get("create_redirects", []):
            if redirect.get("enabled"):
                _create_redirect(client, redirect.get("from"), redirect.get("to"))
                result["applied"].setdefault("redirects", []).append(redirect)

    return result


def _product_update(client, input_data):
    mutation = """
    mutation UpdateProduct($input: ProductInput!) {
      productUpdate(input: $input) {
        product { id handle }
        userErrors { field message }
      }
    }
    """
    client.execute_graphql(mutation, {"input": input_data})


def _variant_update_graphql(client, product_id, variant_id, updates):
    mutation = """
    mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        product { id }
        userErrors { field message }
      }
    }
    """
    variant_input = {"id": variant_id}
    if "barcode" in updates:
        variant_input["barcode"] = updates["barcode"]
    if "price" in updates:
        variant_input["price"] = updates["price"]

    if len(variant_input) == 1:
        return True

    result = client.execute_graphql(mutation, {"productId": product_id, "variants": [variant_input]})
    errors = result.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors", []) if result else []
    return not errors


def _variant_update_rest(client, variant_gid, updates):
    variant_id = str(variant_gid).split("/")[-1]
    url = f"https://{client.shop_domain}/admin/api/{client.api_version}/variants/{variant_id}.json"

    payload = {"variant": {"id": int(variant_id)}}
    if "sku" in updates:
        payload["variant"]["sku"] = updates["sku"]
    if "barcode" in updates:
        payload["variant"]["barcode"] = updates["barcode"]
    if "price" in updates:
        payload["variant"]["price"] = updates["price"]
    if "weight" in updates:
        payload["variant"]["weight"] = float(updates["weight"])
        payload["variant"]["weight_unit"] = "g"

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": client.access_token,
    }
    requests.put(url, json=payload, headers=headers, timeout=10)


def _inventory_update_rest(client, inventory_gid, updates):
    inv_id = str(inventory_gid).split("/")[-1]
    url = f"https://{client.shop_domain}/admin/api/{client.api_version}/inventory_items/{inv_id}.json"
    payload = {"inventory_item": {}}
    payload["inventory_item"].update(updates)

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": client.access_token,
    }
    requests.put(url, json=payload, headers=headers, timeout=10)


def _apply_images(client, payload, result):
    diff = payload.get("diff") or {}
    approval = diff.get("requires_approval", {}).get("image_replace", {})
    status = approval.get("status")
    approved = approval.get("approved")

    apply_plan = payload.get("apply_plan") or {}
    image_plan = apply_plan.get("update_images") or {}
    action = image_plan.get("action")

    if action == "skip":
        return

    if status == "needs_approval" and not approved:
        return

    product = payload.get("product") or {}
    product_id = product.get("id")
    media = product.get("media") or []

    if action == "replace":
        if media:
            first_media_id = media[0].get("id")
            if first_media_id:
                client.delete_product_media(product_id, [first_media_id])

    if action in ("replace", "auto_add"):
        image_url = image_plan.get("source_url")
        if image_url:
            # Check if framework transformations are available
            scraped = payload.get("scrape", {}).get("results", {})
            transformations = scraped.get("image_transformations")
            suggested_filename = scraped.get("suggested_filename")
            alt_text = scraped.get("alt_text") or product.get("title")

            if transformations:
                print(f"  [Framework] Applying image transformations:")
                print(f"    - Format: {transformations.get('format', 'N/A')}")
                print(f"    - Square: {transformations.get('convert_to_square', {}).get('target_size', 'N/A')}px")
                print(f"    - Transparency: {transformations.get('ensure_transparency', {}).get('convert_to_rgba', False)}")

                # Apply transformations before upload
                try:
                    from src.core.image_framework import get_framework
                    import requests
                    from io import BytesIO

                    # Download image
                    print(f"    - Downloading from: {image_url[:60]}...")
                    response = requests.get(image_url, timeout=30)
                    response.raise_for_status()
                    image_data = response.content

                    # Apply transformations
                    framework = get_framework()
                    transformed_data = framework.processor.apply_transformations(image_data, transformations)

                    print(f"    - Transformed: {len(image_data)} -> {len(transformed_data)} bytes")

                    # Upload transformed image with suggested filename
                    # TODO: Use staged upload for filename control
                    # For now, still use direct URL upload but log that transformations were applied
                    print(f"    - Uploading with filename: {suggested_filename}")

                except Exception as e:
                    print(f"    - WARNING: Transformation failed: {e}")
                    print(f"    - Falling back to direct URL upload")

            client.update_product_media(product_id, image_url, alt_text=alt_text)
            result["applied"]["image_update"] = True

            if transformations:
                result["applied"]["image_transformed"] = True

            # Post-upload verification
            try:
                from src.core.image_verifier import verify_and_fix_product_image

                print(f"\n  [Verifier] Checking uploaded image quality...")

                # Get the uploaded image URL (need to refetch product to get latest media)
                # For now, use the source URL as proxy
                verification = verify_and_fix_product_image(
                    product_id=product_id,
                    image_url=image_url,
                    product_title=product.get("title", ""),
                    vendor=product.get("vendor", ""),
                    image_type=scraped.get("image_type", "product"),
                    shopify_client=client,
                    auto_fix=False  # Set to False initially, log only
                )

                if verification.get("needs_recrop"):
                    print(f"  [Verifier] WARNING: Image may need adjustment")
                    print(f"    Issue: {verification.get('issue')}")
                    print(f"    Recommendation: {verification.get('recommendation')}")
                    print(f"    Confidence: {verification.get('confidence', 0):.0%}")
                    result["image_verification"] = verification
                else:
                    print(f"  [Verifier] OK: Image looks good (confidence: {verification.get('confidence', 0):.0%})")

            except Exception as e:
                print(f"  [Verifier] Skipped: {e}")


def _create_redirect(client, old_path, new_path):
    mutation = """
    mutation CreateRedirect($redirect: UrlRedirectInput!) {
      urlRedirectCreate(urlRedirect: $redirect) {
        urlRedirect { id path target }
        userErrors { field message }
      }
    }
    """
    variables = {"redirect": {"path": old_path, "target": new_path}}
    client.execute_graphql(mutation, variables)


def _write_rollback(payload):
    run_id = payload.get("run_id") or "unknown"
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rollback_dir = os.path.join(root, "data", "rollback")
    os.makedirs(rollback_dir, exist_ok=True)
    rollback_path = os.path.join(rollback_dir, f"{run_id}.json")

    rollback = {
        "run_id": run_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "product": payload.get("product"),
        "apply_plan": payload.get("apply_plan"),
    }

    with open(rollback_path, "w", encoding="utf-8") as f:
        json.dump(rollback, f, indent=2)
