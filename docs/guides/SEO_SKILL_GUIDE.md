# SEO Update Skill - Quick Reference

## Super Simple Workflow

Just paste a product identifier and approve the changes. That's it!

## Usage

```
/seo-update ABC123
```

or

```
/seo-update 1234567890
```

or just tell Claude naturally:

```
"Update SEO for SKU ABC123"
```

## What Happens

1. **You provide** a product identifier:
   - SKU (e.g., "ABC123", "2493")
   - Barcode (e.g., "1234567890", "5998294510048")
   - Product URL (e.g., "https://yourstore.myshopify.com/admin/products/123456")

2. **Claude generates** SEO content:
   - Fetches the product from Shopify
   - Generates optimized meta title, meta description, and product description
   - Shows you original vs. generated content side-by-side

3. **You review** the changes:
   - Claude displays the comparison in a clear format
   - You see exactly what will change

4. **You approve** by saying "yes":
   - Claude pushes the changes to Shopify immediately
   - You get a confirmation message

## What Gets Generated

The AI creates (in German):
- **Meta Title** (50-60 chars) - Optimized for search engines
- **Meta Description** (155-160 chars) - Compelling with call-to-action
- **Product Description HTML** (300-500 words) - Structured content with:
  - Product overview
  - Bullet points of key features
  - Usage instructions
  - FAQ section

## Example Session

```
You: /seo-update 2493

Claude:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Product: Pentart Wachspaste Gold 20ml
SKU: 2493 | Barcode: 5998294510048 | Vendor: Pentart
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

META TITLE
CURRENT: Pentart Wachspaste Gold 20ml
NEW: Pentart Wachspaste Gold 20ml - Kreative Wachspaste

META DESCRIPTION
CURRENT: (empty)
NEW: Hochwertige Pentart Wachspaste in Gold, 20ml. Perfekt für kreative Bastel- und Dekorationsprojekte. Jetzt online bestellen!

PRODUCT DESCRIPTION
[Shows comparison of descriptions]

Validation: ✓ PASS - All validations passed

Would you like to push these changes to Shopify?

You: yes

Claude: ✓ Successfully updated product on Shopify!
```

## Safety Features

- **Backups:** Original data automatically backed up before changes
- **Preview First:** Always shows you changes before applying
- **Manual Approval:** Nothing happens without your "yes"
- **Validation:** Checks content against SEO best practices
- **Reports:** Detailed report saved to `data/seo_push_report_[timestamp].md`

## Tips

- Start with a single product to test
- Claude auto-detects if you provide SKU, barcode, or URL
- You can say "no" to cancel at any time
- If validation fails, you'll be warned but can still proceed
- Full descriptions are saved to CSV even if display is truncated

## Common Commands

Just talk naturally:
- "Update SEO for SKU ABC123"
- "Generate SEO content for barcode 1234567890"
- "Fix the SEO for this product: [paste URL]"
- "Update product 2493's SEO"

## Files & Locations

- **Temp CSV:** `data/temp_seo_approval.csv` (auto-generated during workflow)
- **Backups:** `data/backups/backup_[timestamp]_*.json`
- **Push Reports:** `data/seo_push_report_[timestamp].md`
- **Skill Definition:** `.claude/skills/seo-update.yaml`

## Troubleshooting

**"No products found"**
- Double-check the identifier is correct
- Verify it exists in your Shopify store

**"Authentication failed"**
- Check `.env` file has valid Shopify credentials

**Validation warnings**
- Claude will warn you if content is too long or short
- You can still approve if you want to proceed

---

**Ready?** Just type `/seo-update [your-sku-or-barcode]` and let Claude handle the rest!
