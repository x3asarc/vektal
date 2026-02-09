# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-03)

**Core value:** Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, through an intelligent conversational AI interface.
**Current focus:** Phase 5 - Backend API Design

## Current Position

Phase: 5 of 15 (Backend API Design)
Plan: Ready to begin
Status: Phase 4 complete, UAT passed (10/10 tests)
Last activity: 2026-02-09 — Completed Phase 4 UAT verification and endpoint testing

Progress: [███████░░░] 90% (40/44 plans estimated)

## Recent Session Summary (2026-02-09)

**Phase 4 Complete - Authentication & User Management:**
- Plan 04-01 complete: Database Models Extension (auth fields, OAuthAttempt, enums)
- Plan 04-02 complete: Flask-Session Redis + Auth Decorators
- Plan 04-03 complete: Login/Logout + Email Verification Infrastructure
- Plan 04-04 complete: Stripe Checkout Session Creation
- Plan 04-05 complete: Stripe Webhooks + Subscription Management
- Plan 04-06 complete: Shopify OAuth Refactor + Blueprint Integration
- **UAT complete:** All 10 tests passed (0 issues)
- Backend container startup optimized: runtime dependency installation (flask-login, stripe, etc.)
- 22+ endpoints registered: 13 auth, 9 billing, 4 OAuth routes
- Three-tier pricing structure implemented ($29/$99/$299 per month)
- Session persistence via Redis with HttpOnly/SameSite cookies
- Flask-Login integration with user_loader and authentication redirects
- Endpoint verification: /auth/login, /billing/plans, /oauth/status all operational

**Phase 3 Complete - Database Migration (SQLite to PostgreSQL):**
- Plan 03-01 complete: Flask-SQLAlchemy + PostgreSQL Setup (5 minutes)
- Plan 03-02 complete: SQLAlchemy ORM Models (5 minutes)
- Plan 03-03 complete: Migrations, Backups & Encryption (7 minutes)
- Plan 03-04 complete: Pentart Import & Auto-Migrations (3 minutes)
- Plan 03-05 complete: app.py SQLAlchemy refactor & Job CRUD operations (auto-completed)
- **Verification complete:** All 16 verification tasks passed (0 critical issues)
- Flask-Migrate initialized with 11-table migration (users, stores, vendors, products, jobs)
- 39 indexes for performance (primary keys, foreign keys, unique constraints, composite indexes)
- Backup/restore scripts with pg_dump compression and 5-minute restore target
- Fernet encryption for OAuth token storage (ShopifyStore.access_token_encrypted)
- Pentart import script for initial vendor catalog data (barcode, SKU, weight only)
- Docker auto-migration on container startup (flask db upgrade)
- PostgreSQL ARRAY types for tags, colors, materials, embeddings
- Connection pooling: psycopg3 driver (4-5x more memory efficient)
- All data integrity constraints verified: FK cascades, NOT NULL, UNIQUE, enum types

**Phase 2.2 Execution Completed:**
- Wave 1 (4 plans in parallel): Attribute extraction, AI descriptions, product families, embeddings
- Wave 2 (1 plan): Pipeline orchestrator with Jinja2 templating
- Wave 3 (1 plan): Vendor YAML integration
- Total execution: 98 minutes for 6 plans
- Test coverage: 118 tests passing (34+27+21+15+12+9)
- All 10 success criteria verified

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
- Total plans completed: 40
- Average duration: 8 min
- Total execution time: 5.1 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-codebase-cleanup-analysis | 3 | 64 min | 21 min |
| 01.1-root-documentation-organization | 3 | 23 min | 8 min |
| 02-docker-infrastructure-foundation | 4 | 114 min | 29 min |
| 02.1-universal-vendor-scraping-engine | 11 | 93 min | 8 min |
| 02.2-product-enrichment-pipeline | 6 | 88 min | 15 min |
| 03-database-migration-sqlite-to-postgresql | 5 | 20 min | 4 min |
| 04-authentication-user-management | 6 | N/A | N/A |

