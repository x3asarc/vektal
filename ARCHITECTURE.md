# Architecture

This document describes the high-level architecture of the Shopify Multi-Supplier Platform.

> **For new developers:** If you want to understand how components fit together, start here. This follows the [ARCHITECTURE.md pattern](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html) - a bird's-eye view of the system, a code map, and key architectural invariants.

## Bird's Eye View

The Shopify Multi-Supplier Platform is a Python-based automation system that maintains accurate, SEO-optimized product catalogs for a Shopify store sourcing from 8+ vendors. The system scrapes vendor websites for product data, enriches it with AI-generated content, and applies changes to Shopify through a controlled approval workflow.

**Major Components:**

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interfaces                         │
├─────────────┬─────────────┬─────────────┬──────────────────┤
│ Flask Web   │ Typer CLI   │ AI Bot      │ CSV Import       │
│ app.py      │ cli/main.py │ ai_bot_*.py │ pipeline.py      │
└─────┬───────┴─────┬───────┴─────┬───────┴────┬─────────────┘
      │             │             │            │
      └─────────────┴─────────────┴────────────┘
                          │
              ┌───────────▼───────────┐
              │   Core Pipeline       │
              │   pipeline.py         │
              └───────────┬───────────┘
                          │
      ┌──────────┬────────┼────────┬──────────┬──────────┐
      │          │        │        │          │          │
┌─────▼────┐ ┌──▼──┐ ┌───▼───┐ ┌──▼──┐ ┌────▼────┐ ┌───▼────┐
│ Resolve  │ │Scrape│ │Enrich │ │Diff │ │ Approve │ │ Apply  │
│Identifier│ │Vendor│ │AI/SEO │ │     │ │ Review  │ │Shopify │
└──────────┘ └──────┘ └───────┘ └─────┘ └─────────┘ └────────┘
                                                           │
                                              ┌────────────▼──────────┐
                                              │  Shopify GraphQL API  │
                                              └───────────────────────┘
