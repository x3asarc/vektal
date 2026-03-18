# Roadmap: Shopify Multi-Supplier Platform v1.0

## Overview

This roadmap transforms an organically-grown monolithic Python application into a production-ready containerized SaaS platform. Starting with codebase cleanup to establish a maintainable foundation, we progress through Docker infrastructure setup, database migration to PostgreSQL, backend service containerization, modern Next.js frontend development, and the sophisticated conversational AI interface that serves as the platform's centerpiece. The journey concludes with tier system implementation, external API hardening, and production deployment readiness.

## Governance Baseline v1 (2026-02-12)

Canonical governance spec: `solutionsos/compound-engineering-os-policy.md`

1. Canonical lifecycle file: `.planning/ROADMAP.md` (this file).
2. Canonical execution state file: `.planning/STATE.md`.
3. Task closure requires exactly four reports in `reports/<phase>/<task>/`.
4. Required report fields cannot be empty; use explicit `N/A` when non-applicable.
5. Merge blocking: `Critical`, `High`, and `Medium` for `Security`/`Dependency`.
6. Reviewer uses two-pass protocol (`Blind Audit` then `Context Fit`) with timestamp evidence.
7. `MASTER_MAP.md` must be updated at daily batch and phase-close.
8. Protected paths (`.planning`, `.rules`, `AGENTS.md`) cannot be auto-moved.
9. Review timing is tracked as SLO, not a hard merge gate (`4h` initial, `2h` re-review; escalate at `24h`).
10. Pinning policy is canonical: Python exact pins in `requirements.txt`; Node changes require committed `package-lock.json`.
11. License policy blocks strong copyleft direct dependencies; transitive strong copyleft requires expiration-dated suppression plus replacement plan or blocks.
12. Dev auth bypass is local-pilot only and must be default OFF, dev-only, and explicitly visible when active.
13. Governance sequence is enforced: `07.1` validated before `07.2` execution.

### Phase 7 Governance Task Board

| Task | Purpose | Gate Status | Evidence |
|---|---|---|---|
| 07.1-governance-baseline-dry-run | Stand up governance artifacts and evidence flow | `GREEN` | `reports/07/07.1-governance-baseline-dry-run/` |
| 07.2-governance-operational-defaults | Lock v1.1 defaults (SLO, pinning, license scope, dev-bypass guard) | `GREEN` | `reports/07/07.2-governance-operational-defaults/` |

## Phases

**Phase Numbering:**
- Integer phases (1-15): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

**Audience Tags:**
- `[developer-facing]` - Benefits developers/maintainers/AI assistants (not visible to end users)
- `[user-facing]` - Delivers features/value directly to Shopify store owners (end users)

---

### Completed Phases

- [x] **Phase 1: Codebase Cleanup & Analysis** `[developer-facing]` - Foundation cleanup before building
- [x] **Phase 1.1: Root Documentation Organization (INSERTED)** `[developer-facing]` - Complete root directory cleanup
- [x] **Phase 2: Docker Infrastructure Foundation** `[developer-facing]` - Container orchestration and service architecture
- [x] **Phase 2.1: Universal Vendor Scraping Engine (INSERTED)** `[user-facing]` - Vendor-agnostic scraping with intelligent strategy selection
- [x] **Phase 2.2: Product Enrichment Pipeline (INSERTED)** `[user-facing]` - AI-powered enrichment (without vectorization)
- [x] **Phase 3: Database Migration (SQLite to PostgreSQL)** `[developer-facing]` - Production-grade data layer
- [x] **Phase 4: Authentication & User Management** `[user-facing]` - User system in containerized environment
- [x] **Phase 5: Backend API Design** `[developer-facing]` - RESTful API structure and contracts
- [x] **Phase 6: Job Processing Infrastructure (Celery)** `[developer-facing]` - Async task processing foundation
- [x] **Phase 7: Frontend Framework Setup (Next.js)** `[user-facing]` - Modern React-based UI foundation
- [x] **Phase 8: Product Resolution Engine** `[user-facing]` - Intelligent product lookup and enrichment
- [x] **Phase 9: Real-Time Progress Tracking** `[user-facing]` - Live job monitoring with WebSocket/SSE
- [x] **Phase 10: Conversational AI Interface** `[user-facing]` - ChatGPT-style intelligent interface
- [x] **Phase 11: Product Search & Discovery** `[user-facing]` - Advanced search and version tracking
- [x] **Phase 12: Tier System Architecture** `[developer-facing]` - Multi-tier capability routing (LLM to Full Agents)
- [x] **Phase 13: Integration Hardening & Deployment** `[developer-facing]` - Production readiness and external API robustness
- [x] **Phase 13.1: Product Data Enrichment Protocol v2 Integration (INSERTED)** `[user-facing]` - Canonical enrichment v2 as integrated platform feature
- [x] **Phase 13.2: Oracle Framework Reuse (INSERTED)** `[developer-facing]` - Shared verifier/oracle adapters for cross-phase use
- [x] **Phase 14: Codebase Knowledge Graph & Continual Learning** `[developer-facing]` - Knowledge graph of code structure for AI-assisted development
- [x] **Phase 14.1: Neo4j-Vector-Hybrid-RAG Enhancement (INSERTED)** `[developer-facing]` - Upgrade graph from passive store to MCP-accessible hybrid RAG engine
- [x] **Phase 14.2: Tool Calling 2.0 Integration (INSERTED)** `[developer-facing]` - Optimize MCP/tool call semantics (batching, deferred loading, schema examples)
- [x] **Phase 14.3: Graph Availability + Sync Reliability (INSERTED)** `[developer-facing]` - Guarantee Aura-first graph availability with local Neo4j and snapshot fallback
- [x] **Phase 15: Self-Healing & Runtime Optimization** `[developer-facing]` - Autonomous refactoring, performance optimization, cost reduction
- [x] **Phase 16: Agent Context OS (INSERTED)** `[developer-facing]` - Always-fresh onboarding context, graph-first broker, and live memory governance

