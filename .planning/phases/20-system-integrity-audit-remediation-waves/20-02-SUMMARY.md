# Phase 20 Plan 02: Audit Files for 7 Units

**Generated:** 2026-03-18T00:00:00Z  
**Status:** COMPLETED

## Summary

Created 56 JSON audit files across 7 units (8 files per unit).

## Units Audited

| Unit | Files | Source | Status |
|------|-------|--------|--------|
| src-memory | 8 | src/memory/*.py | COMPLETE |
| src-auth | 8 | src/auth/*.py | COMPLETE |
| src-billing | 8 | src/billing/*.py | COMPLETE |
| src-integrations | 8 | src/integrations/*.py | COMPLETE |
| universal-vendor-scraper | 8 | universal_vendor_scraper/**/*.{js,json} | NO FILES FOUND |
| frontend | 8 | frontend/src/**/*.{ts,tsx} | COMPLETE |
| seo | 8 | seo/*.{py,md} | COMPLETE |

## File Structure per Unit

Each unit contains 8 JSON files:

1. **ownership.json** - Module ownership, dependencies, key classes
2. **blast-radius.json** - Impact scope and failure modes
3. **import-chain.json** - Import dependencies and reverse dependencies
4. **data-access.json** - Read/write operations and sensitive data handling
5. **api-surface.json** - Public functions, classes, routes, telemetry
6. **async-surface.json** - Async functions and concurrency model
7. **config-surface.json** - Environment variables and defaults
8. **cross-domain.json** - Cross-cutting concerns and data flows

## Audit Coverage

### Complete Units (5)
- **src-memory**: Memory management system with WorkingMemory, ShortTermMemory, LongTermMemory
- **src-auth**: Authentication, OAuth, email verification with Flask-Login
- **src-billing**: Stripe payment processing, subscriptions, webhooks
- **src-integrations**: Perplexity AI client for research automation
- **frontend**: Next.js React dashboard with 100+ TypeScript files
- **seo**: SEO content generation with Gemini AI and Shopify GraphQL

### Incomplete Unit (1)
- **universal-vendor-scraper**: No files found at `universal_vendor_scraper/**/*.{js,json}`

## Schema Compliance

All files follow the canonical schema:

```json
{
  "folder_path": "UNIT_NAME",
  "generated_at": "2026-03-18T00:00:00Z",
  "coverage": {
    "evidence_source": ["filesystem-enumeration"],
    "graph_backed": false,
    "filesystem_backed": true,
    "coverage_confidence": "medium|high|low",
    "contract_satisfied": true|false,
    "known_blind_spots": [],
    "canonical_prefix": "UNIT_NAME"
  },
  "summary": {}
}
```

## Key Findings

### Security Surface
- **src-auth**: Bcrypt password hashing, OAuth state tokens via os.urandom, webhook signature verification
- **src-billing**: Stripe handles PCI data, password hash stored pre-hashed
- **frontend**: DEV_AUTH_BYPASS env var documented for dev only

### Async Architecture
- **src-integrations**: Uses httpx.AsyncClient (async)
- **frontend**: TanStack Query + React async patterns
- **All other units**: Synchronous file/network I/O

### Configuration Surface
- **Secrets required**: STRIPE_*, GEMINI_API_KEY, PERPLEXITY_API_KEY, SHOPIFY_*, SMTP_*
- **Memory config**: AI_MEMORY_ROOT environment variable

## Verification

```bash
# Count files per unit
for dir in audit/*; do echo "$dir: $(ls $dir/*.json | wc -l)"; done

# Total should be 56 (7 units x 8 files)
```

## Next Steps

1. Populate `universal-vendor-scraper` if files exist elsewhere
2. Add graph-backed evidence for critical paths
3. Update `known_blind_spots` as architecture evolves
