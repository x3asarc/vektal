# Phase 2.1: Universal Vendor Scraping Engine

**Status**: Discussion phase - not yet planned
**Created**: 2026-02-08

## Quick Links

- **Context Document**: [`02.1-CONTEXT.md`](./02.1-CONTEXT.md) - Detailed vision, architecture, and open questions
- **Related Work**: `/quickcleanup` - Proven ITD Collection scraping implementation (247/381 success)

## The Vision

Transform vendor-specific scraping code into a **universal, vendor-agnostic engine** where:
- Users add new vendors via YAML config (no code changes)
- System intelligently selects strategy (Playwright, Selenium, Firecrawl)
- SKU validation prevents product mismatches
- Firecrawl discovery automates collection page crawling
- Future customers with ANY vendor work seamlessly

## Key Insights from `/quickcleanup`

✅ **What Worked**:
- Strict SKU pattern validation (prevented A3/A4 mixups)
- Batch processing (50 SKUs optimal)
- Retry logic (4 attempts)
- GSD optimization (pre-mapped URLs = 10x faster)
- Safe backup before apply

❌ **What Was Painful**:
- Manual Firecrawl integration
- Vendor-specific code (can't reuse for other vendors)
- Slow initial discovery (search one-by-one)
- Separate Node.js + Python scripts

## Next Steps

When ready to plan this phase:

```bash
/gsd:discuss-phase 2.1
```

This will:
1. Analyze existing vendor scrapers (ITD, Pentart, Aisticraft, FN Deco, Paper Designs)
2. Design universal engine architecture
3. Create YAML schema for vendor configs
4. Plan Firecrawl integration
5. Define migration strategy from existing scrapers

---

*See CONTEXT.md for complete details captured from user discussion.*