### Future Phases

- [ ] **Future Phase: Production Refinement & Integration Cleanup** `[user-facing]` - Make existing features production-ready (frontend integration fixes, edge cases, polish)
- [ ] **Future Phase: User Data Knowledge Graph & Semantic Search** `[user-facing]` - Knowledge graph of user's products/vendors with vector search, duplicate detection, smart recommendations

## Phase Details

### Phase 1: Codebase Cleanup & Analysis
**Goal**: Organize and document the codebase to establish a maintainable foundation before containerization
**Depends on**: Nothing (first phase)
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03, CLEAN-04, CLEAN-05, CLEAN-06, CLEAN-07
**Success Criteria** (what must be TRUE):
  1. Developer can locate production code vs experimental scripts by directory structure
  2. All tests run with single pytest command from tests/ directory
  3. New developer can understand system architecture by reading ARCHITECTURE.md
  4. CLI operations use unified interface instead of 5+ separate scripts
  5. Scraper strategy (Python vs JavaScript boundaries) documented and clear
**Plans**: 3 plans in 2 waves

Plans:
- [x] 01-01-PLAN.md - Archive 50+ scripts to archive/2026-scripts/ with categorization (Wave 1)
- [x] 01-02-PLAN.md - Typer CLI consolidation and pytest test migration (Wave 1)
- [x] 01-03-PLAN.md - ARCHITECTURE.md and scraper strategy documentation (Wave 2)

### Phase 1.1: Root Documentation Organization (INSERTED)
**Goal**: Complete root directory cleanup by organizing ALL 70 items (42 files + 28 directories) in root
**Depends on**: Phase 1
**Requirements**: CLEAN-01 (complete), CLEAN-04 (complete)
**Success Criteria** (what must be TRUE):
  1. Root directory contains only essential project files (README.md, ARCHITECTURE.md, requirements.txt, pyproject.toml, .env files, .gitignore, demo_framework.py)
  2. All 11 CSV files organized in data/csv/ or results/csv/
  3. All 6 JSON result files organized in results/scraping/ or data/test/
  4. All 12 loose markdown docs organized in docs/ subdirectories (guides/, reference/, legacy/)
  5. All questionable directories investigated and either kept, moved, archived, or deleted
  6. Documentation index created (docs/INDEX.md) for easy navigation
  7. Developer can understand root structure at a glance
**Plans**: 3 plans in 3 waves

Plans:
- [x] 01.1-01-PLAN.md - Organize 42 loose files (CSV, JSON, docs, scripts) (Wave 1)
- [x] 01.1-02-PLAN.md - Investigate and organize 13 questionable directories (Wave 2)
- [x] 01.1-03-PLAN.md - Create documentation index and verify complete cleanup (Wave 3)

### Phase 2: Docker Infrastructure Foundation
**Goal**: Establish containerized service architecture with development workflow and production-ready configuration
**Depends on**: Phase 1.1
**Requirements**: DOCKER-01, DOCKER-02, DOCKER-08, DOCKER-09, DOCKER-12, DOCKER-14
**Success Criteria** (what must be TRUE):
  1. Developer can start entire stack with single docker compose up command
  2. All services respond to health check endpoints within 30 seconds of startup
  3. Secrets never appear in docker inspect output or container logs
  4. Hot reload works for backend code changes without container rebuild
  5. Nginx correctly routes requests to appropriate backend services
**Plans**: 4 plans in 2 waves

