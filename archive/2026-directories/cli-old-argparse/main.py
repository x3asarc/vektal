"""
DEPRECATED: This module is deprecated.
Use the new Typer CLI instead: python -m src.cli.main

This wrapper will be removed in a future version.

For migration guide see: docs/CLI_MIGRATION.md
"""

import warnings
import argparse
import csv
import os
import sys

import pandas as pd

# Show deprecation warning (print to stderr to ensure visibility)
print("\n" + "="*70, file=sys.stderr)
print("  DEPRECATED: cli/main.py is deprecated", file=sys.stderr)
print("="*70, file=sys.stderr)
print("\nUse the new Typer CLI instead: python -m src.cli.main\n", file=sys.stderr)
print("Examples:", file=sys.stderr)
print("  - python -m src.cli.main products update-sku <SKU>", file=sys.stderr)
print("  - python -m src.cli.main search by-sku <SKU>", file=sys.stderr)
print("  - python -m src.cli.main products process <CSV_FILE>", file=sys.stderr)
print("\n" + "="*70 + "\n", file=sys.stderr)

# Also register the warning for programmatic detection
warnings.warn(
    "cli/main.py is deprecated. Use: python -m src.cli.main",
    DeprecationWarning,
    stacklevel=2
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.pipeline import process_identifier, process_with_product, apply_payload_with_context
from src.core.shopify_resolver import ShopifyResolver
from src.core.product_analyzer import ProductAnalyzer, present_analysis_cli


def parse_args():
    parser = argparse.ArgumentParser(description="Unified Shopify pipeline CLI")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--sku")
    group.add_argument("--ean")
    group.add_argument("--handle")
    group.add_argument("--title")
    group.add_argument("--url")
    parser.add_argument("--csv", dest="csv_path")
    parser.add_argument("--mode", choices=["cli", "web"], default="cli")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", default="pipeline_results.csv")
    parser.add_argument("--select-index", type=int, help="Select candidate index when multiple matches are found (1-based)")
    parser.add_argument("--no-prompt", action="store_true", help="Disable interactive prompts and skip approvals")
    parser.add_argument("--auto-apply", action="store_true", help="Apply changes without final confirmation prompt")
    parser.add_argument("--no-analyze", action="store_true", help="Skip pre-processing analysis (SKU/naming check)")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically apply analyzer corrections without prompting")
    return parser.parse_args()


def build_identifier_from_args(args):
    if args.sku:
        return {"kind": "sku", "value": args.sku}
    if args.ean:
        return {"kind": "ean", "value": args.ean}
    if args.handle:
        return {"kind": "handle", "value": args.handle}
    if args.title:
        return {"kind": "title", "value": args.title}
    if args.url:
        return {"kind": "url", "value": args.url}
    return None


def build_identifier_from_row(row):
    for key, kind in [
        ("SKU", "sku"),
        ("EAN", "ean"),
        ("Barcode", "ean"),
        ("Handle", "handle"),
        ("Title", "title"),
        ("URL", "url"),
    ]:
        value = row.get(key)
        if value and str(value).strip():
            return {"kind": kind, "value": str(value).strip()}
    return None


def prompt_choice(message, choices):
    while True:
        raw = input(message).strip().lower()
        if raw in choices:
            return raw


def select_candidate(candidates, select_index=None):
    print("Multiple products found:")
    for idx, c in enumerate(candidates, start=1):
        print(f"  {idx}) {c.get('title')} | {c.get('handle')} | {c.get('id')}")

    if select_index:
        idx = select_index - 1
        if 0 <= idx < len(candidates):
            return candidates[idx]
        return None

    if not sys.stdin.isatty():
        return None

    choice = input("Select product number (or blank to skip): ").strip()
    if not choice:
        return None
    try:
        idx = int(choice) - 1
        return candidates[idx]
    except Exception:
        return None


def apply_cli_approvals(payload, batch_state=None, auto_apply=False):
    batch_state = batch_state or {}
    diff = payload.get("diff", {})
    if not diff or "requires_approval" not in diff:
        return payload
    apply_plan = payload.get("apply_plan", {})
    product = payload.get("product", {})

    # Title approval
    title_req = diff.get("requires_approval", {}).get("title_change", {})
    if title_req.get("proposed_title"):
        if auto_apply:
            title_req["approved"] = True
        elif batch_state.get("title_all") is True:
            title_req["approved"] = True
        elif batch_state.get("title_all") is False:
            title_req["approved"] = False
        elif not sys.stdin.isatty():
            title_req["approved"] = False
        else:
            title = product.get("title") or product.get("handle")
            resp = prompt_choice(
                f"Change title for '{title}' to '{title_req.get('proposed_title')}'? (y/n/all/none): ",
                {"y", "n", "all", "none"},
            )
            if resp == "all":
                batch_state["title_all"] = True
                title_req["approved"] = True
            elif resp == "none":
                batch_state["title_all"] = False
                title_req["approved"] = False
            else:
                title_req["approved"] = resp == "y"

        if title_req.get("approved"):
            apply_plan.setdefault("update_fields", {})
            apply_plan["update_fields"]["title"] = title_req.get("proposed_title")
        else:
            if apply_plan.get("update_fields", {}).get("title"):
                apply_plan["update_fields"].pop("title", None)

    # SEO approval
    seo_req = diff.get("requires_approval", {}).get("seo_change", {})
    if seo_req.get("proposed_fields"):
        if auto_apply:
            seo_req["approved"] = True
        elif batch_state.get("seo_all") is True:
            seo_req["approved"] = True
        elif batch_state.get("seo_all") is False:
            seo_req["approved"] = False
        elif not sys.stdin.isatty():
            seo_req["approved"] = False
        else:
            title = product.get("title") or product.get("handle")
            resp = prompt_choice(
                f"Apply SEO/description updates for '{title}'? (y/n/all/none): ",
                {"y", "n", "all", "none"},
            )
            if resp == "all":
                batch_state["seo_all"] = True
                seo_req["approved"] = True
            elif resp == "none":
                batch_state["seo_all"] = False
                seo_req["approved"] = False
            else:
                seo_req["approved"] = resp == "y"

        if seo_req.get("approved"):
            apply_plan.setdefault("update_fields", {})
            for key, value in (seo_req.get("proposed_fields") or {}).items():
                apply_plan["update_fields"][key] = value

    # Image approval
    image_req = diff.get("requires_approval", {}).get("image_replace", {})
    if image_req.get("status") == "needs_approval":
        if auto_apply:
            image_req["approved"] = True
        elif batch_state.get("image_all") is True:
            image_req["approved"] = True
        elif batch_state.get("image_all") is False:
            image_req["approved"] = False
        elif not sys.stdin.isatty():
            image_req["approved"] = False
        else:
            title = product.get("title") or product.get("handle")
            resp = prompt_choice(
                f"Replace image #1 for '{title}'? (y/n/all/none): ",
                {"y", "n", "all", "none"},
            )
            if resp == "all":
                batch_state["image_all"] = True
                image_req["approved"] = True
            elif resp == "none":
                batch_state["image_all"] = False
                image_req["approved"] = False
            else:
                image_req["approved"] = resp == "y"

        if not image_req.get("approved"):
            apply_plan["update_images"]["action"] = "skip"

    # Handle approval
    handle_req = diff.get("requires_approval", {}).get("handle_change", {})
    if handle_req.get("proposed_handle"):
        if not title_req.get("approved"):
            handle_req["approved"] = False
            apply_plan["update_handle"]["enabled"] = False
        elif auto_apply:
            handle_req["approved"] = True
        elif batch_state.get("handle_all") is True:
            handle_req["approved"] = True
        elif batch_state.get("handle_all") is False:
            handle_req["approved"] = False
        elif not sys.stdin.isatty():
            handle_req["approved"] = False
        else:
            title = product.get("title") or product.get("handle")
            resp = prompt_choice(
                f"Change handle for '{title}' to '{handle_req.get('proposed_handle')}'? (y/n/all/none): ",
                {"y", "n", "all", "none"},
            )
            if resp == "all":
                batch_state["handle_all"] = True
                handle_req["approved"] = True
            elif resp == "none":
                batch_state["handle_all"] = False
                handle_req["approved"] = False
            else:
                handle_req["approved"] = resp == "y"

        if handle_req.get("approved"):
            apply_plan["update_handle"]["enabled"] = True
            for redirect in apply_plan.get("create_redirects", []):
                redirect["enabled"] = True
        else:
            apply_plan["update_handle"]["enabled"] = False

    # HS code approval (hybrid suggestion)
    hs_req = diff.get("requires_approval", {}).get("hs_code_change", {})
    if hs_req.get("proposed_hs_code"):
        if auto_apply:
            hs_req["approved"] = True
        elif batch_state.get("hs_all") is True:
            hs_req["approved"] = True
        elif batch_state.get("hs_all") is False:
            hs_req["approved"] = False
        elif not sys.stdin.isatty():
            hs_req["approved"] = False
        else:
            prompt = (
                f"Apply HS code '{hs_req.get('proposed_hs_code')}' "
                f"(confidence {hs_req.get('confidence')}, {hs_req.get('source')})? (y/n/all/none): "
            )
            resp = prompt_choice(prompt, {"y", "n", "all", "none"})
            if resp == "all":
                batch_state["hs_all"] = True
                hs_req["approved"] = True
            elif resp == "none":
                batch_state["hs_all"] = False
                hs_req["approved"] = False
            else:
                hs_req["approved"] = resp == "y"

        if hs_req.get("approved"):
            apply_plan.setdefault("update_inventory", {})
            apply_plan["update_inventory"]["harmonized_system_code"] = hs_req.get("proposed_hs_code")

    payload["apply_plan"] = apply_plan
    payload["diff"]["requires_approval"]["seo_change"] = seo_req
    payload["diff"]["requires_approval"]["image_replace"] = image_req
    payload["diff"]["requires_approval"]["handle_change"] = handle_req
    payload["diff"]["requires_approval"]["title_change"] = title_req
    payload["diff"]["requires_approval"]["hs_code_change"] = hs_req
    return payload


def print_payload_summary(payload):
    product = payload.get("product") or {}
    diff = payload.get("diff") or {}
    apply_plan = payload.get("apply_plan") or {}
    scraped = (payload.get("scrape") or {}).get("results", {})
    quality = payload.get("quality") or {}

    print("\n=== Product Snapshot ===")
    print(f"Title: {product.get('title')}")
    print(f"Handle: {product.get('handle')}")
    print(f"SKU: {(product.get('primary_variant') or {}).get('sku')}")
    print(f"Barcode: {(product.get('primary_variant') or {}).get('barcode')}")
    print(f"Weight: {(product.get('primary_variant') or {}).get('weight')} {(product.get('primary_variant') or {}).get('weight_unit')}")
    print(f"Country: {(product.get('primary_variant') or {}).get('inventory_country')}")
    print(f"HS Code: {(product.get('primary_variant') or {}).get('inventory_hs_code')}")
    print(f"SEO Title: {product.get('seo_title')}")
    print(f"SEO Desc: {product.get('seo_description')}")

    print("\n=== Missing Fields ===")
    print(", ".join(diff.get("missing_fields") or []) or "None")

    print("\n=== Scraped Results ===")
    if not scraped:
        print("None")
    else:
        for key, value in scraped.items():
            if value not in (None, "", []):
                print(f"- {key}: {value}")

    print("\n=== Planned Updates ===")
    print(f"Fields: {list((apply_plan.get('update_fields') or {}).keys())}")
    print(f"Variant updates: {list((apply_plan.get('update_variants') or {}).keys())}")
    print(f"Inventory updates: {list((apply_plan.get('update_inventory') or {}).keys())}")
    print(f"Image action: {(apply_plan.get('update_images') or {}).get('action')}")
    print(f"Handle change: {(apply_plan.get('update_handle') or {}).get('enabled')}")

    # Show image framework processing status
    if scraped.get("image_transformations"):
        transformations = scraped["image_transformations"]
        print(f"\n=== Image Framework ===")
        print(f"Format: {transformations.get('format', 'N/A')}")
        print(f"Size: {transformations.get('convert_to_square', {}).get('target_size', 'N/A')}x{transformations.get('convert_to_square', {}).get('target_size', 'N/A')}px")
        print(f"Method: {transformations.get('convert_to_square', {}).get('method', 'N/A')}")
        print(f"Transparency: {transformations.get('ensure_transparency', {}).get('convert_to_rgba', False)}")
        print(f"Filename: {scraped.get('suggested_filename', 'N/A')}")
        print(f"Alt text: {scraped.get('alt_text', 'N/A')[:60]}...")
    if diff.get("requires_approval", {}).get("title_change", {}).get("proposed_title"):
        print(f"Proposed title: {diff['requires_approval']['title_change']['proposed_title']}")
    if diff.get("requires_approval", {}).get("hs_code_change", {}).get("proposed_hs_code"):
        hs = diff["requires_approval"]["hs_code_change"]
        print(f"Proposed HS code: {hs.get('proposed_hs_code')} (confidence {hs.get('confidence')}, {hs.get('source')})")
    seo_req = diff.get("requires_approval", {}).get("seo_change", {})
    if seo_req.get("proposed_fields"):
        fallback = "fallback" if seo_req.get("fallback") else "ai"
        print(f"Proposed SEO ({fallback}):")
        if seo_req.get("proposed_seo_title"):
            print(f"- meta title: {seo_req.get('proposed_seo_title')}")
        if seo_req.get("proposed_seo_description"):
            print(f"- meta desc: {seo_req.get('proposed_seo_description')}")
        if seo_req.get("proposed_description_html"):
            desc = seo_req.get("proposed_description_html") or ""
            preview = (desc[:200] + "...") if len(desc) > 200 else desc
            print(f"- description_html: {preview}")

    if quality:
        print("\n=== Ralph Quality Suggestions (Local Only) ===")
        missing = quality.get("missing_required") or []
        print(f"Missing required: {', '.join(missing) if missing else 'None'}")
        for item in quality.get("suggested_repairs") or []:
            print(f"- {item.get('field')}: {item.get('script')} {item.get('args')}")

def write_results(rows, out_path):
    fieldnames = [
        "run_id",
        "input_kind",
        "input_value",
        "product_id",
        "handle",
        "status",
        "errors",
        "image_action",
        "handle_changed",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def process_single(identifier, args, batch_state=None, context=None):
    context = context or {}
    corrections = []
    
    # Pre-processing analysis: detect SKU/naming issues
    if not args.no_analyze:
        analyzer = ProductAnalyzer(context)
        resolver = context.get("resolver")
        
        # First, resolve the product to get current state
        if resolver:
            resolve_result = resolver.resolve_identifier(identifier)
            matches = resolve_result.get("matches", [])
            
            if matches:
                # If multiple matches, let user select first
                if len(matches) > 1:
                    product = select_candidate(matches, select_index=args.select_index)
                    if not product:
                        return {"errors": ["no selection"], "product": None}, None
                else:
                    product = matches[0]
                
                # Run analysis
                analysis = analyzer.analyze(
                    product, 
                    identifier, 
                    product.get("vendor")
                )
                
                if analysis.has_issues():
                    if args.auto_fix:
                        # Auto-approve all corrections
                        corrections = analysis.corrections
                        print("\n[Auto-fix] Applying corrections:")
                        for c in corrections:
                            print(f"  - {c.get('type')}: {c.get('current')} -> {c.get('proposed')}")
                    elif not args.no_prompt:
                        # Present to user and get confirmation
                        corrections = present_analysis_cli(analysis, auto_approve=args.auto_apply)
                    
                    # Store corrections in context for pipeline
                    context["corrections"] = corrections
    
    # Continue with normal pipeline processing
    payload = process_identifier(identifier, mode=args.mode, context=context)

    if payload.get("candidates"):
        selected = select_candidate(payload.get("candidates"), select_index=args.select_index)
        if not selected:
            payload.setdefault("errors", []).append("no selection")
            return payload, None
        payload = process_with_product(identifier, selected, mode=args.mode, context=context)

    print_payload_summary(payload)

    if args.no_prompt:
        batch_state = dict(batch_state or {})
        batch_state["image_all"] = False
        batch_state["handle_all"] = False
        batch_state["title_all"] = False
        batch_state["hs_all"] = False
        batch_state["seo_all"] = False
    payload = apply_cli_approvals(payload, batch_state=batch_state, auto_apply=args.auto_apply)

    apply_result = None
    if not args.dry_run:
        if not args.auto_apply and not args.no_prompt and sys.stdin.isatty():
            proceed = prompt_choice("Proceed to apply changes? (y/n): ", {"y", "n"})
            if proceed != "y":
                return payload, None
        apply_result = apply_payload_with_context(payload, context=context)

        # Show image verification results if available
        if apply_result and apply_result.get("image_verification"):
            verification = apply_result["image_verification"]
            print("\n=== Image Verification ===")
            if verification.get("needs_recrop"):
                print(f"Status: NEEDS ATTENTION")
                print(f"Issue: {verification.get('issue')}")
                print(f"Fix: {verification.get('recommendation')}")
                print(f"Confidence: {verification.get('confidence', 0):.0%}")
            else:
                print(f"Status: OK")
                print(f"Confidence: {verification.get('confidence', 0):.0%}")

    return payload, apply_result


def main():
    args = parse_args()

    rows = []
    batch_state = {}

    resolver = ShopifyResolver()
    context = {
        "resolver": resolver,
        "shop_domain": resolver.shop_domain,
        "access_token": resolver.client.access_token,
        "api_version": resolver.api_version,
    }

    identifier = build_identifier_from_args(args)
    if identifier:
        payload, apply_result = process_single(identifier, args, batch_state=batch_state, context=context)
        rows.append(_result_row(identifier, payload, apply_result))
        write_results(rows, args.out)
        return 0

    if args.csv_path:
        df = pd.read_csv(args.csv_path)
        for _, row in df.iterrows():
            identifier = build_identifier_from_row(row)
            if not identifier:
                continue
            payload, apply_result = process_single(identifier, args, batch_state=batch_state, context=context)
            rows.append(_result_row(identifier, payload, apply_result))
        write_results(rows, args.out)
        return 0

    print("No identifier provided. Use --sku/--ean/--handle/--title/--url or --csv")
    return 1


def _result_row(identifier, payload, apply_result):
    product = payload.get("product") or {}
    errors = payload.get("errors") or []
    status = "ok" if not errors else "error"

    image_action = payload.get("apply_plan", {}).get("update_images", {}).get("action")
    handle_changed = payload.get("apply_plan", {}).get("update_handle", {}).get("enabled")

    return {
        "run_id": payload.get("run_id"),
        "input_kind": identifier.get("kind"),
        "input_value": identifier.get("value"),
        "product_id": product.get("id"),
        "handle": product.get("handle"),
        "status": status,
        "errors": "; ".join(errors),
        "image_action": image_action,
        "handle_changed": bool(handle_changed),
    }


if __name__ == "__main__":
    sys.exit(main())
