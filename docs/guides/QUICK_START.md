# Quick Start Guide - Product Creation Feature

## 🚀 Get Started in 5 Minutes

### Step 1: Verify Installation
```bash
# Check database migrated successfully
python src/app.py
# Look for: "Pentart database initialized successfully"
```

### Step 2: Run Tests (Optional)
```bash
# Test the new methods
python test_product_creation.py
```

### Step 3: Prepare Test CSV
Edit `test_data/sample_new_products.csv` with SKUs that don't exist in your store:
```csv
Handle,SKU,Vendor
test-1,YOUR-NEW-SKU-1,Aistcraft
test-2,YOUR-NEW-SKU-2,Pentart
```

### Step 4: Upload & Process
1. Start app: `python src/app.py`
2. Go to: http://localhost:5000
3. Upload CSV
4. Watch job progress

### Step 5: Verify Safety
```bash
# Run the critical safety check
sqlite3 data/scraper.db -header -column "SELECT * FROM job_results WHERE inventory_set = 1 AND product_created = 0;"
# Must return NO ROWS!
```

---

## 📊 What Happens

### For NEW Products (SKU not in Shopify)
1. ✅ Created as DRAFT
2. ✅ Title, vendor, SKU set
3. ✅ Barcode, price, weight added
4. ✅ Country, HS code set
5. ✅ Image uploaded
6. ✅ **Inventory set to 0**
7. ✅ Activated to ACTIVE
8. ✅ Status: "Created"

### For EXISTING Products (SKU in Shopify)
1. ✅ Metadata updated
2. ✅ Old images deleted
3. ✅ New image uploaded
4. ✅ Barcode, cost, HS code updated
5. ❌ **Inventory NOT changed**
6. ✅ Status: "Updated"

---

## 🔒 Safety Guarantees

### The Golden Rule
**Inventory is ONLY set for products created in the current job.**

### How It Works
```python
# Session-scoped tracking
newly_created_products = set()

# Only these products can have inventory set
if product_id in newly_created_products:
    set_inventory(0)
```

### Verify Safety
```sql
-- This MUST return 0 rows
SELECT * FROM job_results WHERE inventory_set = 1 AND product_created = 0;
```

---

## 📋 Status Codes

| Status | Meaning | Action Taken |
|--------|---------|--------------|
| `Created` | New product created | Product created, inventory set to 0 |
| `Updated` | Existing product updated | Metadata updated, inventory unchanged |
| `New Product - Not Found` | Would create but no data | Skipped, no product created |
| `Not Found` | Existing product, no data | Skipped, no changes |
| `Error` | Operation failed | Check error_message column |

---

## 🗂️ Database Schema

### New Columns - `job_results`
- `product_created` - Was product created? (1/0)
- `product_id` - Shopify product GID
- `variant_id` - Shopify variant GID
- `inventory_set` - Was inventory set? (1/0)
- `inventory_quantity` - Quantity set

### New Columns - `jobs`
- `created_count` - # products created
- `updated_count` - # products updated
- `inventory_set_count` - # inventory operations

---

## 🧪 Testing

### Test Script
```bash
python test_product_creation.py
```

### Test Data
- `test_data/sample_new_products.csv` - New products
- `test_data/sample_existing_products.csv` - Existing products
- `test_data/sample_mixed_products.csv` - Mixed batch

### Safety Audit
```bash
sqlite3 data/scraper.db < safety_audit.sql
```

---

## 🛠️ Troubleshooting

### "Could not get default location"
**Fix**: Ensure location is active in Shopify Settings → Locations

### Product created but image failed
**Fix**: Product exists as DRAFT, re-run or upload image manually

### Safety audit returns rows
**Fix**: STOP! This is critical. Review implementation before proceeding.

### Products stuck as DRAFT
**Fix**: Activation failed. Manually activate in Shopify admin.

---

## 📚 Full Documentation

- **Complete Guide**: `PRODUCT_CREATION_GUIDE.md`
- **Implementation Details**: `IMPLEMENTATION_SUMMARY.md`
- **Test Data Info**: `test_data/README.md`
- **Safety Queries**: `safety_audit.sql`

---

## ⚠️ Important Notes

1. **Always test with small batches first** (5-10 products)
2. **Run safety audit after every job**
3. **Monitor the logs** during processing
4. **Verify in Shopify admin** after job completes
5. **Inventory is NEVER modified on existing products**

---

## ✅ Success Checklist

- [ ] Database migrated successfully
- [ ] Test script passes all tests
- [ ] Test CSV uploaded and processed
- [ ] Safety audit returns 0 rows
- [ ] New products visible in Shopify as ACTIVE
- [ ] Existing products updated without inventory changes
- [ ] Job statistics look correct
- [ ] Ready for production!

---

## 🎯 Next Steps

1. **Update test CSV with real SKUs**
2. **Process test batch**
3. **Run safety audit**
4. **Verify in Shopify**
5. **Scale to production batches**

---

## Support

Questions? Review the comprehensive guide:
```bash
cat PRODUCT_CREATION_GUIDE.md
```