Plans:
- [x] 02-01-PLAN.md - Foundation files: .gitattributes, Dockerfile.backend, gunicorn config, .env.example (Wave 1)
- [x] 02-02-PLAN.md - Docker Compose with 6 services and Nginx reverse proxy (Wave 1)
- [x] 02-03-PLAN.md - Documentation, frontend placeholder, and stack verification (Wave 2)
- [x] 02-04-PLAN.md - Docker secrets implementation (gap closure for DOCKER-08) (Wave 1)

### Phase 2.1: Universal Vendor Scraping Engine (INSERTED)
**Goal**: Self-learning AI-powered vendor discovery with zero-configuration setup and niche-aware safety
**Depends on**: Phase 2
**Requirements**: TBD (will be defined during discussion phase)
**Success Criteria** (what must be TRUE):
  1. User provides ONLY SKU/barcode - System auto-discovers vendor (confidence >70%)
  2. System learns vendor site structure and auto-generates YAML config
  3. Onboarding questionnaire builds store profile (niche, keywords, vendor scope)
  4. Niche mismatch detection prevents wrong vendors (car parts in arts store)
  5. Context-aware search uses store keywords + SKU (not SKU alone)
  6. User confirmation required when confidence <70% or niche mismatch
  7. Firecrawl discovery extracts direct product URLs from collection pages
  8. GSD optimization (pre-mapped URLs) makes scraping 10x faster
  9. Batch processing achieves >80% success rate with retry logic
  10. Future customers with ANY vendor work seamlessly
**Plans**: 11 plans in 5 waves

Plans:
- [x] 02.1-01-PLAN.md - Core Pydantic schemas and YAML loader (Wave 1)
- [x] 02.1-02-PLAN.md - Store profile analyzer with TF-IDF extraction (Wave 1)
- [x] 02.1-03-PLAN.md - Local pattern matching and SKU validation (Wave 1)
- [x] 02.1-04-PLAN.md - Web search and niche validation (Wave 2)
- [x] 02.1-05-PLAN.md - AI inference and vendor discovery pipeline (Wave 2)
- [x] 02.1-06-PLAN.md - Multi-strategy scraping engine (Wave 3)
- [x] 02.1-07-PLAN.md - YAML auto-generation and verification (Wave 3)
- [x] 02.1-08-PLAN.md - Chat interface routing (Wave 4)
- [x] 02.1-09-PLAN.md - Site reconnaissance and selector discovery (Wave 5, Gap Closure)
- [x] 02.1-10-PLAN.md - Firecrawl integration and GSD auto-population (Wave 5, Gap Closure)
- [x] 02.1-11-PLAN.md - Metrics tracking and adaptive learning (Wave 5, Gap Closure)

### Phase 2.2: Product Enrichment Pipeline (INSERTED)
**Goal**: AI-powered product enrichment with description generation, attribute extraction, quality scoring, and embedding generation
**Depends on**: Phase 2.1
**Requirements**: TBD (will be defined during discussion phase)
**Success Criteria** (what must be TRUE):
  1. Scraped products are enriched using vendor YAML config (keywords, tags, content templates)
  2. AI generates German-language descriptions following store's content framework
  3. Attributes extracted automatically (colors, materials, techniques) from title/description
  4. Quality score (0-100) assigned to each product based on completeness
  5. Vector embeddings generated for semantic search (sentence-transformers)
  6. Content templates ensure brand consistency across all products
  7. SEO optimization applied (meta titles, descriptions, URL handles)
  8. Image alt text generated following vendor patterns
  9. Products grouped into families (variants linked to base product)
  10. Enrichment achieves >85% quality score on average
**Plans**: 6 plans in 2 waves

Plans:
- [x] 02.2-01-PLAN.md - Attribute extraction and quality scoring foundation (Wave 1)
- [x] 02.2-02-PLAN.md - AI description generation and SEO content (Wave 1)
- [x] 02.2-03-PLAN.md - Product family grouping and quality gate (Wave 1)
- [x] 02.2-04-PLAN.md - Vector embedding generation (Wave 1)
- [x] 02.2-05-PLAN.md - EnrichmentPipeline orchestrator and Jinja2 templating (Wave 2)
- [x] 02.2-06-PLAN.md - Vendor YAML enrichment integration (Wave 2)

### Phase 3: Database Migration (SQLite to PostgreSQL)
**Goal**: Set up production PostgreSQL database with fresh schema designed from v1.0 requirements, Flask-SQLAlchemy ORM, and disaster recovery capability
**Depends on**: Phase 2.2
**Requirements**: DOCKER-05, DOCKER-07
**Success Criteria** (what must be TRUE):
  1. All Shopify OAuth tokens and API keys remain decryptable after migration
  2. Multiple backend services can query database concurrently without connection errors
  3. Developer can restore database from backup within 5 minutes
  4. All production data migrated with zero data loss verified by row counts
  5. Connection pool limits prevent PostgreSQL max_connections exhaustion
**Plans**: 5 plans in 1 wave

