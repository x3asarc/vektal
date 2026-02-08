# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, through an intelligent conversational AI interface.
**Current focus:** Phase 2.1 - Universal Vendor Scraping Engine

## Current Position

Phase: 2.2 of 15 (Product Enrichment Pipeline)
Plan: 2 of 6 (Completed)
Status: In progress
Last activity: 2026-02-08 — Completed 02.2-02-PLAN.md (AI Description & SEO Generation)

Progress: [█████░░░░░] 53% (19/36 plans estimated)

## Recent Session Summary (2026-02-08)

**Phase 2.1 Discussion Completed:**
- Discovery strategy: Hybrid (local patterns → known vendors → web search → AI)
- Chat routing: Pattern matcher → LLM classifier (Gemini Flash) → handlers
- AI integration: Local-first, aggressive caching, API fallback
- YAML generation: Auto-generate with LLM verification + user review
- Created comprehensive vendor template: `config/vendors/_template.yaml` (700+ lines)

**Phase 2.2 Created:**
- Product Enrichment Pipeline (AI descriptions, embeddings, quality scoring)
- Integrates `/side-project` patterns
- Runs after 2.1, before Phase 3 database design

## Performance Metrics

**Velocity:**
- Total plans completed: 18
- Average duration: 13 min
- Total execution time: 3.9 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-codebase-cleanup-analysis | 3 | 64 min | 21 min |
| 01.1-root-documentation-organization | 3 | 23 min | 8 min |
| 02-docker-infrastructure-foundation | 4 | 114 min | 29 min |
| 02.1-universal-vendor-scraping-engine | 11 | 93 min | 8 min |
| 02.2-product-enrichment-pipeline | 2 | 45 min | 23 min |

