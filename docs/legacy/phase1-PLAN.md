# Phase 1: Universal Vendor Scraper - Implementation Plan

## Overview
Create production-ready universal vendor scraper with 3-attempt retry logic and Shopify integration.

---

## Architecture

```
universal_vendor_scraper/
├── scraper.js              # Main scraper with retry logic
├── vendors/                # Vendor-specific configs
│   ├── paperdesigns.js
│   ├── pentart.js
│   ├── itd.js
│   ├── aistcraft.js
│   └── stamperia.js
├── strategies/             # Search strategies
│   ├── direct-search.js    # Attempt 1: Vendor search
│   ├── google-search.js    # Attempt 2: Google site search
│   └── fallback.js         # Attempt 3: Alternative selectors
├── utils/
│   ├── shopify-mapper.js   # Map scraped data to Shopify fields
│   ├── validator.js        # Validate extracted data
│   └── logger.js           # Detailed logging
└── integration/
    ├── dry-run.js          # Generate preview data
    └── create-product.js   # Push to Shopify
```

---

## Implementation Steps

### Step 1: Refactor Core Scraper (2 hours)
**File:** `scraper.js`

**Features:**
- [ ] Extract retry logic into separate function
- [ ] Implement 3-attempt strategy pattern
- [ ] Add detailed logging at each step
- [ ] Save screenshots per attempt
- [ ] Rate limiting (3 sec between vendors)
- [ ] Timeout handling (30 sec per page)

**Key Functions:**
```javascript
async function scrapeWithRetry(vendor, sku, maxAttempts = 3)
async function attemptStrategy(strategy, vendor, sku)
async function validateResult(data, expectedTitle)
```

---

### Step 2: Implement Search Strategies (3 hours)

#### Strategy 1: Direct Vendor Search
**File:** `strategies/direct-search.js`

- Use vendor's search URL
- Wait for JavaScript rendering
- Extract from search results
- Navigate to product page

#### Strategy 2: Google Site Search
**File:** `strategies/google-search.js`

- Construct Google query: `site:vendor.com SKU`
- Parse Google results
- Extract first matching URL
- Navigate and scrape

#### Strategy 3: Fallback Selectors
**File:** `strategies/fallback.js`

- Try alternative CSS selectors
- Check mobile version
- Try different URL patterns
- Last resort: mark for manual review

---

### Step 3: Fix Vendor Configs (2 hours)
**Files:** `vendors/*.js`

#### Paperdesigns ✅
- Already working
- Add Google search fallback

#### Pentart ❌
**Issues:**
- Search not finding products
- Wrong selectors

**Fix:**
- Test actual website structure
- Update selectors
- Add Google search as primary

#### ITD Collection ⚠️
**Issues:**
- Finding wrong products
- Need better matching

**Fix:**
- Improve search query (exact SKU match)
- Validate against expected title
- Add SKU verification step

#### AistCraft ❌
**Issues:**
- Products not loading

**Fix:**
- Increase wait time for JavaScript
- Try PrestaShop-specific selectors
- Add Google search fallback

#### Stamperia ⚠️
**Issues:**
- Redirecting to wrong page

**Fix:**
- Improve product link detection
- Add WordPress/WooCommerce selectors
- Google search primary strategy

---

### Step 4: Shopify Integration (2 hours)

#### Dry Run Function
**File:** `integration/dry-run.js`

```javascript
Input: { vendor, sku, scrapedData }
Output: {
  shopify_formatted: {
    sku, title, vendor, product_type,
    price, weight, country, hs_code,
    image_url, description, tags,
    inventory_quantity
  },
  scraped_raw: { ...raw data },
  validation: { matched, confidence, warnings }
}
```

**Display Format:**
```
=== DRY RUN: Pentart 2493 ===
Title: Pentart Grundierfarbe 100ml
Price: €3.50
Image: ✓ Found
Description: ✓ Extracted (250 chars)

Shopify Fields:
  SKU: 2493
  Vendor: Pentart
  Product Type: Reispapier
  Weight: 150g
  Country: HU
  HS Code: 3210.00
  Inventory: 0 (to be set)

Validation: ✓ Title matches expected
Status: READY TO PUSH
```

#### Product Creation
**File:** `integration/create-product.js`

- Use existing Shopify client
- Create product with all fields
- Upload image from URL
- Set inventory level
- Return product ID and URL

---

### Step 5: Testing & Validation (1 hour)

#### Test Cases
1. **All 5 vendors** with known SKUs
2. **Retry scenarios** (simulate failures)
3. **Data validation** (match accuracy)
4. **Shopify integration** (dry run output)
5. **Missing products** (views_0167, views_0084, rc003)

#### Success Metrics
- 5/5 vendors working
- <5 seconds average scrape time
- 95%+ title match accuracy
- Complete data fields (no nulls)
- Proper Shopify format

---

## File Structure

```
C:\Users\Hp\Documents\Shopify Scraping Script\
├── universal_vendor_scraper/
│   ├── scraper.js
│   ├── vendors/
│   ├── strategies/
│   ├── utils/
│   └── integration/
├── test/
│   ├── test_all_vendors.js
│   └── test_missing_products.js
├── results/
│   ├── dry-run-{date}.json
│   └── created-products-{date}.json
└── screenshots/
    └── {vendor}_{sku}_{attempt}_{timestamp}.png
```

---

## Timeline
- **Step 1:** Core refactor - 2 hours
- **Step 2:** Strategies - 3 hours
- **Step 3:** Vendor fixes - 2 hours
- **Step 4:** Integration - 2 hours
- **Step 5:** Testing - 1 hour
- **Total:** ~10 hours work

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Google blocking searches | Add delays, rotate user agents |
| Vendor site changes | Multiple selector fallbacks |
| JavaScript not rendering | Increase wait times, check network |
| Wrong products matched | Strict title validation |
| Rate limiting | 3 sec delays, exponential backoff |

---

## Deliverables

1. ✅ `scraper.js` - Production-ready scraper
2. ✅ All 5 vendor configs working
3. ✅ 3-attempt retry framework
4. ✅ Shopify integration (dry run + create)
5. ✅ Test results for 5 vendors
6. ✅ Missing 4 products scraped and created
7. ✅ Documentation and usage guide