Plans:
- [x] 03-01-PLAN.md - Flask-SQLAlchemy + psycopg3 foundation (Wave 1)
- [x] 03-02-PLAN.md - SQLAlchemy models: User, ShopifyStore, Vendor, Product, Job (Wave 1)
- [x] 03-03-PLAN.md - Flask-Migrate, migrations, backup/restore, encryption (Wave 1)
- [x] 03-04-PLAN.md - Pentart import script & auto-migrations (Wave 1)
- [x] 03-05-PLAN.md - app.py SQLAlchemy refactor & Job CRUD operations (Wave 1)

### Phase 4: Authentication & User Management
**Goal**: Implement complete user authentication system for standalone SaaS with Stripe billing, Redis sessions, and Shopify OAuth integration
**Depends on**: Phase 3
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. User can register account and log in with credentials persisted in PostgreSQL
  2. Shopify OAuth flow works from containerized Flask backend
  3. User sessions persist across backend container restarts
  4. API endpoints reject requests without valid authentication tokens
  5. User tier assignment determines which features are accessible
**Plans**: 6 plans in 4 waves

Plans:
- [x] 04-01-PLAN.md - Database models: User auth fields, OAuthAttempt, dependencies (Wave 1)
- [x] 04-02-PLAN.md - Flask-Session Redis config, decorators (@requires_tier, @email_verified_required) (Wave 1)
- [x] 04-03-PLAN.md - Login/logout, email verification endpoints (Wave 2)
- [x] 04-04-PLAN.md - Stripe checkout session creation (Wave 2)
- [x] 04-05-PLAN.md - Stripe webhooks, subscription management (Wave 3)
- [x] 04-06-PLAN.md - Shopify OAuth refactor with retry logic and blueprint integration (Wave 4)

### Phase 5: Backend API Design
**Goal**: Define RESTful API structure with validation, documentation, and real-time capabilities
**Depends on**: Phase 4
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08
**Success Criteria** (what must be TRUE):
  1. Developer can explore all API endpoints via interactive OpenAPI documentation
  2. Invalid request payloads return structured error responses with field-level details
  3. API enforces tier-based rate limiting (different limits per user tier)
  4. Frontend can consume SSE stream for real-time updates (with polling fallback)
  5. CORS configuration allows frontend development server to call backend APIs
**Plans**: 6 plans in 4 waves

Plans:
- [x] 05-01-PLAN.md - API core infrastructure (RFC 7807 errors, pagination, rate limits)
- [x] 05-02-PLAN.md - OpenAPI app factory and versioned route registration
- [x] 05-03-PLAN.md - SSE infrastructure and polling fallback
- [x] 05-04-PLAN.md - Domain blueprints (products, jobs, vendors)
- [x] 05-04-01-PLAN.md - Per-user API versioning and migration lifecycle
- [x] 05-05-PLAN.md - End-to-end verification and API test completion

### Phase 6: Job Processing Infrastructure (Celery)
**Goal**: Implement async job processing with monitoring and parallel execution capabilities
**Depends on**: Phase 3
**Requirements**: DOCKER-03, DOCKER-04, DOCKER-06, DOCKER-10, DOCKER-11, JOBS-01, JOBS-02, JOBS-03, JOBS-04, JOBS-05, JOBS-06, JOBS-07, JOBS-08
**Success Criteria** (what must be TRUE):
  1. Developer can monitor running jobs in real-time via Flower dashboard
  2. Long-running scraping tasks execute in background without blocking API responses
  3. Tier 3 user jobs process before Tier 1 user jobs when queue is busy
  4. User can cancel in-progress job and see status change immediately
  5. Job results persist in database and remain accessible after worker restart
**Plans**: 6 plans in 5 waves

Plans:
- [x] 06-01: Schema and model invariants foundation (Wave 1)
- [x] 06-02: Queue/container/logging/Flower infrastructure closure (Wave 1)
- [x] 06-03: Ingest orchestration and chunk execution integration (Wave 2)
- [x] 06-04: Checkpoint outbox dispatcher + finalizer convergence (Wave 3)
- [x] 06-05: Cancellation, prioritization under load, retention cleanup (Wave 4)
- [x] 06-06: Verification, requirement traceability, and UAT closure (Wave 5)

### Phase 7: Frontend Framework Setup (Next.js)
**Goal**: Build modern React-based UI foundation with routing and progressive onboarding
**Depends on**: Phase 5
**Requirements**: FRONTEND-01, FRONTEND-02, FRONTEND-03, FRONTEND-04, FRONTEND-05, FRONTEND-06, FRONTEND-07, FRONTEND-08
**Success Criteria** (what must be TRUE):
  1. New user completes 3-step onboarding wizard (Connect Shopify, Upload CSV, Preview)
  2. Frontend makes API calls with optimistic updates and loading states
  3. UI responds to mobile and tablet screen sizes without horizontal scrolling
  4. Navigation between routes (chat, dashboard, search, settings) works instantly
  5. Application state persists when user refreshes browser
