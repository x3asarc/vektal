# Product Quality Orchestrator - Setup Tasks

**Status:** Paused - Redirect system needed before proceeding
**Last Updated:** 2026-01-30

---

## ✅ Completed Tasks (5/19)

### #1 - Add vendor logistics data to vendor_configs.yaml ✅
- Added `default_weight` to all vendors
- Added Bastelschachtel vendor configuration
- Updated config at: `config/vendor_configs.yaml`

### #2 - Create config directory if missing ✅
- Created `config/` directory
- Ready for configuration files

### #3 - Test logistics enrichment script ✅
- Fixed vendor name matching (handles spaces and underscores)
- Fixed key name mismatch (hs_code_default vs default_hs_code)
- Fixed config path lookup
- **Test Result:** Successfully added Country of Origin (IT) and HS Code (4823.90) to CBRP104

### #4 - Test URL handle fix script ✅
- Fixed slugify function (regex error with umlauts)
- **Test Result:** Successfully changed handle from `reispapier-a4-love-in-venice-6761` to `reispapier-a4-under-the-tuscan-sun-cards`
- **IMPORTANT:** Discovered critical issue - breaks existing URLs without redirects!

### #8 - Run full quality check with auto-repair on test product ✅
- Tested on CBRP104
- **Before:** 60/100 score, 6 missing fields
- **After:** 73/100 score, 4 missing fields
- **Auto-fixed:** Country of origin, HS code, SEO description
- **Failed:** Images (selenium dependency), Weight (API limitation)

---

## 🚨 Critical Issue Discovered

**Problem:** Changing product handles breaks existing URLs and SEO
**Impact:** Old product URLs return 404 errors
**Example:** `/products/reispapier-a4-love-in-venice-6761` → broken
**Resolution:**
- Disabled handle checking in quality rules
- Created manual redirect for CBRP104
- Need to implement automatic redirect system before re-enabling

---

## ⏸️ Paused Tasks

### #19 - Implement URL redirect system before handle fixes 🚨 CRITICAL
**Priority:** HIGH - Must complete before any handle fixing
**Requirements:**
- Implement Shopify UrlRedirect API integration
- Auto-create redirects when changing handles
- Requires API scope: `write_online_store_navigation`

**Shopify API Mutation:**
```graphql
mutation CreateRedirect {
  urlRedirectCreate(urlRedirect: {
    path: "/products/old-handle"
    target: "/products/new-handle"
  }) {
    urlRedirect { id path target }
  }
}
```

**Current Status:**
- Redirect utility created at `utils/create_shopify_redirect.py`
- Needs API permission update
- Handle checking **DISABLED** in quality rules until this is complete

---

## 📋 Pending Core Setup Tasks

### #5 - Test tags generation script
**Status:** Not started
**Script:** `utils/generate_product_tags.py`
**Test:** Generate AI tags for a product with <3 tags
**Expected:** Product gains 3-7 relevant German tags

### #6 - Test collections assignment script
**Status:** Not started
**Script:** `utils/assign_collections.py`
**Test:** Assign collections to a product without any
**Expected:** Product added to 1-3 matching collections

### #7 - Test product categorization script
**Status:** Not started
**Script:** `utils/categorize_product.py`
**Test:** Set product_type for a product without one
**Expected:** Product type set based on title/tags

---

## 📋 Pending Integration Tasks

### #9 - Integrate quality check trigger into SEO script
**Status:** Not started
**Location:** `seo/generate_seo_quick.py`
**Changes needed:**
```python
from orchestrator.trigger_quality_check import after_seo_update

# After push_from_csv completes:
for update in approved_updates:
    sku = # extract SKU
    after_seo_update(sku)
```

### #10 - Integrate quality check trigger into image scraper
**Status:** Not started
**Location:** `image_scraper.py`
**Changes needed:**
```python
from orchestrator.trigger_quality_check import after_image_scrape

# After images uploaded:
after_image_scrape(sku)
```

### #11 - Integrate quality check trigger into barcode search
**Status:** Not started
**Location:** `search_barcode.py`
**Changes needed:**
```python
from orchestrator.trigger_quality_check import after_barcode_found

# After barcode updated:
after_barcode_found(sku)
```

---

## 📋 Pending Testing Tasks

### #12 - Test chain reaction workflow
**Status:** Not started
**Description:** Test complete chain where one repair triggers another
**Test scenario:**
1. Run SEO update on very incomplete product
2. Verify SEO triggers quality check
3. Verify quality check dispatches other repairs
4. Verify repairs complete and trigger more checks
5. Document the chain reaction

### #13 - Run bulk quality check on all incomplete products
**Status:** Not started
**Command:** `python orchestrator/product_quality_agent.py --check-all --limit 20`
**Purpose:** Populate master tracking file, audit product quality
**Expected:** Master file with 20 products showing completeness scores

### #14 - Review master tracking file and identify patterns
**Status:** Not started
**File:** `data/product_quality_master.json`
**Analyze:**
- Which fields are most commonly missing?
- Which vendors have most incomplete products?
- Average completeness score?
- Vendor-specific patterns?

