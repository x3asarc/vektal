# Scraper Strategy: Python vs JavaScript

## Context

This project has **two scraping implementations** operating in parallel:

1. **Python scraper:** `src/core/scrape_engine.py`, `src/core/image_scraper.py`
   - Libraries: BeautifulSoup4, requests, Selenium (when needed)
   - Integrated directly with pipeline.py

2. **JavaScript scraper:** `universal_vendor_scraper/scraper.js`
   - Library: Playwright (headless Chromium)
   - Standalone, outputs JSON for pipeline consumption

This document clarifies **when to use each scraper**, how they integrate, and the long-term strategy.

## Decision

**Primary scraper: Python** (`src/core/scrape_engine.py`)

**Secondary scraper: JavaScript** (`universal_vendor_scraper/scraper.js`) for JavaScript-heavy sites

Both scrapers read from the same vendor configuration (`config/vendor_configs.yaml`) and output compatible product data structures.

## Rationale

### Use Python When:

✓ **Static HTML pages** - BeautifulSoup parses faster than browser automation (2-5x speed improvement)

✓ **Simple form submissions** - requests library handles POST/GET without browser overhead

✓ **Direct API access** - Some vendors expose JSON endpoints (no HTML parsing needed)

✓ **Integration with pipeline** - Python scraper runs in-process with `pipeline.py` (no subprocess overhead)

✓ **Database fallback** - Pentart uses local SQLite database when vendor site is down

**Typical vendors:** Pentart (static product pages), PaperDesigns (simple search forms)

### Use JavaScript When:

✓ **Single-page applications (SPAs)** - Sites using React/Vue/Angular that render content client-side

✓ **JavaScript-required content** - Product data loaded via AJAX, not in initial HTML

✓ **Complex user interactions** - Scroll-to-load, click-to-reveal, dynamic filters

✓ **Anti-scraping measures** - Sites detecting headless browsers, requiring full browser fingerprint

✓ **Session-based authentication** - OAuth flows, multi-step logins requiring cookies/localStorage

**Typical vendors:** Aistcraft (SPA), ITD Collection (dynamic pricing), Stamperia (JavaScript product gallery)

### Performance Comparison

| Scraper Type | Speed (per product) | Memory Usage | Headless? | Parallelizable? |
|--------------|---------------------|--------------|-----------|-----------------|
| Python (requests) | 0.5-2 seconds | ~50 MB | N/A | Yes (threading) |
| Python (Selenium) | 3-8 seconds | ~200 MB | Yes | Limited (browser instances) |
| JavaScript (Playwright) | 4-10 seconds | ~300 MB | Yes | Yes (browser contexts) |

**Recommendation:** Use Python for static sites to minimize resource usage and maximize speed.

## Current Vendor Assignments

Based on site analysis and scraper implementation:

| Vendor | Scraper | Site Type | Reason |
|--------|---------|-----------|--------|
| **Pentart** | Python | Static HTML | Simple product pages, BeautifulSoup sufficient |
| **ITD Collection** | JavaScript | SPA | React-based site, AJAX-loaded product data |
| **Aistcraft** | JavaScript | SPA | Vue.js application, dynamic content rendering |
| **PaperDesigns** | Python | Static HTML | Server-rendered pages, no JavaScript required |
| **Stamperia** | JavaScript | Mixed | Product gallery uses JavaScript, images lazy-loaded |
| **Ciao Bella** | TBD | Unknown | Scraper not yet implemented (config exists) |

**How to determine scraper type for new vendor:**

1. Visit vendor site in browser
2. Disable JavaScript (Chrome DevTools → Settings → Debugger → Disable JavaScript)
3. Refresh page
4. **If product data still visible:** Use Python scraper
5. **If page blank or shows "Enable JavaScript":** Use JavaScript scraper

## Integration Pattern

### JavaScript → Python Pipeline Flow

JavaScript scraper is **not** called directly by pipeline. Instead, it's used as a **standalone tool** for vendors requiring browser automation.

```
┌──────────────────────────────────────────────────────────┐
│  Option 1: Direct Python Scraper (Integrated)            │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  pipeline.py                                              │
│      ↓                                                    │
│  scrape_engine.scrape_missing_fields()                    │
│      ↓                                                    │
│  image_scraper.scrape_product_info()                      │
│      ↓                                                    │
│  BeautifulSoup/Selenium scrapes vendor site               │
│      ↓                                                    │
│  Returns: {title, price, image_url, weight, ...}          │
│                                                           │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Option 2: JavaScript Scraper (Subprocess)                │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  1. Run JavaScript scraper manually or via CLI:           │
│     $ node scraper.js --vendor aistcraft --sku ABC123     │
│                                                           │
│  2. Scraper outputs JSON to results/scrape_output.json:   │
│     {                                                     │
│       "success": true,                                    │
│       "data": {                                           │
│         "title": "Product Name",                          │
│         "price": "12.99 EUR",                             │
│         "image_url": "https://...",                       │
│         ...                                               │
│       }                                                   │
│     }                                                     │
│                                                           │
│  3. Python pipeline reads JSON as input:                  │
│     pipeline.py → load scrape_output.json → process       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Why this architecture:**

- **Separation of concerns:** Browser automation isolated from pipeline
- **Error handling:** JavaScript scraper failures don't crash pipeline
- **Manual intervention:** Operator can review scraped data before pipeline processing
- **Debugging:** JSON output allows inspection of scraped data

**Future improvement (Phase 2):** Subprocess integration - `scrape_engine.py` calls JavaScript scraper automatically when vendor requires it.

## Configuration

Both scrapers read from the **same canonical source**: `config/vendor_configs.yaml`

### Shared Configuration Structure

```yaml
pentart:
  country_of_origin: "HU"
  default_weight: 0.15
  filename_pattern: "{category}_{product_name}_{sku}"

  scraper:
    enabled: true
    base_url: "https://www.pentacolor.eu"
    search_url: "https://www.pentacolor.eu/kereses?description=0&keyword={sku}"
    fallback_to_database: true  # Python-specific (SQLite DB)

