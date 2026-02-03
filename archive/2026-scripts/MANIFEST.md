# Archived Scripts Manifest

**Archive Date:** 2026-02-03
**Archived By:** Claude Code (GSD Plan 01-01)
**Reason:** Cleanup root directory to distinguish production code (src/core/) from one-off experimental scripts

## Overview

This archive contains 50+ scripts that were cluttering the root directory. These are one-off scripts written to handle specific tasks, experiments, or debugging. They have been organized by category below.

## Category Structure

- **apply/** - Scripts that apply changes to Shopify (modify products/images)
- **scrape/** - Scraping scripts for vendor data and images
- **fix/** - Fix/repair scripts for data cleanup
- **dry-run/** - Dry run preview scripts (show changes without applying)
- **debug/** - Debug scripts including JavaScript debugging tools
- **analysis/** - Analysis, search, and find scripts
- **test-scripts/** - Standalone test scripts from root (NOT from tests/ directory)
- **misc/** - Miscellaneous scripts that don't fit other categories

---

## Scripts Index

| Script | Category | Original Purpose | Date Archived |
|--------|----------|------------------|---------------|
| apply_all_galaxy_flakes_sop.py | apply | Apply SOP to all 12 Galaxy Flakes products: convert to square, transparent background, SEO filenames | 2026-02-03 |
| apply_saturn_green.py | apply | Apply image updates to Saturn Green product | 2026-02-03 |
| apply_saturn_green_with_filename.py | apply | Apply Saturn Green updates with specific filename | 2026-02-03 |
| scrape_and_upload_images.py | scrape | Scrape and upload images for 3 Pentart products | 2026-02-03 |
| scrape_paperdesigns_missing.py | scrape | Scrape missing Paperdesigns products | 2026-02-03 |
| scrape_single_paperdesign.py | scrape | Scrape single Paperdesigns product by SKU | 2026-02-03 |
| scrape_three_images.py | scrape | Scrape images for 3 specific products | 2026-02-03 |
| scrape_views_0009_direct.py | scrape | Direct scraping for views-0009 product | 2026-02-03 |
| fix_and_add_images.py | fix | Fix products and add missing images | 2026-02-03 |
| fix_pentart_products.py | fix | Complete Pentart product fix: SKU, barcode, weight, inventory, images, German translation | 2026-02-03 |
| fix_pentart_rest.py | fix | Fix remaining Pentart products | 2026-02-03 |
| auto_fix_images.py | fix | Automated image fixing script | 2026-02-03 |
| dry_run_pluto_yellow.py | dry-run | Preview Pluto Yellow product update without applying | 2026-02-03 |
| dry_run_restore_all_images.py | dry-run | Preview restore all images operation | 2026-02-03 |
| dry_run_restore_shared_images.py | dry-run | Preview restore shared images operation | 2026-02-03 |
| dry_run_saturn_green.py | dry-run | Preview Saturn Green image update without applying | 2026-02-03 |
| debug_aistcraft.js | debug | Debug Aistcraft vendor scraper | 2026-02-03 |
| debug_itd.js | debug | Debug ITD Collection vendor scraper | 2026-02-03 |
| debug_pentart.js | debug | Debug Pentart vendor scraper | 2026-02-03 |
| debug_single_vendor.js | debug | Debug single vendor scraping (Paperdesigns) | 2026-02-03 |
| analyze_deleted_images.py | analysis | Analyze deleted images from Shopify | 2026-02-03 |
| analyze_reispapier_vendors.py | analysis | Analyze Reispapier vendor data | 2026-02-03 |
| find_missing_products.py | analysis | Find products missing in catalog | 2026-02-03 |
| find_products_by_sku.py | analysis | Search products by SKU | 2026-02-03 |
| find_remaining_products.py | analysis | Find remaining products to process | 2026-02-03 |
| search_broad.py | analysis | Broad search across products | 2026-02-03 |
| search_by_title.py | analysis | Search products by title | 2026-02-03 |
| list_all_products.py | analysis | List all products in Shopify catalog | 2026-02-03 |
| test_pentart_scraper.py | test-scripts | Test Pentart scraper functionality | 2026-02-03 |
| test_product_creation.py | test-scripts | Test product creation workflow | 2026-02-03 |
| test_universal_scraper.js | test-scripts | Test universal vendor scraper | 2026-02-03 |
| add_pentart_products.py | misc | Add new Pentart products to Shopify | 2026-02-03 |
| catalog_paperdesigns.py | misc | Catalog Paperdesigns products | 2026-02-03 |
| complete_pentart_products.py | misc | Complete Pentart product setup | 2026-02-03 |
| download_galaxy_flakes_images.py | misc | Download Galaxy Flakes images from vendor | 2026-02-03 |
| generate_square_versions.py | misc | Generate square versions of images | 2026-02-03 |
| get_test_skus.py | misc | Get SKUs for testing | 2026-02-03 |
| hybrid_image_naming.py | misc | Hybrid image naming strategy implementation | 2026-02-03 |
| infer_paperdesigns_urls.py | misc | Infer Paperdesigns product URLs | 2026-02-03 |
| inspect_pentacolor.py | misc | Inspect Pentacolor product data | 2026-02-03 |
| preview_galaxy_flakes_updates.py | misc | Preview Galaxy Flakes updates before applying | 2026-02-03 |
| process_products_by_id.py | misc | Process products by product ID | 2026-02-03 |
| quick_image_test.py | misc | Quick test for image operations | 2026-02-03 |
| recreate_pentart_products.py | misc | Recreate Pentart products from scratch | 2026-02-03 |
| replace_juno_rose_primary.py | misc | Replace primary image for Juno Rose product | 2026-02-03 |
| replace_primary_image_safe.py | misc | Safely replace primary image with validation | 2026-02-03 |
| restore_shared_images_to_all_products.py | misc | Restore shared images across all products | 2026-02-03 |
| set_inventory_final.py | misc | Set final inventory levels | 2026-02-03 |
| set_inventory_levels.py | misc | Set inventory levels for products | 2026-02-03 |
| update_saturn_green_final.py | misc | Final Saturn Green product update | 2026-02-03 |
| update_three_products.py | misc | Update three specific products | 2026-02-03 |
| upload_scraped_images.py | misc | Upload scraped images to Shopify | 2026-02-03 |
| verify_image_types_with_vision.py | misc | Verify image types using Vision AI | 2026-02-03 |
| verify_uploaded_images.py | misc | Verify successfully uploaded images | 2026-02-03 |
| universal_vendor_scraper.js | misc | Universal vendor scraper (v1) | 2026-02-03 |
| universal_vendor_scraper_v2.js | misc | Universal vendor scraper (v2) | 2026-02-03 |
| scrape_missing_products.js | misc | Scrape missing products from vendors | 2026-02-03 |

---

## Files Kept in Root

**demo_framework.py** - Kept as documentation example showing how to use the framework
**requirements.txt** - Package dependencies (essential)
**.env, .env.example** - Configuration files (essential)
**README.md and other .md files** - Project documentation (essential)

---

## Notes

- All scripts moved using `git mv` to preserve git history
- None of these scripts are imported by production code in `src/core/`
- Scripts may have dependencies on each other or on src/core/ modules
- Before deleting, check if any script contains useful logic to extract into core modules

---

**Total Scripts Archived:** 58 (50 Python + 8 JavaScript)