```

**Data Flow (Happy Path):**

1. **Input:** User provides product identifier (SKU, EAN, handle, or URL)
2. **Resolve:** `shopify_resolver.py` finds product in Shopify catalog
3. **Scrape:** `scrape_engine.py` fetches current vendor data (price, images, specs)
4. **Enrich:** `vision_engine.py` + `seo_engine.py` generate AI content
5. **Analyze:** `product_analyzer.py` detects SKU/naming issues
6. **Diff:** `diff_engine.py` compares current vs proposed changes
7. **Approve:** Human reviews changes (or auto-approves safe changes)
8. **Apply:** `shopify_apply.py` executes approved changes via GraphQL
9. **Verify:** `image_verifier.py` confirms uploaded images match expected

**Safety:** All operations support dry-run mode. See `CRITICAL_SAFEGUARDS.md` for rollback and approval workflows.

## Code Map

### src/core/ (Production Modules - DO NOT MODIFY WITHOUT REVIEW)

These modules are production-tested and form the core business logic. Changes require testing and approval.

| Module | Purpose | Key Exports | Dependencies |
|--------|---------|-------------|--------------|
| **pipeline.py** | Orchestrates CSV → scrape → enrich → approve → apply | `process_identifier()`, `build_payload()` | All core modules |
| **shopify_resolver.py** | Resolves product identifiers to Shopify products | `ShopifyResolver` | image_scraper (for client) |
| **product_analyzer.py** | Analyzes products for SKU/naming issues | `ProductAnalyzer`, `AnalysisResult` | pentart_db (optional) |
| **image_framework.py** | YAML-driven image transformations | `ImageFramework`, `process_image()` | PIL, vendor_config |
| **image_scraper.py** | Downloads images from vendor websites | `scrape_product_info()`, `ImageScraper`, `ShopifyClient` | requests, selenium |
| **vision_client.py** | Gemini Vision AI integration | `VisionAIClient` | google.generativeai |
| **vision_engine.py** | Vision analysis orchestration | `generate_vision_alt_text()`, `generate_vision_metadata()` | vision_client, vision_cache |
| **vision_cache.py** | Caches Vision AI results | `VisionAltTextCache` | sqlite3 |
| **vision_prompts.py** | Vision AI prompt templates | `PROMPTS` dictionary | - |
| **vendor_config.py** | Vendor-specific scraping configuration | `load_vendor_config()`, `get_vendor_manager()` | yaml |
| **shopify_apply.py** | Applies changes to Shopify via GraphQL | `apply_payload()` | image_scraper (for client) |
| **scrape_engine.py** | Core scraping logic | `scrape_missing_fields()` | image_scraper, vendor_config |
| **diff_engine.py** | Compares before/after product states | `build_diff_and_plan()`, `generate_diff()` | - |
| **hs_code_resolver.py** | HS tariff code lookup | `resolve_hs_code()` | OpenAI API |
| **seo_engine.py** | GPT-4 German SEO content generation | `generate_seo_fields()` | OpenAI API |
| **quality_assessor.py** | Image quality assessment | `evaluate_quality()` | PIL |
| **image_verifier.py** | Verifies uploaded images match expected | `verify_images()` | requests, PIL |
| **paths.py** | Path constants and utilities | `DATA_DIR`, `LOGS_DIR`, `ARCHIVE_DIR` | - |

**Module relationships:**

- `pipeline.py` is the orchestrator - it imports almost all other core modules
- `image_scraper.py` provides `ShopifyClient` used by resolver and apply modules
- `vendor_config.py` is used by scrape/image modules for vendor-specific rules
- Vision modules (`vision_*`) form a subsystem for AI-powered image analysis

### src/ (Application Layer)

| Module | Purpose | When to Use |
|--------|---------|-------------|
| **app.py** | Flask web application with GUI | Interactive product management, bulk operations |
| **ai_bot_server.py** | AI bot integration server | Conversational product updates |
| **bot_server.py** | Bot server base class | Building new bot integrations |

### src/cli/ (Command Line Interface)

Modern Typer-based CLI (consolidated in Phase 1 Plan 02).

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| **main.py** | Typer CLI entry point | `python -m src.cli.main` |
| **commands/products.py** | Product management commands | `shopify-tools products update-sku` |
| **commands/search.py** | Search commands | `shopify-tools search by-sku` |

**Legacy CLI:** `cli/main.py` still exists with deprecation wrapper for backward compatibility.

### universal_vendor_scraper/ (JavaScript Scrapers)

Playwright-based scrapers for JavaScript-heavy vendor sites. See `docs/SCRAPER_STRATEGY.md` for Python vs JavaScript decision criteria.

| File | Purpose |
|------|---------|
| **scraper.js** | Main Playwright scraper entry point |
| **strategies/** | Vendor-specific scraping strategies |
| **vendors/** | Vendor configurations |

### config/ (Configuration Files)

| File | Purpose | Format |
|------|---------|--------|
| **vendor_configs.yaml** | Vendor-specific scraping rules | YAML |
| **image_processing_rules.yaml** | Image transformation rules | YAML |
| **product_quality_rules.yaml** | Quality assessment thresholds | YAML |

### utils/ (Utility Modules)

| Module | Purpose |
|--------|---------|
| **pentart_db.py** | Pentart vendor database lookup |
| **shopify_utils.py** | Shopify API helpers |

### archive/2026-scripts/ (Historical One-Off Scripts)

Organized by category (apply, scrape, fix, dry-run, debug, analysis, test-scripts, misc). See `archive/2026-scripts/MANIFEST.md` for script index.

**Do not use these scripts.** They're archived for reference only. Use the unified CLI instead.

## Data Flow

### Primary Pipeline Flow

```python
# Entry point: pipeline.process_identifier()

1. INPUT VALIDATION
   identifier = {"kind": "sku", "value": "ABC123"}

2. RESOLVE PRODUCT
   resolver = ShopifyResolver()
   product = resolver.resolve_identifier(identifier)
   # → Queries Shopify GraphQL/REST for matching products

3. ANALYZE PRODUCT (optional)
   analyzer = ProductAnalyzer()
   analysis = analyzer.analyze_product(product, identifier)
   # → Detects SKU/naming issues, generates corrections

4. SCRAPE VENDOR DATA
   scraped = scrape_missing_fields(identifier, product, vendor)
   # → Fetches current data from vendor website
   # → Python scraper (BeautifulSoup/Selenium) or JavaScript (Playwright)

5. ENRICH WITH AI
   # Vision AI for images
   alt_text = generate_vision_alt_text(product, scraped, vendor)

   # German SEO content
   seo_fields = generate_seo_fields(product, scraped)

   # HS code lookup
   hs_code = resolve_hs_code(product_type, tags)

