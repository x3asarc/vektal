# Integration Example: Adding Quality Checks to Existing Scripts

## Example 1: Integrate with SEO Generator

Currently when you run `/seo-update`, it only updates SEO fields. Let's make it trigger the quality orchestrator after, which will then fix ANY other missing fields automatically.

### Add to `seo/generate_seo_quick.py`

At the top of the file:
```python
# Add this import
from orchestrator.trigger_quality_check import after_seo_update
```

In the `push_from_csv` function, after the push succeeds (around line 217):
```python
# After this line:
print("=" * 70)

# Add this:
# Trigger quality check for repaired products
print("\n[ORCHESTRATOR] Running quality checks...")
for update in approved_updates:
    sku = update.get("product_title").split()[0]  # Extract SKU from title or metadata
    try:
        after_seo_update(sku)
    except Exception as e:
        print(f"   [WARNING] Quality check failed for {sku}: {e}")
```

### What This Does

Now when you run:
```
/seo-update ABC123
```

The workflow becomes:
1. Generates SEO content ✓
2. You approve ✓
3. Pushes to Shopify ✓
4. **Triggers quality check** (NEW!)
5. **Finds missing fields** (barcode, weight, HS code, etc.)
6. **Auto-dispatches repair scripts**
7. Product becomes 95-100% complete!

## Example 2: Integrate with Image Scraper

### Add to `image_scraper.py`

At the top:
```python
from orchestrator.trigger_quality_check import after_image_scrape
```

After images are successfully scraped and uploaded (around your success message):
```python
# After successful image upload
print(f"✓ Successfully uploaded {len(images)} images")

# Add this:
try:
    after_image_scrape(sku)
except Exception as e:
    print(f"[WARNING] Quality check failed: {e}")
```

### What This Does

Now when images are scraped:
1. Images uploaded ✓
2. **Quality check triggered**
3. Detects missing SEO, tags, collections, etc.
4. **Auto-repairs everything**
5. Product is now fully optimized!

## Example 3: Integrate with Barcode Search

### Add to `search_barcode.py`

At the top:
```python
from orchestrator.trigger_quality_check import after_barcode_found
```

After barcode is found and updated:
```python
# After successful barcode update
print(f"✓ Barcode updated: {barcode}")

# Add this:
try:
    after_barcode_found(sku)
except Exception as e:
    print(f"[WARNING] Quality check failed: {e}")
```

## Example 4: Bulk Import Integration

### Add to `scripts/import_pentart_catalog.py`

At the top:
```python
from orchestrator.trigger_quality_check import after_bulk_import
```

After each product is created/imported:
```python
# After product creation
print(f"✓ Created product: {product_data['title']}")

# Add this:
try:
    after_bulk_import(sku)
except Exception as e:
    print(f"[WARNING] Quality check failed: {e}")
```

### What This Does

During bulk import:
1. Product created with basic data ✓
2. **Quality check triggered immediately**
3. Identifies ALL missing fields
4. **Dispatches all repair jobs in sequence**
5. Product emerges fully complete!

## The Magic: Chain Reaction

The beauty of this system is it creates a **repair chain reaction**:

```
User Action: /seo-update ABC123
    ↓
SEO updated → Quality check triggered
    ↓
Detects: missing barcode, images, tags
    ↓
Dispatch: search_barcode.py (runs) → finds barcode
    ↓
Quality check triggered again (from barcode script!)
    ↓
Detects: missing images, tags
    ↓
Dispatch: image_scraper.py (runs) → finds 3 images
    ↓
Quality check triggered again!
    ↓
Detects: missing tags
    ↓
Dispatch: generate_product_tags.py (runs) → adds 5 tags
    ↓
Quality check triggered final time
    ↓
100% COMPLETE! 🎉
```

## Configuration: Enable Auto-Repair By Default

The trigger functions have `auto_repair=True` by default, so repairs happen automatically. If you want to disable this:

```python
# Manual approval mode
after_seo_update(sku, auto_repair=False)  # Only checks, doesn't repair

# Auto mode (recommended)
after_seo_update(sku, auto_repair=True)  # Checks and repairs
```

## Testing the Integration

### 1. Test with a product missing everything:

```bash
python orchestrator/product_quality_agent.py --sku "TEST123"
```

See what's missing.

### 2. Run with auto-repair:

```bash
python orchestrator/product_quality_agent.py --sku "TEST123" --auto-repair
```

Watch it fix everything!

### 3. Check the master file:

```bash
cat data/product_quality_master.json
```

See the complete tracking data.

## Tips for Integration

1. **Always catch exceptions** - Don't let quality checks break your main scripts
2. **Pass the trigger name** - Helps track what triggered repairs
3. **Enable auto_repair** - Unless you have a reason not to
4. **Log everything** - Quality checks print useful info
5. **Review master file** - Understand what's being fixed

## Disable for Specific Scripts

If you don't want quality checks for a specific script:

```python
# Simply don't add the trigger call
# Or add a flag:

if enable_quality_check:
    after_seo_update(sku)
```

## Full Automation Setup

For completely hands-off operation:

1. **Add triggers to ALL scripts** (SEO, images, barcode, imports)
2. **Set auto_repair=True everywhere**
3. **Schedule daily cleanup run:**
   ```bash
   python orchestrator/product_quality_agent.py --check-all --auto-repair
   ```
4. **Monitor master file** for patterns

Result: Your product data self-heals! 🔧✨

---

**Ready to integrate?** Start with your SEO script, test it, then add to others!
