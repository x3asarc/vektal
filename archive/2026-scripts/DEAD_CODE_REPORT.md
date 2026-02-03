# Dead Code Analysis Report

**Analysis Date:** 2026-02-03
**Analyzed By:** Claude Code (GSD Plan 01-01, Task 3)
**Tools Used:** Vulture 2.14, deadcode 2.4.1
**Scope:** src/, cli/ (excluding archive/, venv/)

---

## Executive Summary

This report documents potential dead code found in the production codebase. The analysis identifies:
- **6 findings from Vulture** (80%+ confidence)
- **46 findings from deadcode** across multiple categories

**CRITICAL:** This is analysis only. DO NOT delete any code without manual review. Some findings may be false positives (e.g., Flask route handlers appear unused because they're registered via decorators).

---

## Findings by Severity

### HIGH CONFIDENCE - Unused Imports (likely safe to remove)

| File | Item | Status | Notes |
|------|------|--------|-------|
| src/app.py | import send_from_directory | CONFIRMED_DEAD | Flask import not used (90% confidence) |
| src/bot_server.py | import asyncio | CONFIRMED_DEAD | Import not used (90% confidence) |
| src/core/image_verifier.py | import Tuple | CONFIRMED_DEAD | Type hint not used (90% confidence) |
| src/core/pipeline.py | import generate_vision_alt_text | CONFIRMED_DEAD | Import not used (90% confidence) |

**Recommendation:** Safe to remove these unused imports in a cleanup PR.

---

### MEDIUM CONFIDENCE - Unused Variables (review needed)

| File | Item | Status | Notes |
|------|------|--------|-------|
| src/core/image_verifier.py:247 | variable shopify_client | NEEDS_REVIEW | Variable defined but never used (100% confidence) |
| src/core/image_verifier.py:353 | variable shopify_client | NEEDS_REVIEW | Variable defined but never used (100% confidence) |
| cli/testing/test_image_improvements.py:108 | variable should_warn | NEEDS_REVIEW | May be intended for future use |
| src/app.py:254 | variable order_data | NEEDS_REVIEW | Webhook handler - may need data for logging |
| src/core/product_analyzer.py:26 | variable correct_barcode | NEEDS_REVIEW | Dataclass field, check if used elsewhere |
| src/core/paths.py:16 | variable NOT_FOUND_CSV | NEEDS_REVIEW | Config constant, may be used dynamically |
| src/core/paths.py:18 | variable VISION_PROOF_CSV | NEEDS_REVIEW | Config constant, may be used dynamically |

**Recommendation:** Manual code review to determine if these are truly unused or have planned uses.

---

### FALSE POSITIVES - API Routes & Webhook Handlers

These are **NOT dead code** - they're Flask route handlers registered via decorators:

| File | Function | Status | Notes |
|------|----------|--------|-------|
| src/app.py:172 | health() | FALSE_POSITIVE | Flask route: GET /health |
| src/app.py:177 | shopify_auth() | FALSE_POSITIVE | Flask route: GET /api/auth/shopify |
| src/app.py:200 | shopify_callback() | FALSE_POSITIVE | Flask route: GET /api/auth/callback |
| src/app.py:245 | webhook_orders_create() | FALSE_POSITIVE | Flask route: POST /webhooks/orders/create |
| src/app.py:260 | get_status() | FALSE_POSITIVE | Flask route: GET /api/status |
| src/app.py:269 | get_jobs() | FALSE_POSITIVE | Flask route: GET /api/jobs |
| src/app.py:292 | get_job() | FALSE_POSITIVE | Flask route: GET /api/jobs/<job_id> |
| src/app.py:325 | job_detail_page() | FALSE_POSITIVE | Flask route: GET /jobs/<job_id> |
| src/app.py:330 | pipeline_dry_run() | FALSE_POSITIVE | Flask route: POST /api/pipeline/dry-run |
| src/app.py:359 | pipeline_push() | FALSE_POSITIVE | Flask route: POST /api/pipeline/push |
| src/app.py:382 | create_job() | FALSE_POSITIVE | Flask route: POST /api/jobs |
| src/app.py:717 | cancel_job() | FALSE_POSITIVE | Flask route: POST /api/jobs/<job_id>/cancel |

**Recommendation:** Keep all Flask routes. Deadcode cannot detect @app.route decorator usage.

---

### FALSE POSITIVES - CLI Commands

These are **NOT dead code** - they're Click CLI commands registered via decorators:

| File | Function | Status | Notes |
|------|----------|--------|-------|
| src/cli/commands/products.py:26 | update_sku() | FALSE_POSITIVE | Click command registered via decorator |
| src/cli/commands/products.py:121 | process() | FALSE_POSITIVE | Click command registered via decorator |
| src/cli/commands/search.py:55 | search_by_sku() | FALSE_POSITIVE | Click command registered via decorator |
| src/cli/commands/search.py:76 | search_by_title() | FALSE_POSITIVE | Click command registered via decorator |
| src/cli/commands/search.py:97 | search_by_handle() | FALSE_POSITIVE | Click command registered via decorator |

**Recommendation:** Keep all CLI commands. Deadcode cannot detect @click.command decorator usage.

---

### NEEDS_REVIEW - Potentially Unused Methods

These methods may be genuinely unused or may be called dynamically:

| File | Method | Status | Notes |
|------|--------|--------|-------|
| cli/bulk/push_images_only.py:83 | delete_media() | NEEDS_REVIEW | May be legacy method to remove |
| cli/products/update_pentart_barcode.py:118 | update_variant_and_inventory() | NEEDS_REVIEW | Check if used in workflows |
| src/core/image_framework.py:240 | validate_filename() | NEEDS_REVIEW | Validation method, may be for future use |
| src/core/image_framework.py:650 | get_action() | NEEDS_REVIEW | May be part of strategy pattern |
| src/core/image_verifier.py:241 | recrop_and_reupload() | NEEDS_REVIEW | Specific operation, check if needed |
| src/core/vendor_config.py:305 | is_scraper_enabled() | NEEDS_REVIEW | Config query method |
| src/core/vendor_config.py:319 | get_scraper_config() | NEEDS_REVIEW | Config query method |
| src/core/vision_cache.py:258 | get_stats_for_date() | NEEDS_REVIEW | Analytics method, may be for reporting |

**Recommendation:** Investigate call sites. If truly unused, consider removing or documenting as "planned feature."

---

### NEEDS_REVIEW - Potentially Unused Functions

| File | Function | Status | Notes |
|------|----------|--------|-------|
| src/core/vendor_config.py:373 | get_vendor_hs_code() | NEEDS_REVIEW | Config query, check if used elsewhere |
| src/core/vendor_config.py:378 | get_vendor_country() | NEEDS_REVIEW | Config query, check if used elsewhere |
| src/core/vision_engine.py:36 | generate_vision_alt_text() | CONFIRMED_DEAD | Also flagged as unused import in pipeline.py |
| src/utils/sku_ean_validator.py:121 | format_sku_ean_info() | NEEDS_REVIEW | Formatting utility, may be for future use |

**Recommendation:** Manual review. The vision_engine function is likely safe to remove (imported but never called).

---

### NEEDS_REVIEW - Unused Attributes

| File | Attribute | Status | Notes |
|------|-----------|--------|-------|
| src/app.py:33 | app.secret_key | NEEDS_REVIEW | Flask config, may be needed for sessions |
| src/app.py:276 | cursor.row_factory | NEEDS_REVIEW | SQLite config for query results |
| src/app.py:299 | cursor.row_factory | NEEDS_REVIEW | SQLite config for query results |
| src/app.py:428 | thread.daemon | NEEDS_REVIEW | Thread config, may be needed |
| src/core/product_analyzer.py:181 | .correct_barcode | NEEDS_REVIEW | Dataclass field assignment |
| src/core/product_analyzer.py:186 | .correct_barcode | NEEDS_REVIEW | Dataclass field assignment |
| src/core/product_analyzer.py:191 | .correct_barcode | NEEDS_REVIEW | Dataclass field assignment |
| src/core/product_analyzer.py:196 | .correct_barcode | NEEDS_REVIEW | Dataclass field assignment |

**Recommendation:** Most of these are configuration attributes. Likely false positives.

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Confirmed Dead (safe to remove) | 4 (unused imports) |
| False Positives (Flask/Click) | 17 |
| Needs Review | 25 |
| **Total Findings** | 46 |

---

## Recommended Actions

### Immediate Cleanup (Low Risk)
1. Remove 4 confirmed unused imports:
   - send_from_directory in src/app.py
   - asyncio in src/bot_server.py
   - Tuple in src/core/image_verifier.py
   - generate_vision_alt_text in src/core/pipeline.py

### Further Investigation Required
2. Manual review of 25 items marked NEEDS_REVIEW
3. Investigate generate_vision_alt_text() function - imported but never called
4. Review shopify_client variables in image_verifier.py (lines 247, 353)

### No Action Needed
- Keep all Flask route handlers (17 false positives)
- Keep all Click CLI commands (5 false positives)
- Keep configuration attributes (likely false positives)

---

## Notes

- **Production code constraint:** src/core/ should not be modified without thorough testing
- **Decorator limitation:** Static analysis tools cannot detect function usage via decorators
- **Dynamic calls:** Some methods may be called via getattr() or other dynamic patterns
- **Planned features:** Some unused code may be infrastructure for future features

---

**Next Steps:** Create a separate plan for dead code removal after manual review and testing.
