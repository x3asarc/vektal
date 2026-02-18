Galaxy Flakes Image Plan Summary
================================

Status
------

- Primary filenames no longer include "detail".
  - Example: `pentart-galaxy-flakes-15g-jupiter-white.jpg`
  - Source: `data/svse/galaxy-flakes-15g-juno-rose/reports/seo_plan_per_product.csv`
- Shared alt review and cluster mapping reports generated.
- Farbe metafields exported and mapped to Galaxy Flakes.

Files Generated
---------------

- `data/svse/galaxy-flakes-15g-juno-rose/reports/shared_alt_review.csv`
- `data/svse/galaxy-flakes-15g-juno-rose/reports/shared_clusters_products.csv`
- `data/output/farbe_metafields_pentart.csv` (1275 rows)
- `data/output/farbe_metafields_galaxy_flakes.csv` (13 rows)

Step 2 (Apply) Status
---------------------

Apply is not executed yet because the main-image replacement requires supplier images.
Alt text + filename updates can be applied separately if desired.

Supplier Image Pull (Pentart / pentacolor.eu)
---------------------------------------------

✓ **COMPLETED** - Selenium scraper implemented and working

The Pentacolor search is JS-driven (RapidSearch). Simple HTML search does not work.
Solution: Enhanced existing `scrape_pentart_image()` function in `fix_pentart_products.py` with:
- Simple BeautifulSoup scraper (fast, tries first)
- Selenium fallback (for JS-driven sites)

**Files Updated:**
- `fix_pentart_products.py` - Added Selenium fallback to `scrape_pentart_image()`
- `download_galaxy_flakes_images.py` - Bulk download script for all Galaxy Flakes products

**Results:**
- All 12 primary images downloaded to: `data/supplier_images/galaxy_flakes/`
- Images are high-resolution (w1719h900) from Pentacolor CDN
- Filenames match SEO plan: `pentart-galaxy-flakes-15g-{variant}.jpg`

**Note:** All searches land on the same Galaxy Flakes category page, so images need to be matched to specific SKUs (37046, 37047, etc.) from the product page thumbnails.

✅ COMPLETED - All Steps Done
-----------------------------

**Standard Operating Procedure Established and Applied:**

All 12 Galaxy Flakes products now have:
1. ✅ Square images (900x900, 1:1 ratio, center crop method)
2. ✅ Transparent backgrounds (PNG format)
3. ✅ SEO-friendly filenames (pentart-galaxy-flakes-{variant}.png)
4. ✅ Proper alt text (Pentart supplier branding)
5. ✅ Clean image lists (old random-filename images deleted)
6. ✅ Set as featured/primary images

**SOP Script:** `apply_all_galaxy_flakes_sop.py`

**Standard for all future image uploads:**
- Non-square images → center crop to 1:1
- Always preserve/create transparent backgrounds
- Use proper SEO filenames (never Shopify's random names)
- Delete old images after uploading new ones
- Staged uploads for filename control

**Completion Date:** 2026-02-02
**Success Rate:** 12/12 (100%)