**Recent Trend:**
- Last 6 plans: Phase 4 plans (04-01 through 04-06) completed from previous session
- Phase 4 complete: Authentication infrastructure with UAT verification (10/10 tests passed)
- Backend operational with 22+ registered endpoints across auth, billing, and OAuth

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
- Lazy component loading (02.2-05): AI generator and embedding generator loaded on first use, saves 2-3s startup for partial re-runs
- Checkpoint after each step (02.2-05): JSON checkpoints enable resumability after API timeouts or failures
- Step skip flags (02.2-05): Individual flags (skip_extraction, skip_ai, etc.) for fine-grained pipeline control
- StrictUndefined templates (02.2-05): Jinja2 fails on missing variables to catch vendor YAML config errors early
- Vendor auto-detection (02.2-06): Detect vendor from product['vendor'] field, normalize to slug for YAML lookup
- Conditional OR support (02.2-06): Support OR logic in tagging rules to reduce YAML duplication (vintage OR retro → style:vintage)
- Vendor rules after extraction (02.2-06): Apply vendor enrichment as Step 1.5 so rules can reference extracted attributes
- Dynamic color learning (02.2 enhancement): ColorLearner extracts colors from Shopify catalog during Phase 2.1 store analysis, merges with base COLOR_MAP for automatic recognition
- Store-specific color vocabulary (02.2 enhancement): AttributeExtractor accepts custom_color_map, EnrichmentPipeline auto-loads from data/store_profile.json (typical 38 base → 85-150 total colors)
- Color filtering heuristics (02.2 enhancement): Min 2 occurrences to filter typos, false positive removal (format, papier, vintage), 3-char minimum length
- Color auto-normalization (02.2 enhancement): mintgrün → Mint Grün, sky-blue → Sky Blue for consistent data quality
- psycopg3 over psycopg2 (03-01): 4-5x more memory efficient, async support, better connection handling for production scaling
- Development-friendly connection pool (03-01): pool_size=5, max_overflow=2 = 7 connections max per service (14 total with backend + celery_worker, well under PostgreSQL max_connections=100)
- PostgreSQL 16 (03-01): Latest stable version with performance improvements per RESEARCH.md recommendations
- Naming convention for Alembic (03-01): Explicit MetaData naming convention prevents "unnamed constraint" errors during schema changes
- Automatic psycopg3 URL conversion (03-01): Auto-convert postgresql:// to postgresql+psycopg:// to ensure psycopg3 driver usage
- Separate ProductEnrichment table (03-02): AI-generated SEO and attributes can be regenerated independently without affecting core product data
- Deferred imports for encryption (03-02): Import encryption functions inside methods to avoid circular dependency between models and core modules
- PostgreSQL ARRAY types (03-02): Native array support for tags, colors, materials, embeddings eliminates junction tables, simpler queries
- Composite index on VendorCatalogItem (03-02): Index on (vendor_id, sku, barcode) enables fast catalog lookups during product matching
- One-to-one User-ShopifyStore (03-02): unique=True on user_id enforces v1.0 requirement at database level, multi-store support deferred to v2.0
- Flask app factory for CLI (03-03): src/app_factory.py provides Flask app instance for flask db migrate/upgrade commands without running full application server
- Custom format pg_dump with compression level 6 (03-03): Custom format (-Fc) enables selective restore and better compression; level 6 balances speed vs size for frequent backups
- 5-backup retention by default (03-03): Keeps last 5 backups automatically to prevent disk space issues while maintaining reasonable history
- Confirmation prompt in restore script (03-03): Prevents accidental data loss by requiring explicit confirmation before destructive restore operation
- Fernet for OAuth token encryption (03-03): Industry-standard symmetric encryption with HMAC authentication; simpler than asymmetric encryption for database storage use case
- Return None on decryption failure (03-03): Graceful error handling allows application to detect and handle corrupted/expired tokens without crashing
- Import Pentart as initial vendor catalog data, NOT SQLite migration (03-04): Per CONTEXT.md, SQLite is temporary; production schema designed from requirements
- Import only 3 columns from Pentart CSV (03-04): Barcode, SKU, weight only - titles were Hungarian and other columns not applicable
- Auto-run migrations on container startup (03-04): flask db upgrade runs before server starts; ensures schema is always up-to-date, fails fast on errors

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
**Phase 2.2 COMPLETE (6/6 plans, verification PASSED):**
- Plans 01-04: Attribute extraction, AI/SEO generators, families/quality, embeddings (83 tests)
- Plan 05: EnrichmentPipeline orchestrator with 7-step workflow and checkpointing (10 integration tests)
- Plan 06: Vendor YAML integration with auto-detection and conditional tagging (12 integration tests)

**Phase 3 COMPLETE (5/5 plans, verification PASSED - 16/16 tasks):**
- Plans 01-05: PostgreSQL migration with SQLAlchemy, migrations, backup/restore, encryption (20 min total)
- 11 tables, 39 indexes, 3 enum types, 25+ foreign key constraints
- All data integrity verified: CASCADE deletes, NOT NULL, UNIQUE, auto-timestamps
- Verification: Database operations, indexes, FK constraints, enums, timestamps, constraints tested
- Production-ready with backup/restore, encryption, connection pooling, auto-migrations

**Phase 4 COMPLETE (6/6 plans, UAT PASSED - 10/10 tests):**
- Plans 01-06: Auth models, Flask-Session/Redis, login/email, Stripe checkout, webhooks, OAuth refactor
- 22+ endpoints registered: 13 auth routes, 9 billing routes, 4 OAuth routes
- Three-tier pricing: Starter ($29), Professional ($99), Enterprise ($299)
- Authentication infrastructure: Flask-Login, session persistence, auth decorators
- Stripe integration: Checkout sessions, webhook-driven user creation, subscription management
- OAuth flow: Refactored with retry logic, state validation, error handling
- Backend container optimized: Runtime dependency installation avoids full rebuild
- All endpoints verified operational: /auth/login, /billing/plans, /oauth/status

**Ready for Phase 5: Backend API Design**

## Session Continuity

Last session: 2026-02-09 16:30:00Z
Stopped at: Completed Phase 4 UAT verification (10/10 tests passed, 0 issues) + endpoint testing
Resume file: None

Config (if exists):
{
  "project_name": "Shopify Multi-Supplier Platform",
  "model_profile": "balanced",
  "commit_docs": true,
  "autonomous_cleanup_enabled": true
}
