# SEO Generator - Quick Start

## 3-Step Workflow

### Step 1: Generate
```bash
python seo/generate_seo_quick.py --vendor "Pentart" --output data/pentart_seo.csv
```

Creates CSV with original + generated content.

### Step 2: Review & Approve
1. Open `data/pentart_seo.csv`
2. Review generated content
3. Change `approved` column to `YES` for products to update
4. Save file

### Step 3: Push
```bash
python seo/generate_seo_quick.py --push-csv data/pentart_seo.csv
```

Updates approved products in Shopify.

## Common Commands

**Single Product:**
```bash
# By URL (easiest - just copy from browser!)
python seo/generate_seo_quick.py --url "https://www.bastelschachtel.at/products/product-handle"

# By handle
python seo/generate_seo_quick.py --handle "product-handle"

# By barcode
python seo/generate_seo_quick.py --barcode "5997412761382"

# By SKU
python seo/generate_seo_quick.py --sku "ABC123"
```

**Batch Products:**
```bash
# All Pentart products
python seo/generate_seo_quick.py --vendor "Pentart"

# Products in collection
python seo/generate_seo_quick.py --collection "holiday-items"

# Products matching title
python seo/generate_seo_quick.py --title "Wachspaste" --limit 10
```

## What Gets Updated

- **Product description HTML** - Full SEO-optimized content
- **Meta title** - 50-60 character optimized title
- **Meta description** - 155-160 character description

## Files Created

- **Backup:** `data/backups/backup_[timestamp].json` - Original data
- **CSV:** `data/seo_preview.csv` - Review & approve here
- **Report:** `data/seo_push_report_[timestamp].md` - Push results

## CSV Columns to Review

| Column | What to Check |
|--------|---------------|
| `validation_status` | Should be `PASS` |
| `generated_meta_title` | 50-60 characters, looks good? |
| `generated_meta_description` | 155-160 characters, compelling? |
| `generated_description_html` | Full HTML content, well-formatted? |
| `approved` | Change to `YES` to approve |

## Safety Features

- ✓ Original data always backed up
- ✓ No updates without approval
- ✓ Only approved (YES) products get updated
- ✓ Full audit trail in push report

## Need Help?

See full documentation: `seo/README.md`