**Plans**: 4 plans in 3 waves

Plans:
- [x] 07-01: Next.js setup with routing and API client
- [x] 07.1: Governance baseline dry-run and gate scaffolding
- [x] 07-02: Progressive onboarding and responsive layout
- [x] 07-03: State management and Module Federation preparation

### Phase 8: Product Resolution Engine
**Goal**: Implement intelligent product lookup across Shopify, database, and web with AI enrichment
**Depends on**: Phase 6
**Requirements**: RESOLVE-01, RESOLVE-02, RESOLVE-03, RESOLVE-04, RESOLVE-05, RESOLVE-06, RESOLVE-07, RESOLVE-08
**Success Criteria** (what must be TRUE):
  1. User provides SKU and system finds product in Shopify catalog within 2 seconds
  2. System searches supplier CSV database when Shopify search returns no results
  3. Web search ranks results by relevance based on existing product catalog patterns
  4. System automatically detects vendor and selects correct scraping strategy
  5. User previews all changes (prices, descriptions, images) before applying to Shopify
**Plans**: 4 plans in 3 waves

Plans:
- [x] 08-01: Resolution persistence, policy engine, and checkout locking foundation (Wave 1)
- [x] 08-02: Multi-source resolver, scoring, structural conflicts, and dry-run compiler APIs (Wave 2)
- [x] 08-03: Collaborative dry-run review UX, strategy quiz, and rule suggestion inbox (Wave 3)
- [x] 08-04: Guarded apply engine, pre-flight + Recovery Logs, and image sovereignty pipeline (Wave 3)

### Phase 9: Real-Time Progress Tracking
**Goal**: Provide live job progress updates with visual feedback and error handling
**Depends on**: Phase 6, Phase 7
**Requirements**: PROGRESS-01, PROGRESS-02, PROGRESS-03, PROGRESS-04, PROGRESS-05, PROGRESS-06, PROGRESS-07
**Success Criteria** (what must be TRUE):
  1. User sees progress bar update in real-time as job processes each product
  2. UI displays current step (searching Shopify, scraping web, analyzing images)
  3. User sees estimated time remaining that updates based on actual progress
  4. Failed jobs show error details with retry button
  5. Success notification shows count of products updated with link to results
**Plans**: 2 plans in 2 waves

Plans:
- [x] 09-01: WebSocket/SSE connection and progress components
- [x] 09-02: Step transitions, time estimates, and error states

### Phase 10: Conversational AI Interface
**Goal**: Build ChatGPT-style interface for natural language product management
**Depends on**: Phase 8, Phase 9
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08
**Success Criteria** (what must be TRUE):
  1. User types "update SKU 12345" and chat responds with product found in Shopify
  2. Chat streams responses in real-time like ChatGPT (not all-at-once)
  3. User provides up to 1000 SKUs and chat processes them via auto-chunked parallel orchestration
  4. Chat maintains context within conversation (remembers previous queries)
  5. Complex data (product tables, price comparisons) displays in structured format
**Plans**: 4 plans in 4 waves

Plans:
- [x] 10-01: Chat backend contracts, session state, and streaming foundation (Wave 1)
- [x] 10-02: Single-SKU conversational orchestration with dry-run + approvals (Wave 2)
- [x] 10-03: Bulk orchestration (up to 1000 SKUs) with adaptive chunk concurrency (Wave 3)
- [x] 10-04: Chat workspace UX, structured rendering, and approval controls (Wave 4)

### Phase 11: Product Search & Discovery
**Goal**: Enable advanced product search with version history and bulk operations
**Depends on**: Phase 8, Phase 10
**Requirements**: SEARCH-01, SEARCH-02, SEARCH-03, SEARCH-04, SEARCH-05, SEARCH-06, SEARCH-07, SNAP-01, SNAP-02, SNAP-03, SNAP-04
**Success Criteria** (what must be TRUE):
  1. User searches by HS code and finds all products in that tariff category
  2. Filter by vendor, price range, and stock level returns accurate results
  3. Product cards display image, name, SKU, price, and stock at a glance
  4. User views product detail and sees complete change history (what changed when)
  5. User selects 50 products with checkboxes and initiates bulk update operation
  6. Snapshot storage is efficient: periodic full-store baseline + per-batch manifest + touched-product pre-change snapshots with hash dedupe.
**Plans**: 3 plans in 3 waves

Plans:
- [x] 11-01: Multi-field search and advanced filtering
- [x] 11-02: Version history, diff visualization, and bulk selection
- [x] 11-03: Snapshot lifecycle optimization (baseline + delta + dedupe + retention/recovery index)

