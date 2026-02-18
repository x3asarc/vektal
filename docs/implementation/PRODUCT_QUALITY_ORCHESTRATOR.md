

# Product Quality Orchestrator System

## Overview

The **Product Quality Orchestrator** is an automated system that monitors product completeness, identifies missing fields, and automatically dispatches repair jobs to fix issues.

## How It Works

```
Product Update Event (image scrape, SEO update, etc.)
    ↓
Quality Agent Triggered
    ↓
Fetches product from Shopify
    ↓
Checks against quality rules:
    ✓ Has barcode?
    ✓ Has country of origin?
    ✓ Has HS code?
    ✓ Has weight?
    ✓ Has SEO metadata?
    ✓ Has images (min 1, ideal 3)?
    ✓ Has proper description?
    ✓ Has tags (min 3)?
    ✓ Has collections?
    ✓ URL handle matches title?
    ↓
Calculates completeness score (0-100)
    ↓
Identifies missing fields
    ↓
Dispatches repair jobs automatically:
    → Missing images? → image_scraper.py
    → Missing SEO? → seo/generate_seo_quick.py
    → Missing barcode? → search_barcode.py
    → Missing logistics? → utils/enrich_product_logistics.py
    → Wrong URL handle? → utils/fix_product_handles.py
    → Missing tags? → utils/generate_product_tags.py
    → Missing collections? → utils/assign_collections.py
    → Missing category? → utils/categorize_product.py
    ↓
Updates master tracking file
    ↓
Reports: "Product is now 95% complete"
```

## Key Files

### Configuration
- `config/product_quality_rules.yaml` - Defines what makes a complete product

### Core System
- `orchestrator/product_quality_agent.py` - Main orchestrator agent
- `orchestrator/trigger_quality_check.py` - Integration helper functions
- `data/product_quality_master.json` - Master tracking file (auto-created)

### Repair Scripts
- `utils/enrich_product_logistics.py` - Adds country of origin, HS code, weight
- `utils/fix_product_handles.py` - Fixes URL handles to match titles
- `utils/generate_product_tags.py` - Generates product tags using AI
- `utils/assign_collections.py` - Assigns products to collections
- `utils/categorize_product.py` - Sets product type/category
- `seo/generate_seo_quick.py` - Generates SEO content
- `image_scraper.py` - Scrapes product images
- `search_barcode.py` - Finds product barcodes

## Usage

### 1. Check Single Product

```bash
python orchestrator/product_quality_agent.py --sku "ABC123"
```

This will:
- Fetch product from Shopify
- Check against quality rules
- Show completeness score
- List missing fields
- Show what repair jobs would run

### 2. Check and Auto-Repair

```bash
python orchestrator/product_quality_agent.py --sku "ABC123" --auto-repair
```

This will:
- Check product quality
- **Automatically execute repair scripts** to fix issues
- Update master tracking file

### 3. Check All Products Needing Repair

```bash
python orchestrator/product_quality_agent.py --check-all --limit 50 --auto-repair
```

This will:
- Find all products with missing fields
- Sort by priority (most missing first, then FIFO)
- Process up to 50 products
- Auto-repair each one

### 4. Integrate with Existing Scripts

Add this to the end of your scripts:

```python
# At the top of your script
from orchestrator.trigger_quality_check import after_seo_update

# After your updates
if success:
    after_seo_update(sku)  # Triggers quality check and auto-repair
```

Integration examples:
- `after_image_scrape(sku)` - After image scraping
- `after_seo_update(sku)` - After SEO generation
- `after_barcode_found(sku)` - After barcode update
- `after_bulk_import(sku)` - After product creation

## Required Fields

Every product must have:

### Core Identification
- ✅ SKU
- ✅ Barcode

### Logistics (for shipping)
- ✅ Country of origin (metafield)
- ✅ HS code (metafield)
- ✅ Product weight

### Content
- ✅ Product title
- ✅ Product description (min 200 chars)
- ✅ Images (min 1, ideal 3)

### SEO
- ✅ SEO meta title (30-60 chars)
- ✅ SEO meta description (120-160 chars)

