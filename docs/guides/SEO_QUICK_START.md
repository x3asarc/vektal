# SEO Update - Quick Start

## The Simplest Workflow

### Step 1: Run the command
```
/seo-update 2493
```
(Replace `2493` with your SKU, barcode, or product URL)

### Step 2: Review the changes
Claude will show you a comparison of current vs. generated content.

### Step 3: Approve
Type `yes` when you're happy with the changes.

### Done!
Product is updated on Shopify.

---

## That's It!

The entire workflow happens in the conversation. No CSV files to open, no manual edits needed.

## Example

```
You: /seo-update 2493

Claude: [Fetches product, generates SEO content, shows comparison]

Product: Pentart Wachspaste Gold 20ml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

META TITLE
CURRENT: Pentart Wachspaste Gold 20ml (28 chars)
NEW: Pentart Wachspaste Gold 20ml - Kreative Deko (47 chars)

[... more comparisons ...]

Would you like to push these changes to Shopify? (yes/no)

You: yes

Claude: ✓ Successfully updated product on Shopify!
        Report saved to: data/seo_push_report_20260130_103045.md
```

## What It Does

- **Fetches** your product from Shopify
- **Generates** German SEO content using AI:
  - Meta title (50-60 chars)
  - Meta description (155-160 chars)
  - Product description HTML (300-500 words)
- **Shows** you the changes
- **Pushes** to Shopify when you approve

## Identifiers You Can Use

- **SKU**: `2493`, `ABC123`
- **Barcode**: `5998294510048`, `1234567890`
- **URL**: `https://yourstore.myshopify.com/admin/products/123456`

Claude auto-detects which type you're using.

## Safety

- Creates automatic backups before changes
- Shows you everything before applying
- Requires your explicit "yes" to proceed
- Generates detailed reports

## Tips

- Test with one product first
- Review the generated content carefully
- You can say "no" to cancel anytime
- Check the validation status for warnings

## Files Created

- `data/temp_seo_approval.csv` - Temporary file during process
- `data/backups/backup_*.json` - Original product data
- `data/seo_push_report_*.md` - Update report

## Natural Language Works Too

You don't have to use the slash command:
- "Update SEO for SKU 2493"
- "Generate SEO content for barcode 5998294510048"
- "Fix the SEO for product 2493"

Claude will automatically invoke the skill!

---

**Ready to try?** Type `/seo-update [your-sku]` now!