### Phase 12: Tier System Architecture
**Goal**: Implement routing-first multi-tier capability control so each user request is handled by the correct runtime path
**Depends on**: Phase 10
**Requirements**: TIER-01, TIER-02, TIER-03, TIER-04, TIER-05, TIER-06, TIER-07, TIER-08
**Success Criteria** (what must be TRUE):
  1. Every user request resolves to an explainable route decision for Tier 1, Tier 2, or Tier 3.
  2. Tier 1 handles low-risk LLM interactions without privileged execution paths.
  3. Tier 2 executes governed skill/workflow actions with approval-aware behavior.
  4. Tier 3 can orchestrate advanced agents and safely delegate to lower-tier capabilities.
  5. Product UI/API enforce tier-based feature visibility and action boundaries consistently.
**Plans**: 3 plans in 3 waves

Plans:
- [x] 12-01: Tier detection and routing logic
- [x] 12-02: Tier 1 (LLM) and Tier 2 (Agentic) implementation
- [x] 12-03: Tier 3 (Full Agents) and cross-tier interaction

### Phase 13: Integration Hardening & Deployment
**Goal**: Harden production agent execution and external integrations, then prepare deployment infrastructure
**Depends on**: Phase 11, Phase 12
**Requirements**: INTEGRATE-01, INTEGRATE-02, INTEGRATE-03, INTEGRATE-04, INTEGRATE-05, INTEGRATE-06, INTEGRATE-07, INTEGRATE-08, DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06, DEPLOY-07, DEPLOY-08
**Success Criteria** (what must be TRUE):
  1. Agent/tool boundaries, auth, and policy enforcement are production-hardened with auditability.
  2. Provider reliability is resilient (fallback, retries, and optional provider routing such as Replicate behind abstraction).
  3. End-to-end observability and evaluation gates catch regressions and unsafe behavior before broad rollout.
  4. Production deployment includes automated backups and operational alerting.
  5. Health monitoring and failure isolation prevent cascading outages across core services.
**Plans**: 4 plans in 4 waves

Plans:
- [x] 13-01: API rate limiting and circuit breakers
- [x] 13-02: Governance and recovery controls (verification oracle, kill-switch, field policy)
- [x] 13-03: Production deployment and monitoring infrastructure
- [x] 13-04: Preference and verification instrumentation foundation

### Phase 13.1: Product Data Enrichment Protocol v2 Integration (INSERTED)
**Goal:** Integrate a comprehensive enrichment protocol v2 as a first-class platform capability
**Plans:** 4 plans in 4 waves

Plans:
- [x] 13.1-01-PLAN.md - Capability audit, policy contracts, and governed write-plan foundation
- [x] 13.1-02-PLAN.md - Enrichment core profiles, eligibility matrix, Oracle arbitration
- [x] 13.1-03-PLAN.md - API/job lifecycle integration and dedicated enrichment workspace UX
- [x] 13.1-04-PLAN.md - Benchmark gates, audit export/retention, and cutover verification closure

### Phase 13.2: Oracle Framework Reuse (INSERTED)
**Goal:** Establish one reusable Oracle framework for content, visual, execution, and policy verification
**Plans:** 7 plans in 5 waves

Plans:
- [x] 13.2-01-PLAN.md - Infrastructure + Client + Entity Types
- [x] 13.2-02-PLAN.md - Episode Ingestion Pipeline
- [x] 13.2-03-PLAN.md - Graph Oracle Adapter + Memory Retrieval Upgrade
- [x] 13.2-04-PLAN.md - CI Governance Gate + Contract Tests
- [x] 13.2-05-PLAN.md - Phase Closure + Forward Integration Spec
- [x] 13.2-06-PLAN.md - Unify Oracle Contract (Gap Closure)
- [x] 13.2-07-PLAN.md - Create Governance Reports (Gap Closure)

### Phase 14: Codebase Knowledge Graph & Continual Learning
**Goal**: Build self-learning codebase knowledge graph for AI-assisted development
**Plans**: 8 plans in 4 waves

Plans:
- [x] 14-01: Extend Neo4j schema for codebase entities
- [x] 14-02: Vector embedding pipeline (hierarchical summaries)
- [x] 14-03: Full codebase scanner + manual sync command
- [x] 14-04: Planning docs as central nodes
- [x] 14-05: Git pre-commit hook integration
- [x] 14-06: Periodic consistency daemon
- [x] 14-07: LLM instruction framework
- [x] 14-08: Query interface for LLMs

### Phase 14.1: Neo4j-Vector-Hybrid-RAG Enhancement (INSERTED)
**Goal**: Upgrade to an active dual-layer reasoning engine with MCP tool access
**Plans**: 6 plans in 3 waves

