# Phase 1: Universal Vendor Scraper - Context & Decisions

## Project Goal
Create a robust universal vendor scraper using Playwright that works for all 5 vendors (Paperdesigns, Pentart, ITD Collection, AistCraft, Stamperia) and integrates with Shopify product creation.

## Key Decisions

### 1. Search Strategy
**Decision:** Multi-strategy approach with fallbacks

**For vendors WITH search API:**
- Use direct search URL (e.g., Paperdesigns)

**For vendors WITHOUT search API or when search fails:**
- **Strategy 1:** Google site search: `site:vendor.com SKU`
- **Strategy 2:** Google with product name: `"SKU" "product_name" site:vendor.com`
- **Strategy 3:** Manual vendor catalog browsing (last resort)

### 2. Data Validation
**Decision:** Trust-but-verify approach

- Match scraped title against expected title from Shopify
- Acceptable match: Contains key terms (SKU, product type)
- **Not critical** - Most of the time scraper will be right
- Visual verification via screenshots for spot-checking

### 3. Retry Logic - 3 Attempts Framework
**Decision:** Progressive fallback strategy

**Attempt 1: Direct Search**
- Use vendor's search URL
- Wait for JavaScript render
- Extract from search results

**Attempt 2: Google Search + Direct URL**
- If Attempt 1 fails
- Google: `site:vendor.com SKU`
- Navigate to first result
- Extract data

**Attempt 3: Alternative Selectors**
- If Attempt 2 fails
- Try backup CSS selectors
- Check for mobile version
- Try different product page patterns

**After 3 failures:** Mark as "needs manual review"

### 4. Execution Priority
**Decision:** Fix vendors FIRST, then scrape missing products

**Phase 1a:** Fix all 5 vendors (Pentart, ITD, AistCraft, Stamperia improvements)
**Phase 1b:** Use fixed scrapers to find missing products (views_0167, views_0084, rc003)

### 5. Integration & Workflow
**Decision:** Dry run → Review → Push live

**Step 1: Dry Run**
```
Scrape product → Extract data → Map to Shopify fields → Save as JSON
```

**Shopify Field Mapping:**
```json
{
  "sku": "...",
  "title": "...",
  "vendor": "...",
  "product_type": "Reispapier",
  "price": "...",
  "weight": "30",
  "weight_unit": "g",
  "country_of_origin": "IT/HU/PL/etc",
  "hs_code": "4823.90",
  "image_url": "...",
  "description": "...",
  "tags": ["bastelpapier", "decoupage", "vendor_name"],
  "inventory_quantity": "..."
}
```

**Step 2: Review**
- Show formatted data matching Shopify structure
- User reviews and approves

**Step 3: Push Live**
- Create product in Shopify
- Upload images
- Set inventory levels
- Activate product

## Technical Constraints
- **Rate Limiting:** 3 seconds between requests per vendor
- **Timeout:** 30 seconds per page load
- **Screenshots:** Save for debugging (search page + product page)
- **Logging:** Detailed logs for troubleshooting

## Success Criteria
- ✅ All 5 vendors scraping successfully
- ✅ 95%+ accuracy on product matching
- ✅ Complete data extraction (title, price, image, description)
- ✅ Retry logic handles failures gracefully
- ✅ Dry run shows proper Shopify-formatted data
- ✅ Missing 4 Paperdesigns products found and created

## Out of Scope
- Bulk catalog scraping (only on-demand SKUs)
- Price monitoring/updates
- Automatic re-scraping on schedule
