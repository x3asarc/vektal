# SEO Content Generator

AI-powered SEO content generation for Shopify products using Google Gemini.

## Streamlined Workflow

### 1. Generate SEO Content
Fetch products and generate optimized content:

```bash
# Single product by URL (easiest - just copy from browser!)
python seo/generate_seo_quick.py --url "https://www.bastelschachtel.at/products/pentart-wachspaste-metallic-20ml-silber-3805"

# Single product by handle
python seo/generate_seo_quick.py --handle "pentart-wachspaste-metallic-20ml-silber-3805"

# Single product by barcode
python seo/generate_seo_quick.py --barcode "5997412761382" --output data/product_seo.csv

# Single product by SKU
python seo/generate_seo_quick.py --sku "ABC123" --output data/product_seo.csv

# Batch by vendor
python seo/generate_seo_quick.py --vendor "Pentart" --output data/pentart_seo.csv

# Batch by collection
python seo/generate_seo_quick.py --collection "holiday-items" --output data/holiday_seo.csv

# Batch by title pattern
python seo/generate_seo_quick.py --title "Wachspaste" --output data/wax_seo.csv --limit 25
```

**Output:** CSV file with:
- Original product data (full, not truncated)
- Generated SEO content (meta title, meta description, HTML description)
- Validation results
- Approval column (set to PENDING)

### 2. Review & Approve
1. Open the CSV file in Excel/Google Sheets
2. Review the generated content in these columns:
   - `generated_meta_title` (should be 50-60 chars)
   - `generated_meta_description` (should be 155-160 chars)
   - `generated_description_html` (full HTML content)
3. Check `validation_status` column (PASS/FAIL/ERROR)
4. Edit the `approved` column:
   - `YES` = Push this product to Shopify
   - `NO` = Skip this product
   - `PENDING` = Not ready (default)
5. You can also manually edit any generated content if needed
6. Save the CSV file

### 3. Push to Shopify
Push only the approved products:

```bash
python seo/generate_seo_quick.py --push-csv data/pentart_seo.csv
```

**What happens:**
- Reads the CSV file
- Filters rows where `approved = YES`
- Updates those products in Shopify:
  - Product description HTML
  - Meta title (via metafield `global.title_tag`)
  - Meta description (via metafield `global.description_tag`)
- Generates push report: `data/seo_push_report_[timestamp].md`

## File Structure After Workflow

```
data/
├── backups/
│   └── backup_20250130_103000_pentart_25_products.json  # Original data backup
├── pentart_seo.csv                                      # Working file (review & approve here)
└── seo_push_report_20250130_105030.md                  # Push results
```

## Available Filters

| Filter | Description | Example |
|--------|-------------|---------|
| `--url` | Single product by URL | `--url "https://www.bastelschachtel.at/products/product-handle"` |
| `--handle` | Single product by handle | `--handle "pentart-wachspaste-metallic-20ml-silber-3805"` |
| `--sku` | Single product by SKU | `--sku "ABC123"` |
| `--barcode` | Single product by barcode | `--barcode "5997412761382"` |
| `--vendor` | All products from vendor | `--vendor "Pentart"` |
| `--collection` | All products in collection | `--collection "holiday-items"` or `--collection "gid://shopify/Collection/123"` |
| `--title` | Products matching title pattern | `--title "Wachspaste"` |

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `--output` | `data/seo_preview.csv` | Output CSV file path |
| `--limit` | `50` | Max products to process (for batch operations) |
| `--model` | `gemini-2.5-flash` | Gemini AI model to use |

## CSV Columns

**Product Identification:**
- `product_id` - Shopify GID (for updates)
- `sku` - Product SKU
- `barcode` - Product barcode
- `product_title` - Product name
- `vendor` - Brand/vendor name

**Original Content:**
- `original_meta_title` - Current meta title (falls back to product title)
- `original_meta_description` - Current meta description
- `original_description_html` - Current product description (full HTML)

**Generated Content:**
- `generated_meta_title` - AI-generated meta title
- `generated_meta_description` - AI-generated meta description
- `generated_description_html` - AI-generated product description (full HTML)

**Validation:**
- `validation_status` - PASS/FAIL/ERROR
- `validation_notes` - Validation messages

**Approval:**
- `approved` - PENDING/YES/NO (edit this to approve)

## SEO Best Practices (2026)

The generator follows these best practices:

**Meta Title:**
- 50-60 characters
- Primary keyword at the start
- Include brand name if space allows
- Unique and compelling

**Meta Description:**
- 155-160 characters
- Important info at the front (mobile-first)
- Include call-to-action
- Natural keyword integration
- Answer search intent

**Product Description:**
- 300-500 words
- HTML formatted with proper structure
- Bullet points for features
- Technical specifications
- FAQ section (2-3 common questions)
- Natural language, benefit-focused
- Optimized for AI parsing (Google SGE, etc.)

## Backup & Safety

- Original product data is **always backed up** before generation
- Backups saved to: `data/backups/backup_[timestamp]_[info].json`
- Approval workflow prevents accidental updates
- Only products marked `approved=YES` are updated
- Push report documents all changes

## Troubleshooting

**Q: No products found**
- Check that the filter matches existing products
- Verify Shopify credentials in `.env`

**Q: Validation fails (FAIL status)**
- Review `validation_notes` column
- Common issues: title too long/short, description too brief
- You can manually edit generated content in CSV before approval

**Q: Push fails for some products**
- Check the push report: `data/seo_push_report_[timestamp].md`
- Common issues: Invalid product ID, permissions, rate limits

**Q: CSV content looks cut off in Excel**
- Excel may truncate cell display - double-click cell to see full content
- Use "Wrap Text" for better viewing
- Content is stored in full - truncation is visual only

## Quick Start Example

```bash
# 1. Generate for all Pentart products
python seo/generate_seo_quick.py --vendor "Pentart" --output data/pentart_seo.csv

# 2. Open data/pentart_seo.csv in Excel

# 3. Review generated content, change "approved" to YES for good ones

# 4. Save CSV and push
python seo/generate_seo_quick.py --push-csv data/pentart_seo.csv

# 5. Check results in data/seo_push_report_[timestamp].md
```

## Related Files

- `seo_generator.py` - Core classes (generator, fetcher, updater)
- `seo_prompts.py` - AI prompt templates (German market optimized)
- `seo_validator.py` - Content validation logic
- `QUICKSTART.md` - Quick reference guide
- `IMPLEMENTATION.md` - Technical implementation details