Plans:
- [x] 14.1-01-PLAN.md - Memory entity types and relationships
- [x] 14.1-02-PLAN.md - Reasoning provenance and discrepancy tracking
- [x] 14.1-03-PLAN.md - Search-then-Expand bridge
- [x] 14.1-04-PLAN.md - Semantic cache layer
- [x] 14.1-05-PLAN.md - MCP tool server
- [x] 14.1-06-PLAN.md - Session lifecycle hooks and convention guardrails

### Phase 14.2: Tool Calling 2.0 Integration (INSERTED)
**Goal**: Optimize MCP tool invocation (batching, deferred loading, compact output)
**Plans**: 7 plans in 4 waves

Plans:
- [x] 14.2-01-PLAN.md - Input examples on tool schemas
- [x] 14.2-02-PLAN.md - Tool nodes + search_tools in Neo4j
- [x] 14.2-03-PLAN.md - Deferred loading + schema persistence
- [x] 14.2-04-PLAN.md - batch_query + batch_dependencies tools
- [x] 14.2-05-PLAN.md - Compact output optimization path
- [x] 14.2-06-PLAN.md - Batch episode emission in sync pipeline
- [x] 14.2-07-PLAN.md - External Research Tools Integration (Firecrawl + Perplexity)

### Phase 14.3: Graph Availability + Sync Reliability (INSERTED)
**Goal**: Guarantee graph context availability with multi-tier fallback
**Plans**: 7 plans in 4 waves

Plans:
- [x] 14.3-01-PLAN.md - Backend resolver contract + runtime manifest
- [x] 14.3-02-PLAN.md - Shared bootstrap command + local Neo4j auto-start
- [x] 14.3-03-PLAN.md - Sync status contract + metadata updates
- [x] 14.3-04-PLAN.md - PreTool/session integration
- [x] 14.3-05-PLAN.md - MCP response metadata + degraded-mode guardrails
- [x] 14.3-06-PLAN.md - Governance availability gate + integration tests
- [x] 14.3-07-PLAN.md - Sentry issue ingestion + triage normalization

### Phase 15: Self-Healing & Runtime Optimization
**Goal**: Autonomous refactoring and performance optimization using Knowledge Graph
**Plans**: 12 plans in 6 waves

Plans:
- [x] 15-01-PLAN.md - Universal Sandbox with 6-gate verification
- [x] 15-02-PLAN.md - Session Context & Memory Architecture
- [x] 15-03-PLAN.md - Root-Cause Classifier (LLM + Graph)
- [x] 15-04-PLAN.md - Autonomous Fix Generation (Templates + LLM)
- [x] 15-05-PLAN.md - Learnings Loop (Template extraction)
- [x] 15-06-PLAN.md - Sentry Integration Verification
- [x] 15-07-PLAN.md - Infrastructure Bash Agent
- [x] 15-08-PLAN.md - Performance Profiling & Bottleneck Detection
- [x] 15-09-PLAN.md - Runtime Optimization Engine
- [x] 15-10-PLAN.md - Sentry Feedback Closure
- [x] 15-11a-PLAN.md - Approval Queue Backend (Model + API)
- [x] 15-11b-PLAN.md - Approval Queue Frontend (CLI + Web UI)

### Phase 16: Agent Context OS (INSERTED)
**Goal**: Establish a lightweight, always-live agent context operating system with graph-first retrieval and auditable memory governance
**Depends on**: Phase 15
**Plans**: 7 plans in 4 waves

Plans:
- [x] 16-01-PLAN.md - Canonical event schema + append-only event writer
- [x] 16-02-PLAN.md - Deterministic materializers for working/short/long memory views
- [x] 16-03-PLAN.md - Single onboarding entrypoint + folder summaries + link map generation
- [x] 16-04-PLAN.md - Graph-first context broker with reason-coded fallback telemetry
- [x] 16-05-PLAN.md - Lifecycle hook integration across session/task/phase events
- [x] 16-06-PLAN.md - Context OS binary gate + operator report + runbook
- [x] 16-07-PLAN.md - Verification harness, E2E validation, and phase closure artifacts

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Codebase Cleanup & Analysis | 3/3 | Complete | 2026-02-03 |
| 1.1. Root Documentation Organization | 3/3 | Complete | 2026-02-04 |
| 2. Docker Infrastructure Foundation | 4/4 | Complete | 2026-02-05 |
| 2.1. Universal Vendor Scraping Engine | 11/11 | Complete | 2026-02-08 |
| 2.2. Product Enrichment Pipeline | 6/6 | Complete | 2026-02-08 |
| 3. Database Migration (SQLite to PostgreSQL) | 5/5 | Complete | 2026-02-08 |
| 4. Authentication & User Management | 6/6 | Complete | 2026-02-09 |
| 5. Backend API Design | 6/6 | Complete | 2026-02-09 |
| 6. Job Processing Infrastructure (Celery) | 6/6 | Complete | 2026-02-10 |
| 7. Frontend Framework Setup (Next.js) | 3/3 | Complete | 2026-02-12 |
| 8. Product Resolution Engine | 4/4 | Complete | 2026-02-13 |
| 9. Real-Time Progress Tracking | 2/2 | Complete | 2026-02-15 |
| 10. Conversational AI Interface | 4/4 | Complete | 2026-02-15 |
| 11. Product Search & Discovery | 3/3 | Complete | 2026-02-15 |
| 12. Tier System Architecture | 3/3 | Complete | 2026-02-15 |
| 13. Integration Hardening & Deployment | 4/4 | Complete | 2026-02-16 |
| 13.1. Product Data Enrichment Protocol v2 | 4/4 | Complete | 2026-02-16 |
| 13.2. Oracle Framework Reuse | 7/7 | Complete | 2026-02-19 |
| 14. Codebase Knowledge Graph | 8/8 | Complete | 2026-02-20 |
| 14.1. Hybrid-RAG Enhancement | 6/6 | Complete | 2026-02-23 |
| 14.2. Tool Calling 2.0 | 7/7 | Complete | 2026-02-26 |
| 14.3. Graph Availability + Sync | 7/7 | Complete | 2026-03-01 |
| 15. Self-Healing & Optimization | 12/12 | Complete | 2026-03-02 |
| 15.1. Sentry Autonomous Intake + Verified Auto-Resolution | 4/4 | Complete | 2026-03-04 |
| 16. Agent Context OS | 7/7 | Complete | 2026-03-03 |