### Organization
- ✅ Vendor
- ✅ Product type/category
- ✅ Tags (min 3)
- ✅ Collections (min 1)
- ✅ URL handle (matches title)

## Completeness Score

Products are scored 0-100 based on missing fields:
- **100**: Perfect, all fields present
- **90-99**: Nearly complete, 1-2 minor fields missing
- **70-89**: Good, some fields missing
- **50-69**: Incomplete, multiple important fields missing
- **0-49**: Very incomplete, most fields missing

## Master Tracking File

The system maintains `data/product_quality_master.json`:

```json
{
  "products": {
    "gid://shopify/Product/123": {
      "sku": "ABC123",
      "vendor": "Pentart",
      "title": "Product Name",
      "first_checked": "2026-01-30T10:00:00",
      "last_checked": "2026-01-30T14:30:00",
      "completeness_score": 85,
      "missing_count": 2,
      "missing_fields": ["collections", "hs_code"],
      "status": {
        "sku": {"complete": true, "message": "✓ Complete"},
        "barcode": {"complete": true, "message": "✓ Complete"},
        "images": {"complete": true, "message": "✓ Complete (3 items)"},
        "collections": {"complete": false, "message": "Insufficient (0, need 1)"},
        "hs_code": {"complete": false, "message": "Missing HS code"}
      },
      "pending_repairs": [
        {"field": "collections", "script": "utils/assign_collections.py"},
        {"field": "hs_code", "script": "utils/enrich_product_logistics.py"}
      ],
      "repair_history": [
        {"timestamp": "2026-01-30T14:30:00", "trigger": "seo_update", "score_after": 85},
        {"timestamp": "2026-01-30T12:00:00", "trigger": "image_scrape", "score_after": 75}
      ]
    }
  },
  "stats": {},
  "last_updated": "2026-01-30T14:30:00"
}
```

This file:
- ✅ Tracks every product's completeness
- ✅ Shows what's missing
- ✅ Records repair history
- ✅ Can be converted to dashboard later
- ✅ Easy to read and process

## Vendor-Specific Rules

Different vendors can have different requirements.

In `config/product_quality_rules.yaml`:

```yaml
vendor_rules:
  Pentart:
    images:
      min_count: 3  # Pentart products need 3+ images
    tags:
      min_count: 5  # Need more tags
```

## Priority System

Products are fixed in this order:
1. **Most missing fields first** (worst products first)
2. **FIFO within same level** (oldest checked first)

Example:
- Product A: 5 missing fields, checked 2 hours ago
- Product B: 5 missing fields, checked 1 hour ago
- Product C: 3 missing fields, checked 3 hours ago

Order: A → B → C (A and B have more missing, A is older)

## Automation Workflow

### Scenario: New Product Added

```bash
# 1. Product imported from vendor CSV
python scripts/import_pentart_catalog.py

# 2. Quality check triggered automatically (from script)
# → Detects: missing images, missing SEO, missing tags, wrong handle

# 3. Repair jobs dispatched:
#    - image_scraper.py runs → finds 3 images
#    - seo/generate_seo_quick.py runs → generates SEO content
#    - utils/generate_product_tags.py runs → adds 5 tags
#    - utils/fix_product_handles.py runs → fixes URL

# 4. Quality check runs again
# → Product now 95% complete (only HS code missing - needs manual input)
```

### Scenario: SEO Update

```bash
# User runs: /seo-update ABC123

# After SEO push succeeds:
# → Quality check triggered automatically
# → Detects: still missing barcode
# → Dispatches: search_barcode.py
# → Barcode found and added
# → Product now 100% complete!
```

## Example Output