### #15 - Run bulk auto-repair on top 10 worst products
**Status:** Not started
**Command:** `python orchestrator/product_quality_agent.py --check-all --limit 10 --auto-repair`
**Monitor:**
- How many fields successfully repaired?
- Which repairs commonly fail and why?
- Average score improvement?

---

## 📋 Pending Configuration Tasks

### #16 - Customize quality rules for your store
**Status:** Not started
**File:** `config/product_quality_rules.yaml`
**Customize:**
- Adjust minimum requirements (images, tags counts)
- Add vendor-specific overrides
- Adjust scoring weights
- Add custom fields specific to business

### #17 - Set up scheduled daily quality runs
**Status:** Not started
**Setup:** Windows Task Scheduler or cron
**Command:** `python orchestrator/product_quality_agent.py --check-all --limit 50 --auto-repair`
**Schedule:** Daily at 2 AM (low traffic time)
**Purpose:** Continuous product maintenance and self-healing

### #18 - Document customizations and workflow
**Status:** Not started
**Create:** `ORCHESTRATOR_CUSTOM_SETUP.md`
**Document:**
- Vendor logistics data configured
- Custom quality rules added
- Integration points in existing scripts
- Scheduled run configuration
- Troubleshooting guide
- How to add new repair scripts

---

## 🛠️ System Status

### What's Working ✅
- ✅ Product quality checking and scoring (0-100)
- ✅ Missing field detection (15+ required fields)
- ✅ Master tracking file (JSON format, dashboard-ready)
- ✅ Vendor logistics enrichment (country, HS code)
- ✅ SEO content regeneration
- ✅ Priority queue (worst first, then FIFO)

### What's Disabled ⚠️
- ⚠️ Handle fixing (disabled until redirect system ready)
- ⚠️ Weight updates (API limitation)

### What Needs Dependencies 📦
- 📦 Image scraping (needs selenium)
- 📦 Auto redirects (needs API permission)

---

## 📁 Key Files

### Configuration
- `config/product_quality_rules.yaml` - Field requirements
- `config/vendor_configs.yaml` - Vendor logistics data

### Core System
- `orchestrator/product_quality_agent.py` - Main orchestrator
- `orchestrator/trigger_quality_check.py` - Integration helpers
- `data/product_quality_master.json` - Tracking file (auto-created)

### Repair Scripts
- `utils/enrich_product_logistics.py` - ✅ Working
- `utils/fix_product_handles.py` - ⚠️ Disabled (needs redirects)
- `utils/generate_product_tags.py` - ⏳ Not tested
- `utils/assign_collections.py` - ⏳ Not tested
- `utils/categorize_product.py` - ⏳ Not tested
- `utils/create_shopify_redirect.py` - ⏳ Needs API permission
- `seo/generate_seo_quick.py` - ✅ Working
- `image_scraper.py` - 📦 Needs selenium
- `search_barcode.py` - ✅ Existing (needs integration)

---

## 🎯 Next Steps (When Ready to Resume)

### Immediate Priority
1. **Get API permission** for `write_online_store_navigation` (for redirects)
2. **Update redirect script** to work with new permission
3. **Re-enable handle checking** in quality rules
4. **Test complete workflow** with redirects working

### Testing Priority
1. Test remaining repair scripts (#5, #6, #7)
2. Run bulk quality check (#13)
3. Review patterns (#14)
4. Test chain reactions (#12)

### Integration Priority
1. Integrate into SEO script (#9)
2. Integrate into image scraper (#10)
3. Integrate into barcode search (#11)

### Production Priority
1. Run bulk auto-repair (#15)
2. Set up scheduled runs (#17)
3. Document everything (#18)
4. Customize for your needs (#16)

---

## 📊 Test Results

### CBRP104 Test Product
- **Vendor:** Ciao Bella
- **Initial Score:** 60/100 (6 missing fields)
- **After Auto-Repair:** 73/100 (4 missing fields)
- **What Was Fixed:**
  - ✅ Country of origin: IT
  - ✅ HS code: 4823.90
  - ✅ SEO description: Regenerated (now <160 chars)
  - ✅ URL handle: Fixed (manual redirect created)
- **What's Still Missing:**
  - ❌ Weight (API doesn't support)
  - ❌ Images (selenium not installed)
- **Manual Action Taken:**
  - Created redirect: `/products/reispapier-a4-love-in-venice-6761` → `/products/reispapier-a4-under-the-tuscan-sun-cards`

---

## 💡 Key Learnings

1. **URL Changes Are Dangerous** - Always create redirects before changing handles
2. **API Limitations** - Some fields (weight) can't be accessed via GraphQL
3. **Vendor Matching** - Need flexible matching for vendor names (spaces, underscores)
4. **Dependencies Matter** - Image scraping requires selenium installation
5. **The System Works!** - Successfully auto-repaired 2/6 missing fields on first run

---

**Status:** Ready to resume when needed. Priority is getting redirect API permissions.