### Phase 15.1: Sentry Autonomous Intake and Verified Auto-Resolution (INSERTED)

**Goal:** Close the Sentry loop by pulling unresolved production issues, routing them through the existing health/remediation stack, and only marking them resolved once the Sentry API reports no new activity.
**Depends on:** Phase 15 (self-healing + health monitor), Phase 14.3 Sentry ingestion artifacts, and Phase 16 Context OS telemetry/memory contracts
**Plans:** 4 plans in 2 waves

Plans:
- [x] 15.1-01-PLAN.md - Sentry intake normalization and canonical issue-pulled events (Wave 1)
- [x] 15.1-02-PLAN.md - Health monitor deduped routing and issue-level telemetry (Wave 1)
- [x] 15.1-03-PLAN.md - Verified Sentry closure gate in client and feedback loop (Wave 2)
- [x] 15.1-04-PLAN.md - Focused verification suite and binary closure evidence (Wave 2)

### Phase 17: Product Data Command Center + Chat-First Product Ops
**Goal**: Transform the platform into a "System of Record" alongside Shopify with real-time sync, catalog health scoring, and forensic rollback.
**Depends on**: Phase 16, Phase 10
**Plans**: 6 plans in 6 waves

Plans:
- [x] 17.1-PLAN.md - Data Contract (Completeness scoring & Model extensions) (Wave 1)
- [x] 17.2-PLAN.md - Ingest Hardening (Automated metrics & Watermarking) (Wave 2)
- [x] 17.3-PLAN.md - Shopify Listener (Webhook receiver & Reconciliation poller) (Wave 3)
- [x] 17.4-PLAN.md - Dashboard Metrics API (Summary & Search filters) (Wave 4)
- [x] 17.5-PLAN.md - Dashboard UI (Command Center & Chat Dock) (Wave 5)
- [x] 17.6-PLAN.md - Rollback UX (Pre-flight audit & Execution) (Wave 6)

### Phase 18: Evolutionary Schema Engine (Nanoclaw) (INSERTED)
**Goal**: Implement "Self-Writing DNA" where the system autonomously detects new data shapes in incoming webhooks and evolves its own database schema to accommodate them.
**Depends on**: Phase 17 (Webhook infrastructure), Phase 15 (Sandbox & Governance)
**Audience**: `[developer-facing]` - Automates schema maintenance.
**Plans**: TBD

Plans:
- [ ] 18.1-PLAN.md - Picoclaw Observer (Data shape detection & anomaly tagging)
- [ ] 18.2-PLAN.md - Nanoclaw Architect (Type inference & Model rewriting)
- [ ] 18.3-PLAN.md - The Foundry (Automated migration generation & Sandboxed application)
- [ ] 18.4-PLAN.md - Governance GUI (Human approval queue for schema expansion)

## Phase -1: Recovery and Audit Catalog (COMPLETED)
**Goal**: Make existing Phase 20 audit artifacts navigable as single source of truth for Agent SDK
**Depends on**: Phase 20
**Status**: COMPLETE (2026-03-18)

Artifacts:
- `audit/INDEX.md` - Master index of 48 folders with coverage (6% of 813 goal)
- `audit/README.md` - Architecture doc explaining 8 surfaces
- `audit/SURFACE_REGISTRY.json` - Machine-readable registry
- [ ] 18.4-PLAN.md - Governance GUI (Human approval queue for schema expansion)
