# Tag Cleanup Job Context (2026-01-31)

## Summary
- Goal: normalize Shopify product tags, remove APPSTLE_BUNDLE/APPSTEL_BUNDLE, enforce decoupage -> add both "reispapier" and "reis papier".
- Normalization: lowercase, trim, collapse multiple spaces. Keep spaced vs unspaced variants as-is (do NOT merge).
- Blacklist: "APPSTLE_BUNDLE", "APPSTEL_BUNDLE".
- Additional cleanup: remove HTML/escaped artifacts in tags.

## Code Changes Made
- Updated `utils/generate_product_tags.py`:
  - Normalizes tags to lowercase + single spaces.
  - Removes blacklisted/HTML-like tags.
  - Ensures decoupage implies both "reispapier" and "reis papier".
  - Uses vendor-specific min tag count from `config/product_quality_rules.yaml`.
- Added `scripts/cleanup_shopify_tags.py`:
  - Supports `--apply`, `--limit`, `--sleep`, `--cursor-file`, `--report`.
  - Paginates Shopify products and updates tags using the above rules.

## What Was Run
- Bulk tag cleanup started with:
  - `python scripts/cleanup_shopify_tags.py --apply --sleep 0.2 --limit 1000 --cursor-file data/tag_cleanup_cursor.txt --report data/tag_cleanup_report_<timestamp>.json`
- Result (first 1000 products):
  - processed: 1000
  - updated: 169
  - skipped: 831
  - errors: 0
  - decoupage_added_products: 1
  - Report saved: `data/tag_cleanup_report_20260130_233640.json`
  - Cursor saved: `data/tag_cleanup_cursor.txt`
- Subsequent runs with higher limits timed out; job needs to be resumed in smaller batches.

## Current Cursor State
- `data/tag_cleanup_cursor.txt` contains a base64 cursor (Shopify pagination).
- Last read value (do not edit): `eyJsYXN0X2lkIjo2NjY1ODY1MjY1MzA5LCJsYXN0X3ZhbHVlIjoiNjY2NTg2NTI2NTMwOSJ9`

## Files Created/Modified
- Modified: `utils/generate_product_tags.py`
- Added: `scripts/cleanup_shopify_tags.py`
- Generated report: `data/tag_cleanup_report_20260130_233640.json`
- Cursor file: `data/tag_cleanup_cursor.txt`

## Notes / Observations
- Normalization is aggressive (lowercasing). This was requested.
- "Low Stock" tags were lowercased to "low stock"; no blacklist for those yet.
- "decoupage" products now get both "reispapier" and "reis papier".

## Next Steps (Task List)
1) Resume cleanup in smaller batches (200-500 products):
   - `python scripts/cleanup_shopify_tags.py --apply --sleep 0.2 --limit 500 --cursor-file data/tag_cleanup_cursor.txt --report data/tag_cleanup_report_<timestamp>.json`
2) Repeat until all products processed (cursor file will advance).
3) Optional: Add additional blacklist tags if you want to remove system tags (e.g., "low stock", "appstle_*").
4) After full cleanup, re-run tag inventory for a final summary.
5) If desired, add a dry-run option and diff export for QA.