**Recent Trend:**
- Last 5 plans: 02.1-10 (0 min), 02.1-11 (9 min), 02.2-01 (22 min), 02.2-02 (23 min)
- Trend: Phase 2.2 progressing well - AI/SEO generators with 27 tests (23 min)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Cleanup before features: 30+ scripts make codebase unmaintainable; organize first, then build
- Agent-driven refactoring: Leverage awesome-claude-code + GSD for autonomous cleanup
- Docker-first architecture: Scalability requirement; separates concerns, enables multi-tenant future
- Archive by category (01-01): 8-category structure (apply, scrape, fix, dry-run, debug, analysis, test-scripts, misc) for maintainability
- Dead code analysis without deletion (01-01): Document findings with confidence levels; identified 17 false positives in Flask/Click decorators
- Typer CLI framework (01-02): Chose Typer over Click for type hints and automatic validation
- Test organization (01-02): Organized by type (unit/integration/cli) for clarity
- Python primary scraper (01-03): Python for static HTML, JavaScript for SPAs/dynamic sites
- Architecture documentation pattern (01-03): matklad pattern (bird's eye view → code map → invariants → ADRs)
- Architectural invariants (01-03): 8 rules codified (src/core/ protection, approval gates, Vision AI caching, German SEO, YAML config)
- Three-tier documentation structure (01.1-01): docs/ organized into guides/ (users), reference/ (technical), legacy/ (historical)
- Input/output separation (01.1-01): data/ for inputs, results/ for outputs - clearer intent
- Keep demo_framework.py in root (01.1-01): Documentation example referenced in guides
- Archive deprecated directories by purpose (01.1-02): 5 directories archived to archive/2026-directories/ with descriptive names
- Evidence-based investigation (01.1-02): Document evidence, decisions, and rationale before archiving
- Keep active standalone modules in root (01.1-02): seo/, utils/, web/ remain as production-critical modules with imports
- Technical docs in docs/ root (01.1-03): Comprehensive technical docs (SCRAPER_STRATEGY, IMAGE_*, etc.) stay in docs/ root, not subdirectories
- Documentation index structure (01.1-03): Organize by purpose (guides, reference, technical, legacy) for better discoverability
- Debian-over-Alpine for Docker (02-01): python:3.12-slim chosen over Alpine for better Python wheel compatibility
- Single-stage Dockerfile (02-01): Development-first approach, multi-stage optimization deferred to Phase 13
- Extended Gunicorn timeout (02-01): 120s timeout for long-running AI/scraping operations (vs 30s default)
- Docker service names (02-01): Use 'db' and 'redis' hostnames in environment variables for Docker Compose networking
- Manual .env creation (02-03): User creates .env manually to ensure secure DB_PASSWORD knowledge
- Directory ownership in Dockerfile (02-03): Create data directories with proper ownership before USER switch to prevent permission errors
- Learning-first documentation (02-03): Apartment building analogy and beginner-friendly explanations for Docker concepts
- File-based Docker secrets (02-04): Secrets stored in /run/secrets/ files instead of environment variables to prevent docker inspect exposure
- Catalog-first intelligence (02.1-02): 50+ products = high confidence, <10 = questionnaire needed
- TF-IDF for keyword extraction (02.1-02): sklearn TfidfVectorizer with German stop words and special character support
- Pattern learning from SKUs (02.1-02): Pre-defined templates matched against existing SKUs with min_occurrences=5
- Niche detection via keyword scoring (02.1-02): Multiple signals (title/tags/types) more reliable than single field
- Local pattern matching first (02.1-03): Free and instant Stage 1 before web search or AI - pattern matching returns confidence 0.0-1.0
- Pydantic v2 for vendor config validation (02.1-01): Field validators for regex compilation and URL template checks
- _meta field alias (02.1-01): Pydantic v2 doesn't allow leading underscores, use meta with alias="_meta" for YAML compatibility
- Early regex validation (02.1-01): SKU patterns validated at schema level to catch configuration errors immediately
- URL placeholder validation (02.1-01): Product URL templates must contain {sku} placeholder to prevent misconfiguration
- Local-first AI (02.1-05): sentence-transformers for free local classification before paid API calls
- Multi-stage discovery (02.1-05): Pattern → Web → Local LLM → API LLM with early exit on high confidence
- Aggressive caching (02.1-05): LRU caches (1000 local, 500 API) prevent repeated queries
- Confidence thresholds (02.1-05): Pattern >=0.90, Search >=0.80, Local LLM >=0.85 for early exit
- Config auto-generation with confidence scoring (02.1-07): VendorConfigGenerator creates YAML from site recon, flags <0.80 for review
- Pydantic validation at init (02.1-07): Invalid regex and missing URL placeholders caught at schema level
- Optional LLM verification (02.1-07): ConfigVerifier works locally, OpenRouter API enables enhanced checks
- Strategy pattern for scraping (02.1-06): Playwright for JS sites, Requests for static HTML, pluggable architecture
- Tenacity for retry logic (02.1-06): Exponential backoff 2-30s, 3 attempts, rate limit detection
- Lazy Playwright import (02.1-06): Avoid requiring installation if unused, graceful degradation
- Fallback selectors (02.1-06): Robustness against page structure changes via primary + fallback CSS selectors
- Priority-based pattern matching (02.1-08): Check specific commands before generic SKU pattern to prevent "help" matching as SKU
- 3-tier chat classification (02.1-08): Pattern (80%, free) → Local LLM (15%, free) → API LLM (5%, paid)
- Structured responses without LLM (02.1-08): Handlers generate JSON-ready responses from data, no LLM overhead for formatting
- Backend-only chat infrastructure (02.1-08): Phase 5 exposes via REST API, Phase 10 builds ChatGPT-style UI
- Lazy playwright import (02.1-09): Avoid requiring installation if unused, graceful degradation
- Selector scoring algorithm (02.1-09): 0.0-2.0 range with content type validation for reliability
- Multi-sample validation (02.1-09): Test selectors on 3-5 products, require 80% success rate
- JavaScript detection via content size (02.1-09): >20% increase indicates JS requirement
- SKU pattern inference from samples (02.1-09): Extract and validate against 5 pre-defined patterns
- Session-based metrics (02.1-11): In-memory tracking for dynamic improvement, clears on restart
- Six categorized failure types (02.1-11): RATE_LIMIT, TIMEOUT, SELECTOR_FAILED, NETWORK_ERROR, VALIDATION_FAILED, UNKNOWN
- Pragmatic adaptive rules (02.1-11): Rate limits → +50% delay, Timeouts → +25% timeout, Selector failures → fallback selectors
- Rediscovery thresholds (02.1-11): >5 selector failures in 10 attempts OR <50% success rate triggers config refresh
- Exponential backoff with jitter (02.1-11): delay × (2^attempt) ± 20% jitter, max 30s for human-like behavior
- OpenRouter for AI descriptions (02.2-02): Gemini Flash 1.5 default, 75-95% cost savings vs direct APIs ($0.03/1K products)
- TTLCache for AI responses (02.2-02): 30-day TTL prevents duplicate API calls, saves costs on re-runs (95%+ cache hit rate)
- No embedding model in AIDescriptionGenerator (02.2-02): Receives pre-computed embeddings from EmbeddingGenerator (Plan 04), prevents duplicate 400MB model loading
- German stop word transliteration (02.2-02): Stop words use transliterated forms ("fuer" not "für") because removal happens after umlaut conversion
- Meta description padding before CTA (02.2-02): Ensures 120-char minimum before adding optional CTA, Google SEO compliance
- German-first color map (02.2-01): All colors normalized to German (Rot, Grün, etc.) for German market SEO
- Pattern priority ordering (02.2-01): Size patterns ordered specific → general to avoid partial matches (14x14cm before 20ml)
- Compound word materials (02.2-01): Partial word boundaries for German compound words like Epoxidharz
- Quality score formula (02.2-01): 40/30/20/10 weighting (description > structured data > categorization > tags)

### Roadmap Evolution

- Phase 1.1 inserted after Phase 1: Root Documentation Organization (URGENT) - Phase 1 archived scripts but left 20+ documentation/data files unorganized
- Phase 2.1 inserted after Phase 2: Universal Vendor Scraping Engine (URGENT) - Current image_scraper.py lacks strict SKU matching; /quickcleanup proved better patterns (SKU validation, Firecrawl discovery, batch processing, retry logic). Must become vendor-agnostic system before Phase 3 database schema design.
- Phase 14 added as final phase: Continuous Optimization & Learning - Self-improving system with ML-driven optimization, autonomous agents, and intelligent performance enhancement. Must be last to have full context of all previous phases.

### Pending Todos

None yet.

### Blockers/Concerns

**All gaps from VERIFICATION.md CLOSED:**
- Gap 1: SiteReconnaissance.discover() learns site structure (Plan 09, 11 min, 26 tests)
- Gap 2: FirecrawlClient + GSDPopulator auto-populate YAML mappings (Plan 10, 6 min, 16 tests)
- Gap 3: ScrapeMetrics + AdaptiveRetryEngine enable dynamic improvement (Plan 11, 9 min, 19 tests)

**Phase 2.1 COMPLETE (11/11 plans, verification PASSED).**
**Phase 2.2 IN PROGRESS (2/6 plans complete):** AI description and SEO generation complete with 27 passing tests. OpenRouter integration with Gemini Flash 1.5, German URL slug generation with umlaut transliteration.

## Session Continuity

Last session: 2026-02-08 16:52:53Z
Stopped at: Completed 02.2-02-PLAN.md (AI Description & SEO Generation)
Resume file: None

Config (if exists):
{
  "project_name": "Shopify Multi-Supplier Platform",
  "model_profile": "balanced",
  "commit_docs": true,
  "autonomous_cleanup_enabled": true
}