```
======================================================================
Product Quality Orchestrator Agent
======================================================================

[1/3] Fetching product: ABC123
[OK] Found: Pentart Wachspaste Gold 20ml

[2/3] Checking quality...

   Completeness Score: 75/100
   Missing Fields: 4

   Missing:
      ✗ country_of_origin: Missing Country of origin (metafield)
      ✗ hs_code: Missing Harmonized System code (metafield)
      ✗ tags: Insufficient (1, need 3)
      ✗ collections: Insufficient (0, need 1)

[3/3] Updating master record...
[OK] Updated: data/product_quality_master.json

   Found 4 repair job(s) needed:
   [1] country_of_origin: utils/enrich_product_logistics.py --sku ABC123
   [2] hs_code: utils/enrich_product_logistics.py --sku ABC123
   [3] tags: utils/generate_product_tags.py --sku ABC123
   [4] collections: utils/assign_collections.py --sku ABC123

[AUTO-REPAIR] Dispatching repair jobs...

   [1] country_of_origin: utils/enrich_product_logistics.py --sku ABC123
       → Executing...
       ✓ Success

   [2] hs_code: utils/enrich_product_logistics.py --sku ABC123
       → Executing...
       ✓ Success

   [3] tags: utils/generate_product_tags.py --sku ABC123
       → Executing...
       ✓ Success

   [4] collections: utils/assign_collections.py --sku ABC123
       → Executing...
       ✓ Success

[OK] Executed 4 repair job(s)

======================================================================
COMPLETE
======================================================================
```

## Customization

### Add New Required Field

Edit `config/product_quality_rules.yaml`:

```yaml
required_fields:
  my_custom_field:
    required: true
    description: "My custom field"
    metafield:
      namespace: "custom"
      key: "my_field"
    repair_script: "utils/populate_my_field.py"
    repair_args: "--sku {sku}"
```

### Add Vendor-Specific Logistics Data

Edit `vendor_configs.yaml`:

```yaml
Pentart:
  country_of_origin: "HU"  # Hungary
  default_hs_code: "3213.10.00"  # Paints
  default_weight: 0.15  # 150g average
```

### Create Custom Repair Script

```python
# utils/my_custom_repair.py
import sys
import argparse
from seo.seo_generator import ShopifyClient

def repair(sku):
    # Your repair logic here
    print(f"Repairing: {sku}")
    # ... fetch, fix, update ...
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sku", required=True)
    args = parser.parse_args()
    sys.exit(0 if repair(args.sku) else 1)
```

## Best Practices

1. **Run quality checks after every operation**
   - Always trigger after updates
   - Use `--auto-repair` to fix issues immediately

2. **Review master file regularly**
   - Check `data/product_quality_master.json`
   - Identify patterns (which fields always missing?)

3. **Enrich vendor configs**
   - Add logistics defaults for each vendor
   - Saves time on HS codes, weights, country of origin

4. **Monitor repair scripts**
   - Some repairs may fail (API limits, missing data)
   - Check logs and retry if needed

5. **Use priority system**
   - Fix worst products first
   - FIFO ensures old issues get addressed

## Scheduled Runs

Run quality checks regularly:

```bash
# Daily: Check and repair all products needing attention
python orchestrator/product_quality_agent.py --check-all --limit 100 --auto-repair
```

Add to cron/Task Scheduler:
```
0 2 * * * cd /path/to/project && ./venv/Scripts/python.exe orchestrator/product_quality_agent.py --check-all --auto-repair
```

## Dashboard Integration (Future)

The `product_quality_master.json` file is designed for easy dashboard integration:

- Convert to database (SQLite/Postgres)
- Build web dashboard showing:
  - Overall store completeness score
  - Products needing attention
  - Recent repairs
  - Vendor comparison
  - Field-specific issues

## Troubleshooting

**"Product not found"**
- Verify SKU exists in Shopify
- Check authentication credentials

**"Repair script failed"**
- Check script logs
- Verify dependencies installed
- Some repairs need external data (barcodes, etc.)

**"Authentication failed"**
- Check `.env` file credentials
- Verify Shopify API access

**Master file too large**
- Archive old data periodically
- Keep only last 90 days of history

## Next Steps

1. **Test with single product:**
   ```bash
   python orchestrator/product_quality_agent.py --sku "YOUR_SKU"
   ```

2. **Test auto-repair:**
   ```bash
   python orchestrator/product_quality_agent.py --sku "YOUR_SKU" --auto-repair
   ```

3. **Integrate into scripts:**
   - Add trigger calls to your existing scripts

4. **Run scheduled checks:**
   - Set up daily/weekly automated runs

5. **Monitor and improve:**
   - Review master file
   - Adjust quality rules
   - Enhance repair scripts

---

**Ready to ensure 100% complete product data!** 🎯