6. BUILD DIFF
   diff = build_diff_and_plan(product, scraped, enriched_data)
   # → Compares current vs proposed state
   # → Flags changes requiring approval (SEO, title, HS code)

7. APPROVAL WORKFLOW
   # Human reviews diff, approves/rejects changes
   # (or auto-approves safe changes like weight/price)

8. APPLY CHANGES
   result = apply_payload(payload)
   # → Executes approved changes via Shopify GraphQL
   # → Product update, variant update, image upload

9. VERIFY
   verify_images(product_id, uploaded_images)
   # → Confirms images were uploaded correctly
```

### Image Processing Flow

```python
# Entry point: image_framework.process_image()

1. DOWNLOAD IMAGE
   image_data = requests.get(image_url)

2. APPLY TRANSFORMATIONS (from YAML config)
   - Square aspect ratio (if vendor requires)
   - Remove transparency (if vendor requires)
   - Convert format (PNG → JPG for web)
   - Resize (if needed)

3. GENERATE FILENAME
   # Hybrid AI + SEO approach
   filename = generate_hybrid_filename(product, vendor)
   # Example: "pentart-dekorfolie-sternenhimmel-blau.jpg"

4. GENERATE ALT TEXT
   # Vision AI or fallback
   alt_text = generate_hybrid_alt_text(product, image, vendor)
   # Example: "Pentart Dekorfolie Sternenhimmel Blau 15x20cm"

5. UPLOAD TO SHOPIFY
   # Staged upload (for GraphQL) or simple URL (for REST)
   upload_strategy.execute(image_data, filename, alt_text)

6. POSITION IMAGE
   # Replace primary or append to gallery
   positioning_engine.set_position(image, role="primary")
```

## Cross-Cutting Concerns

### Configuration Management

**Environment Variables (.env):**
- `SHOP_DOMAIN` - Shopify store domain
- `SHOPIFY_ACCESS_TOKEN` - Admin API token
- `OPENAI_API_KEY` - For SEO generation and HS code lookup
- `GOOGLE_GEMINI_API_KEY` - For Vision AI
- `API_VERSION` - Shopify API version (default: 2024-01)

**YAML Configuration:**
- `config/vendor_configs.yaml` - Vendor-specific rules (selectors, transformations)
- `config/image_processing_rules.yaml` - Image transformation rules
- `config/product_quality_rules.yaml` - Quality thresholds

### Safety Mechanisms

**Critical safeguards (see CRITICAL_SAFEGUARDS.md):**

1. **Dry-run mode:** All CLI commands support `--dry-run` flag
2. **Approval workflow:** SEO/title/HS changes require explicit approval
3. **Rollback capability:** Payload files saved before apply for rollback
4. **Image deletion protection:** Never delete images without confirmation
5. **Duplicate detection:** Prevents creating duplicate products
6. **Staged uploads:** Image URLs validated before Shopify upload

**Approval gates:**
- SEO content changes (AI-generated descriptions)
- Product title changes (naming pattern deviations)
- HS code updates (tariff classification changes)

**Auto-approved changes:**
- Price updates from vendor
- Weight/dimensions updates
- Image replacements (same product)
- SKU/EAN corrections (when validated)

### External Integrations

| Service | Purpose | Rate Limits | Caching |
|---------|---------|-------------|---------|
| **Shopify GraphQL API** | Product mutations | 2000 points/second | N/A (live data) |
| **Shopify REST API** | Fallback search | 2 requests/second | ShopifyResolver cache |
| **OpenAI GPT-4** | SEO generation, HS codes | 10,000 TPM | N/A (deterministic) |
| **Google Gemini Vision AI** | Image alt text, metadata | Budget-limited | VisionAltTextCache (SQLite) |
| **Vendor websites (8+)** | Product scraping | Vendor-specific | N/A (live data) |

**API Version:** Currently using Shopify API `2024-01`. Upgrade path in Phase 4.

### Logging and Debugging

**Log files (data/logs/):**
- `pipeline.log` - Main pipeline execution
- `scraper.log` - Scraping operations
- `vision_ai.log` - Vision AI requests/responses
- `shopify_api.log` - GraphQL mutations

**Debug modes:**
- `--verbose` flag for detailed CLI output
- `DEBUG=True` in Flask app for request logging
- Vision cache inspection: `sqlite3 data/vision_cache.db`

### Testing Strategy

**Test organization (from Phase 1 Plan 02):**
```
tests/
├── conftest.py          # Shared fixtures
├── unit/                # Fast, isolated tests
│   └── test_image_framework.py
├── integration/         # External service tests
│   ├── test_vision_ai.py
│   └── test_shopify_api.py
└── cli/                 # CLI command tests
    └── test_commands.py
