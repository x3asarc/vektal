# Product Quality Orchestrator - Quick Start

## What Was Built

I've created a **complete automated system** that monitors product completeness, identifies missing fields, and automatically fixes them by dispatching repair scripts.

## 🎯 What It Does

Every time a product is updated (SEO, images, barcode, etc.), the orchestrator:
1. ✅ Checks product against quality rules
2. ✅ Identifies missing fields
3. ✅ **Automatically dispatches repair scripts**
4. ✅ Tracks everything in master file
5. ✅ Product emerges fully complete

## 📁 Files Created

### Configuration
- `config/product_quality_rules.yaml` - Defines required fields

### Core System
- `orchestrator/product_quality_agent.py` - Main orchestrator (680 lines)
- `orchestrator/trigger_quality_check.py` - Integration helpers
- `orchestrator/__init__.py` - Package init

### Repair Scripts (NEW)
- `utils/enrich_product_logistics.py` - Adds country, HS code, weight
- `utils/fix_product_handles.py` - Fixes URL handles
- `utils/generate_product_tags.py` - Generates tags with AI
- `utils/assign_collections.py` - Assigns to collections
- `utils/categorize_product.py` - Sets product type

### Documentation
- `PRODUCT_QUALITY_ORCHESTRATOR.md` - Complete guide (500+ lines)
- `ORCHESTRATOR_INTEGRATION_EXAMPLE.md` - Integration examples
- `ORCHESTRATOR_QUICK_START.md` - This file!

### Auto-Created Files
- `data/product_quality_master.json` - Master tracking file (created on first run)

## 🚀 Test It Right Now

### 1. Check a product:
```bash
python orchestrator/product_quality_agent.py --sku "DFSA4XSF"
```

This shows:
- Completeness score (0-100)
- Missing fields
- What repairs would run

### 2. Auto-repair a product:
```bash
python orchestrator/product_quality_agent.py --sku "DFSA4XSF" --auto-repair
```

This:
- Checks product
- **Runs repair scripts automatically**
- Fixes everything it can
- Updates master file

### 3. Check all incomplete products:
```bash
python orchestrator/product_quality_agent.py --check-all --limit 10 --auto-repair
```

This:
- Finds products with missing fields
- Sorts by priority (worst first, then FIFO)
- Auto-repairs each one

## 📋 Required Fields (What Gets Checked)

Every product must have:
- ✅ SKU, Barcode
- ✅ Country of origin, HS code, Weight
- ✅ Title, Description (200+ chars)
- ✅ Images (min 1, ideal 3)
- ✅ SEO meta title & description
- ✅ Vendor, Product type
- ✅ Tags (min 3), Collections (min 1)
- ✅ URL handle (matches title)

## 🔗 Integration (Make It Automatic)

### Add to SEO script:
```python
from orchestrator.trigger_quality_check import after_seo_update

# After SEO push succeeds:
after_seo_update(sku)
```

### Add to image scraper:
```python
from orchestrator.trigger_quality_check import after_image_scrape

# After images uploaded:
after_image_scrape(sku)
```

### Add to barcode search:
```python
from orchestrator.trigger_quality_check import after_barcode_found

# After barcode updated:
after_barcode_found(sku)
```

Now every operation triggers quality checks and auto-repairs!

## 📊 Master Tracking File

Check `data/product_quality_master.json` to see:
- Which products are incomplete
- What fields are missing
- Repair history
- Completeness scores

This file can be:
- Read by dashboards
- Converted to database
- Used for reporting
- Monitored over time

## 🎬 Real-World Example

```
User runs: /seo-update ABC123

1. SEO generated and pushed ✓
2. Quality check triggered automatically
3. Detects missing: barcode, images, tags, weight
4. Dispatches repairs:
   → search_barcode.py runs → finds barcode ✓
   → image_scraper.py runs → finds 3 images ✓
   → generate_product_tags.py runs → adds 5 tags ✓
   → enrich_product_logistics.py runs → adds weight ✓
5. Product now 100% complete!

All automatic. No manual intervention needed.
```

## ⚙️ Vendor Configuration

Add logistics defaults to `vendor_configs.yaml`:

```yaml
Pentart:
  country_of_origin: "HU"  # Hungary
  default_hs_code: "3213.10.00"  # Artist's paints
  default_weight: 0.15  # 150g average

Bastelschachtel:
  country_of_origin: "DE"  # Germany
  default_hs_code: "4823.90.00"  # Paper craft supplies
  default_weight: 0.05  # 50g average
```

Now logistics enrichment works automatically!

## 🔄 Workflow Cycle

```
Product Update → Quality Check → Identify Gaps → Auto-Repair → Quality Check Again → ...

Continues until product is 100% complete or no more auto-repairs possible
```

## 📈 Priority System

Products are fixed in order:
1. **Most missing fields first** (worst products prioritized)
2. **FIFO within same level** (oldest first)

Example queue:
- Product A: 8 missing fields ← Fixed first
- Product B: 8 missing fields ← Fixed second
- Product C: 5 missing fields ← Fixed third
- Product D: 2 missing fields ← Fixed fourth

## 🛠️ Custom Repair Scripts

Need a custom repair? Easy:

1. Create script: `utils/my_repair.py`
2. Add to `config/product_quality_rules.yaml`:
   ```yaml
   my_field:
     required: true
     repair_script: "utils/my_repair.py"
     repair_args: "--sku {sku}"
   ```
3. Done! It's now part of the system

## 📅 Scheduled Runs

Set up daily auto-repair:

```bash
# Check and repair all products daily at 2 AM
0 2 * * * cd /path/to/project && ./venv/Scripts/python.exe orchestrator/product_quality_agent.py --check-all --auto-repair
```

## 🎯 Success Metrics

After integration, you'll see:
- ⬆️ Average completeness scores increase
- ⬇️ Products with missing fields decrease
- ⏱️ Time to complete products drops to near-zero
- 🤖 Most repairs happen automatically

## 🎁 Bonus: Chain Reactions

The system creates **repair chain reactions**:

```
SEO update → triggers check
  → finds missing barcode
    → search_barcode.py runs
      → triggers check again
        → finds missing images
          → image_scraper.py runs
            → triggers check again
              → finds missing tags
                → generate_tags.py runs
                  → triggers final check
                    → 100% COMPLETE!
```

All automatic. Self-healing product data.

## 📚 Next Steps

1. **Test with one product:**
   ```bash
   python orchestrator/product_quality_agent.py --sku "YOUR_SKU" --auto-repair
   ```

2. **Check the master file:**
   ```bash
   cat data/product_quality_master.json
   ```

3. **Integrate into your workflows:**
   - Add trigger calls to existing scripts

4. **Set up scheduled runs:**
   - Daily cleanup of incomplete products

5. **Customize rules:**
   - Edit `config/product_quality_rules.yaml`
   - Add vendor-specific requirements

## 💡 Pro Tips

- Start with `--auto-repair` to see it in action
- Review master file to spot patterns
- Add vendor logistics data for better auto-enrichment
- Integrate triggers into all your scripts
- Run scheduled cleanups daily/weekly

## 🆘 Need Help?

Read the comprehensive guide:
```bash
cat PRODUCT_QUALITY_ORCHESTRATOR.md
```

Or integration examples:
```bash
cat ORCHESTRATOR_INTEGRATION_EXAMPLE.md
```

---

**Your product data now self-heals!** 🔧✨🎉