itd:
  country_of_origin: "PL"
  default_weight: 0.03

  scraper:
    enabled: true
    base_url: "https://itdcollection.com"
    search_url: "https://itdcollection.com/search?q={sku}"
    # JavaScript scraper uses direct_search strategy
```

**How each scraper uses config:**

| Field | Python Scraper | JavaScript Scraper |
|-------|----------------|--------------------|
| `base_url` | Constructs search URLs | Base for strategy navigation |
| `search_url` | Direct GET request target | Starting point for search |
| `fallback_to_database` | Triggers Pentart SQLite lookup | Ignored (not applicable) |
| `country_of_origin` | Used for product enrichment | Not used (pipeline handles) |
| `filename_pattern` | Image naming (via framework) | Not used (pipeline handles) |

**Loading config:**

```python
# Python
from src.core.vendor_config import get_vendor_manager
vendor_config = get_vendor_manager().get_config("pentart")
```

```javascript
// JavaScript
const vendorConfig = require(`./vendors/${vendor.toLowerCase()}`);
```

**Note:** JavaScript vendors have standalone config files (`vendors/pentart.js`) mirroring YAML for Node.js compatibility. **YAML is source of truth** - update both when changing vendor config.

## Adding New Vendors

Follow this checklist when adding support for a new vendor:

### Step 1: Analyze Site

1. Visit vendor website
2. Search for a known product SKU/EAN
3. Inspect product page HTML structure
4. Test with JavaScript disabled (determine scraper type)
5. Check for rate limiting, CAPTCHA, or anti-scraping measures

### Step 2: Choose Scraper

**Decision tree:**

```
Is product data visible with JavaScript disabled?
│
├─ YES → Use Python scraper
│   └─ Is site structure complex (AJAX, infinite scroll)?
│       ├─ YES → Consider Selenium (Python) for edge cases
│       └─ NO → Use requests + BeautifulSoup
│
└─ NO → Use JavaScript scraper
    └─ Which strategy?
        ├─ Direct search (vendor has search function)
        ├─ Direct URL (known product URL pattern)
        ├─ Google search (vendor doesn't expose search)
        └─ Experimental (site requires complex interaction)
```

### Step 3: Add Vendor Config

Add to `config/vendor_configs.yaml`:

```yaml
new_vendor:
  country_of_origin: "XX"
  default_weight: 0.05
  filename_pattern: "{product_name}_{sku}"
  alt_text_template: "{product_name} - NewVendor"
  hs_code_default: "9999.00"

  scraper:
    enabled: true
    base_url: "https://newvendor.com"
    search_url: "https://newvendor.com/search?q={sku}"
```

### Step 4: Implement Scraping Strategy

**For Python scraper:**

1. Add vendor-specific logic to `src/core/image_scraper.py` (function: `scrape_product_info()`)
2. Define CSS selectors for product data extraction
3. Handle vendor-specific price formats, image URL patterns
4. Test with `--dry-run` flag

**For JavaScript scraper:**

1. Create `universal_vendor_scraper/vendors/new-vendor.js`:

```javascript
module.exports = {
  name: "NewVendor",
  base_url: "https://newvendor.com",
  search_url: "https://newvendor.com/search?q={sku}",

  selectors: {
    product_link: '.product-card a',
    title: 'h1.product-title',
    price: '.price',
    image: 'img.product-image',
    sku: '.product-sku'
  },

  sku_transform: (sku) => {
    // Optional: transform SKU for search (e.g., remove hyphens)
    return sku.replace(/-/g, '');
  }
};
```

2. Test with: `node scraper.js --vendor new-vendor --sku TEST123`

### Step 5: Test with Dry-Run

**Python scraper:**

```bash
python -m src.cli.main products update-sku --vendor new-vendor ABC123 --dry-run
```

**JavaScript scraper:**

```bash
cd universal_vendor_scraper
node scraper.js --vendor new-vendor --sku ABC123
# Review output JSON
```

### Step 6: Add to Vendor Assignment Table

Update this document (SCRAPER_STRATEGY.md) with vendor assignment:

```markdown
| **NewVendor** | Python/JavaScript | Static/SPA | [Reason] |
```

## Output Format Compatibility

Both scrapers output **compatible data structures** for pipeline consumption.

### Python Scraper Output

```python
# From scrape_engine.scrape_missing_fields()
{
    "title": "Product Title",
    "price": "12.99",
    "image_url": "https://vendor.com/image.jpg",
    "weight": 0.15,
    "country": "HU",
    "product_type": "Paint",
    "tags": "acrylic, craft, art",
    "sku": "ABC123",
    "scraped_sku": "EAN1234567890"  # If EAN found
}
```

### JavaScript Scraper Output

```json
{
  "success": true,
  "data": {
    "title": "Product Title",
    "price": "12.99 EUR",
    "image_url": "https://vendor.com/image.jpg",
    "sku": "ABC123",
    "url": "https://vendor.com/product-page"
  },
  "attempts": [
    {"attempt": 1, "strategy": "Direct Search", "status": "success"}
  ],
  "strategy": "Direct Search"
}
```

**Normalization in pipeline:**

`pipeline.py` normalizes both formats to standard structure before processing:

```python
def normalize_scraped_data(scraped, source="python"):
    if source == "javascript":
        # Map JS output to standard format
        return {
            "title": scraped["data"]["title"],
            "price": extract_price(scraped["data"]["price"]),
            "image_url": scraped["data"]["image_url"],
            # ... other mappings
        }
    else:
        # Python output already in standard format
        return scraped
```

## Error Handling

### Python Scraper Errors

| Error Type | Cause | Fallback |
|------------|-------|----------|
| `ConnectionError` | Vendor site down | Pentart: SQLite DB lookup |
| `Timeout` | Slow vendor response | Retry with longer timeout |
| `ParseError` | Vendor changed HTML structure | Return partial data, log error |
| `Not Found` | SKU doesn't exist on vendor site | Return empty result |

### JavaScript Scraper Errors

| Error Type | Cause | Fallback |
|------------|-------|----------|
| `ValidationFailed` | Scraped product doesn't match SKU | Try next strategy (up to 4 attempts) |
| `BrowserTimeout` | Page load timeout | Increase timeout, retry |
| `SelectorNotFound` | Vendor changed site structure | Try fallback selectors |
| `CAPTCHA` | Anti-scraping triggered | Manual intervention required |

**Retry logic:**

- Python: Single attempt (fast, deterministic)
- JavaScript: 4-attempt cascade (direct → direct-url → experimental → google)

## Future Direction

### Phase 2: Unified Scraper Interface

**Goal:** Single Python entry point that automatically chooses scraper type.

```python
# Future API
from src.core.scraper import scrape_product

result = scrape_product(vendor="aistcraft", sku="ABC123")
# Automatically uses JavaScript scraper for Aistcraft (SPA)
# Transparently handles subprocess communication
```

**Implementation plan:**

1. Create `src/core/scraper.py` (unified interface)
2. Add vendor type detection (static vs SPA) to config
3. Implement subprocess wrapper for JavaScript scraper
4. Standardize output format (both scrapers return same schema)
5. Add retry/fallback logic (Python → JavaScript if Python fails)

### Phase 3: Performance Optimization

**Investigate:**

- Should we migrate all vendors to Playwright for consistency?
  - **Pro:** Single scraper, easier maintenance
  - **Con:** 3-5x slower for static sites, higher memory usage

- Parallel scraping for bulk operations
  - Python: `concurrent.futures` thread pool
  - JavaScript: Playwright browser contexts (share browser instance)

- Caching scraped vendor data
  - TTL-based cache (vendor data changes infrequently)
  - Invalidation strategy (manual or time-based)

**Benchmark needed:** Compare Playwright vs requests for static sites on representative vendor sample.

## Open Questions

Questions requiring user/stakeholder input:

1. **Should we consolidate to single scraper type?**
   - Option A: Migrate all to Playwright (consistency, easier maintenance)
   - Option B: Keep both (optimize for performance per vendor)
   - Recommendation: Defer until Phase 2, measure performance impact

2. **How to handle vendor site changes?**
   - Current: Manual fix when selectors break
   - Future: Automated monitoring (daily scrape test), alerts on failure
   - Question: Is monitoring investment worth it for 8 vendors?

3. **Subprocess integration priority?**
   - Current: JavaScript scraper run manually, JSON imported
   - Future: `scrape_engine.py` calls JS scraper automatically
   - Question: How urgent is this? Current manual approach works.

4. **Rate limiting strategy?**
   - Current: No rate limiting (risk of vendor blocking)
   - Future: Configurable delays per vendor
   - Question: Have we been blocked by any vendor? If no, defer.

## See Also

- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - System architecture overview
- **[config/vendor_configs.yaml](../config/vendor_configs.yaml)** - Vendor configuration source of truth
- **[src/core/scrape_engine.py](../src/core/scrape_engine.py)** - Python scraper implementation
- **[universal_vendor_scraper/scraper.js](../universal_vendor_scraper/scraper.js)** - JavaScript scraper implementation

---

*Document version: 1.0*
*Last updated: 2026-02-03*
*Maintained by: Development team*