```

**Run tests:** `pytest tests/`

**Test fixtures (tests/conftest.py):**
- `mock_shopify_client` - Mocked Shopify API
- `temp_data_dir` - Temporary data directory
- `sample_product` - Sample product data

## Architectural Invariants

**These rules must ALWAYS hold:**

1. **src/core/ is production code**
   - Changes require testing and approval
   - No experimental code in core/
   - Archive experimental scripts to archive/

2. **All Shopify mutations go through shopify_apply.py**
   - Never call GraphQL directly from other modules
   - apply_payload() enforces approval gates
   - Rollback data saved before mutations

3. **Vision AI calls are cached**
   - VisionAltTextCache prevents duplicate requests
   - Budget tracking prevents runaway costs
   - Cache invalidation requires explicit action

4. **German language for all SEO content**
   - seo_engine.py hardcoded to German prompts
   - Alt text in German (product descriptions)
   - For other languages, fork seo_engine.py

5. **YAML-driven configuration**
   - Vendor rules in vendor_configs.yaml (not hardcoded)
   - Image transformations in image_processing_rules.yaml
   - Quality thresholds in product_quality_rules.yaml

6. **Scraper selection based on site type**
   - Python (BeautifulSoup/Selenium) for static HTML
   - JavaScript (Playwright) for SPAs and dynamic content
   - See docs/SCRAPER_STRATEGY.md for decision criteria

7. **Approval workflow for destructive changes**
   - SEO content (AI-generated, needs review)
   - Title changes (affects SEO and findability)
   - HS codes (legal/customs implications)

8. **No deletion without confirmation**
   - Images never auto-deleted (only replaced)
   - Products require explicit delete command
   - Variants protected from accidental removal

## Common Workflows

### Workflow 1: Update Product from Vendor

```bash
# Via CLI
python -m src.cli.main products update-sku gid://shopify/ProductVariant/123 "NEW-SKU"

# Via CSV import
python -m src.cli.main products process identifiers.csv

# Via Flask web UI
# Navigate to http://localhost:5000, enter SKU, click "Update"
```

### Workflow 2: Scrape and Enrich New Product

```bash
# Python scraper (static HTML site)
python -m src.cli.main products update-sku --vendor pentart ABC123

# JavaScript scraper (SPA site)
cd universal_vendor_scraper
node scraper.js --vendor aistcraft --sku XYZ789
```

### Workflow 3: Analyze Product for Issues

```python
from src.core.product_analyzer import ProductAnalyzer
from src.core.shopify_resolver import ShopifyResolver

resolver = ShopifyResolver()
analyzer = ProductAnalyzer()

# Resolve product
product = resolver.resolve_identifier({"kind": "sku", "value": "ABC123"})

# Analyze for SKU/naming issues
analysis = analyzer.analyze_product(product, {"kind": "sku", "value": "ABC123"})

if analysis.has_issues():
    print(f"SKU issue: {analysis.sku_issue}")
    print(f"Naming issue: {analysis.naming_issue}")
    print(f"Corrections: {analysis.corrections}")
```

### Workflow 4: Generate Vision AI Alt Text

```python
from src.core.vision_engine import generate_vision_alt_text

product = {...}  # Shopify product
scraped = {"image_url": "https://vendor.com/image.jpg"}

alt_text = generate_vision_alt_text(product, scraped, vendor="pentart")
# → "Pentart Dekorfolie Sternenhimmel Blau 15x20cm transparent"
```

## Architecture Decision Records (ADRs)

### ADR-001: Unified CLI Framework (Typer)

**Context:** 30+ duplicate scripts cluttered root directory, each with slightly different auth/config logic.

**Decision:** Consolidate to single Typer-based CLI at `src/cli/main.py` with subcommands.

**Rationale:**
- Type-hint based API reduces boilerplate
- Automatic help generation
- Shared authentication/config
- Better testing (CliRunner)

**Status:** Implemented (Phase 1 Plan 02)

**Consequences:**
- Old scripts deprecated but kept as wrappers (backward compatibility)
- New commands must use Typer pattern
- CLI tests use `typer.testing.CliRunner`

### ADR-002: YAML-Driven Image Processing

**Context:** Image transformation rules were hardcoded in multiple places, causing inconsistencies.

**Decision:** Centralize ALL image rules in `config/image_processing_rules.yaml`, enforced by `ImageFramework`.

**Rationale:**
- Non-developers can update rules (no code changes)
- Single source of truth
- Version control for rule changes
- Framework validates rules at load time

**Status:** Implemented

**Consequences:**
- Image transformations must go through ImageFramework
- Rule changes require YAML update, not code
- Framework validates YAML schema

### ADR-003: Hybrid Python + JavaScript Scrapers

**Context:** Some vendor sites are static HTML (fast with BeautifulSoup), others are SPAs requiring JavaScript execution.

**Decision:** Maintain both Python (`scrape_engine.py`) and JavaScript (`universal_vendor_scraper/`) scrapers, choose based on site type.

**Rationale:**
- Python faster for static sites (no browser overhead)
- JavaScript required for SPAs and dynamic content
- Integration via JSON output from JS → Python pipeline

**Status:** Implemented (See docs/SCRAPER_STRATEGY.md)

**Consequences:**
- Vendor assignment documented in SCRAPER_STRATEGY.md
- Both scrapers read same YAML config
- JS scraper outputs JSON consumed by pipeline.py

### ADR-004: Vision AI Caching with Budget Tracking

**Context:** Gemini Vision API costs add up quickly when analyzing thousands of images.

**Decision:** SQLite cache in `vision_cache.py` with budget tracking and confidence scoring.

**Rationale:**
- Prevent duplicate API calls for same image URL
- Budget limits prevent runaway costs
- Confidence scores allow re-analysis if needed

**Status:** Implemented

**Consequences:**
- Cache grows over time (requires cleanup strategy)
- Image URL used as cache key (URL changes = cache miss)
- Budget exceeded = graceful degradation (skip Vision AI)

## FAQ for New Developers

**Q: Which module do I modify to change scraping logic?**
A: Depends on vendor type. Python scraper: `src/core/scrape_engine.py`. JavaScript scraper: `universal_vendor_scraper/`. Check `docs/SCRAPER_STRATEGY.md` for vendor assignments.

**Q: How do I add a new vendor?**
A:
1. Add vendor config to `config/vendor_configs.yaml`
2. Determine scraper type (Python vs JS) - see `docs/SCRAPER_STRATEGY.md`
3. Implement scraping strategy in appropriate scraper
4. Test with `--dry-run` before production

**Q: Where are product images stored?**
A: Not stored locally (except temp download). Images uploaded directly to Shopify CDN via GraphQL mutations.

**Q: Can I delete the archived scripts in archive/2026-scripts/?**
A: Not yet. Keep for 6 months (until 2026-08) in case logic needs extraction. See `archive/2026-scripts/MANIFEST.md` for script purposes.

**Q: Why are there two CLI entry points (cli/main.py and src/cli/main.py)?**
A: `cli/main.py` is legacy with deprecation wrapper. Use `src/cli/main.py` (new Typer CLI) going forward.

**Q: How do I test my changes?**
A: Run `pytest tests/` for full suite, or `pytest tests/unit/` for fast tests. Use `--dry-run` flag in CLI for production testing.

**Q: What's the difference between approve/apply workflow?**
A: `build_diff_and_plan()` generates change preview. Human approves via `approve` field. `apply_payload()` executes only approved changes.

## Further Reading

- **[docs/INDEX.md](docs/INDEX.md)** - Complete documentation index
- **[docs/DIRECTORY_STRUCTURE.md](docs/DIRECTORY_STRUCTURE.md)** - Project directory organization
- **[docs/SCRAPER_STRATEGY.md](docs/SCRAPER_STRATEGY.md)** - Python vs JavaScript scraper decision criteria
- **[docs/guides/CRITICAL_SAFEGUARDS.md](docs/guides/CRITICAL_SAFEGUARDS.md)** - Approval workflows and rollback procedures
- **[.planning/ROADMAP.md](.planning/ROADMAP.md)** - Future development plans
- **[archive/2026-scripts/MANIFEST.md](archive/2026-scripts/MANIFEST.md)** - Index of archived scripts

---

*Document version: 1.1*
*Last updated: 2026-02-04 (Phase 1.1 - Root Documentation Organization)*
*Maintained by: Development team*
