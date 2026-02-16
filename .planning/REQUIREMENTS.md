# Requirements: Shopify Multi-Supplier Platform v1.0

**Defined:** 2026-02-03
**Core Value:** Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, through an intelligent conversational AI interface.

## v1.0 Requirements

### Codebase Cleanup (CLEAN)

- [x] **CLEAN-01**: Archive 30+ one-off scripts to `archive/2026-scripts/` (apply_*, scrape_*, fix_*, dry_run_*)
- [x] **CLEAN-02**: Consolidate 5 duplicate CLI update scripts into unified interface
- [x] **CLEAN-03**: Move all test files to `tests/` directory with pytest structure
- [x] **CLEAN-04**: Create comprehensive ARCHITECTURE.md from codebase analysis
- [x] **CLEAN-05**: Run Vulture + deadcode autonomous dead code detection
- [x] **CLEAN-06**: Agent-driven cleanup with specialist subagents (Archiver, Consolidator, Test Migrator)
- [x] **CLEAN-07**: Document scraper strategy (Python vs JavaScript boundaries and integration)

### Docker Architecture (DOCKER)

- [x] **DOCKER-01**: Create Docker Compose configuration (dev + production profiles)
- [x] **DOCKER-02**: Containerize Flask API backend (Gunicorn WSGI server, not dev server)
- [ ] **DOCKER-03**: Containerize Celery worker service (async job processing)
- [ ] **DOCKER-04**: Containerize scraper service (unified Python + JavaScript)
- [x] **DOCKER-05**: Set up PostgreSQL 16 container (replace SQLite)
- [x] **DOCKER-06**: Set up Redis 7.4 container (Celery broker + caching)
- [x] **DOCKER-07**: Migrate data from SQLite to PostgreSQL (preserve encryption keys)
- [x] **DOCKER-08**: Implement secrets management (Docker secrets, not plain env vars)
- [x] **DOCKER-09**: Add health checks for all services
- [ ] **DOCKER-10**: Configure centralized logging (Docker log drivers)
- [ ] **DOCKER-11**: Set up Flower monitoring for Celery workers
- [x] **DOCKER-12**: Configure Nginx reverse proxy for service routing
- [ ] **DOCKER-13**: Multi-stage Dockerfile builds (60% size reduction)
- [x] **DOCKER-14**: Hot reload setup for development workflow

### Conversational AI Interface (CHAT)

- [x] **CHAT-01**: Build chat UI component (fullscreen, ChatGPT-style interface)
- [x] **CHAT-02**: Implement streaming responses with real-time updates
- [x] **CHAT-03**: Context management ("at the door" vs "in the house" context states)
- [x] **CHAT-04**: Single SKU intelligent workflow (Shopify â†’ DB â†’ web search â†’ scrape)
- [x] **CHAT-05**: Bulk SKU processing (up to 1000 SKUs with auto-chunked workflow)
- [x] **CHAT-06**: Parallel agent spawning for bulk operations (speed optimization)
- [x] **CHAT-07**: Natural language query parsing (extract SKUs, intents, parameters)
- [x] **CHAT-08**: Response formatting (structured data presentation in conversational format)

### Real-Time Progress Tracking (PROGRESS)

- [x] **PROGRESS-01**: WebSocket or SSE connection for live updates
- [x] **PROGRESS-02**: Progress bar component with percentage tracking
- [x] **PROGRESS-03**: Step-by-step status display (searching Shopify, searching DB, scraping web...)
- [x] **PROGRESS-04**: Visual state transitions with icons/colors
- [x] **PROGRESS-05**: Estimated time remaining calculation
- [x] **PROGRESS-06**: Error state handling with retry options
- [x] **PROGRESS-07**: Success/failure notifications with details

### Intelligent Product Resolution (RESOLVE)

- [x] **RESOLVE-01**: Shopify catalog search by SKU/EAN/barcode/title
- [x] **RESOLVE-02**: Supplier CSV database search (uploaded vendor catalogs)
- [x] **RESOLVE-03**: Web search with relevance scoring (find closest match based on existing products)
- [x] **RESOLVE-04**: Automatic vendor detection and scraping strategy selection
- [x] **RESOLVE-05**: Field extraction (SKU, barcode, EAN, name, description, meta, tags, collection, HS code, country, prices, variants, metafields)
- [x] **RESOLVE-06**: Vision AI image analysis integration (existing system, verify compatibility)
- [x] **RESOLVE-07**: SEO generation (meta title, description, German content)
- [x] **RESOLVE-08**: Dry-run preview before applying changes

### Product Search & Discovery (SEARCH)

- [x] **SEARCH-01**: Multi-field search (HS code, SKU, EAN, name, country, stock, price)
- [x] **SEARCH-02**: Advanced filtering (by vendor, collection, tags, price range, stock level)
- [x] **SEARCH-03**: Search results with product cards (image, name, SKU, price, stock)
- [x] **SEARCH-04**: Product detail view with all fields
- [x] **SEARCH-05**: Version history ("what used to exist" vs "what now exists")
- [x] **SEARCH-06**: Diff visualization for product changes
- [x] **SEARCH-07**: Bulk selection for batch operations (checkboxes)

### Snapshot Lifecycle & Recovery Efficiency (SNAP)

- [x] **SNAP-01**: Periodic full-store baseline snapshots (not per apply)
- [x] **SNAP-02**: Mandatory per-batch manifest + touched-product pre-change snapshots
- [x] **SNAP-03**: Hash-based snapshot dedupe with pointer reuse (no duplicate blobs)
- [x] **SNAP-04**: Re-baseline triggers + retention policy + Recovery Log restore chain (`batch -> pre-image -> baseline`)

### Tier System Architecture (TIER)

- [x] **TIER-01**: Define tier capability matrix and routing contract (Tier 1/2/3 boundaries)
- [x] **TIER-02**: Implement explainable tier detection and request routing logic
- [x] **TIER-03**: Tier 1 runtime: low-risk LLM interaction path without privileged execution
- [x] **TIER-04**: Tier 2 runtime: governed skills/workflows with approval-aware execution
- [x] **TIER-05**: Tier 3 runtime: advanced agent orchestration with safe delegation
- [x] **TIER-06**: Tier-based feature gating and capability disclosure in UI/API
- [x] **TIER-07**: User/team agent profiles with managed enabled-skill sets
- [x] **TIER-08**: Tier transition UX (upgrade prompts, fallback behavior, and continuity)

### External API Integration Hardening (INTEGRATE)

- [x] **INTEGRATE-01**: Agent boundary + threat model for tools, data paths, and permissions
- [x] **INTEGRATE-02**: Strict tool contracts (typed schemas, server-side validation, idempotency)
- [x] **INTEGRATE-03**: Secure execution model (RBAC, sandboxing, and approval checkpoints)
- [x] **INTEGRATE-04**: Reliability controls (retry/backoff, circuit breakers, graceful degradation)
- [x] **INTEGRATE-05**: Provider abstraction + fallback strategy (including optional Replicate path)
- [x] **INTEGRATE-06**: End-to-end observability (traces, metrics, logs, cost telemetry)
- [x] **INTEGRATE-07**: Evaluation gates (regression, drift, safety checks) for production rollout
- [x] **INTEGRATE-08**: Audit/compliance retention and export controls for agent actions

### Product Enrichment Protocol v2 Integration (ENRICHV2)

- [ ] **ENRICHV2-01**: Canonical enrichment v2 path replaces duplicate 2.2 + side-project execution paths
- [ ] **ENRICHV2-02**: Mandatory Shopify capability/schema/scope audit before enrichment write planning
- [ ] **ENRICHV2-03**: Merchant-first conflict arbitration with deterministic Oracle decision contract
- [ ] **ENRICHV2-04**: Profile gears (`Quick`, `Standard`, `Deep`) with tier-aware execution controls
- [ ] **ENRICHV2-05**: Broad retrieval-ready payload with product-class eligibility matrix
- [ ] **ENRICHV2-06**: Reusable Oracle adapters for content/visual/policy arbitration (with Phase 13 execution oracle continuity)
- [ ] **ENRICHV2-07**: Hash/idempotent rerun behavior and bounded transient retry controls
- [ ] **ENRICHV2-08**: User-selectable multilingual output and field-level provenance/confidence lineage
- [ ] **ENRICHV2-09**: Dry-run-first lifecycle with TTL/revalidation and governed approval semantics
- [ ] **ENRICHV2-10**: Governance overlays for vendor field mapping, protected columns, alt-text preservation, and audit export/retention

### User Management & Authentication (AUTH)

- [x] **AUTH-01**: User registration and login
- [x] **AUTH-02**: Shopify OAuth integration (existing, needs containerization compatibility)
- [x] **AUTH-03**: Tier assignment and tracking
- [x] **AUTH-04**: Session management across services
- [x] **AUTH-05**: Permission system (tier-based access control)
- [ ] **AUTH-06**: API key management for user-specific integrations

### Frontend Framework & Infrastructure (FRONTEND)

- [x] **FRONTEND-01**: Next.js 16 + TypeScript setup
- [x] **FRONTEND-02**: API client with React Query (optimistic updates)
- [x] **FRONTEND-03**: Routing structure (onboarding, chat, dashboard, search, settings)
- [x] **FRONTEND-04**: Progressive onboarding wizard (simplified 3-step)
- [x] **FRONTEND-05**: Layout components (header, sidebar, chat panel)
- [x] **FRONTEND-06**: Responsive design (desktop-first, mobile-compatible)
- [x] **FRONTEND-07**: State management (React Context or Zustand)
- [x] **FRONTEND-08**: Module Federation preparation (future modular apps)

### Backend API Design (API)

- [x] **API-01**: RESTful API structure with /api prefix
- [x] **API-02**: OpenAPI specification documentation
- [x] **API-03**: Authentication middleware (JWT or session-based)
- [x] **API-04**: Rate limiting per user/tier
- [x] **API-05**: Request validation with Pydantic
- [x] **API-06**: Error response standardization
- [x] **API-07**: CORS configuration for frontend
- [x] **API-08**: WebSocket/SSE endpoints for real-time updates

### Job Processing & Orchestration (JOBS)

- [ ] **JOBS-01**: Celery task definitions for all workflows
- [ ] **JOBS-02**: Job status tracking (queued, processing, completed, failed)
- [ ] **JOBS-03**: Job prioritization (Tier 3 > Tier 2 > Tier 1)
- [ ] **JOBS-04**: Parallel task execution for bulk operations
- [ ] **JOBS-05**: Job cancellation and retry mechanisms
- [ ] **JOBS-06**: Result persistence (PostgreSQL job results table)
- [ ] **JOBS-07**: Job history and auditing
- [ ] **JOBS-08**: Cleanup of old jobs (retention policy)

### Deployment & DevOps (DEPLOY)

- [x] **DEPLOY-01**: Production Docker Compose configuration
- [x] **DEPLOY-02**: Environment variable management (dev, staging, production)
- [x] **DEPLOY-03**: Database backup and restore scripts
- [x] **DEPLOY-04**: CI/CD pipeline setup (GitHub Actions or similar)
- [x] **DEPLOY-05**: Health monitoring and alerting
- [x] **DEPLOY-06**: Log aggregation and analysis
- [x] **DEPLOY-07**: Performance monitoring (APM)
- [x] **DEPLOY-08**: Security hardening (non-root containers, secrets scanning)

## v2 Requirements

### Advanced Analytics

- **ANALYTICS-01**: Scraping success rate dashboard
- **ANALYTICS-02**: Cost tracking (AI API spend per user/tier)
- **ANALYTICS-03**: Product coverage metrics (vendors, categories)
- **ANALYTICS-04**: Performance analytics (scraping speed, job throughput)

### Image Management App

- **IMAGE-01**: Image gallery view for all products
- **IMAGE-02**: Bulk image replacement workflows
- **IMAGE-03**: Vision AI batch analysis
- **IMAGE-04**: Image editing tools (crop, resize, filters)

### Multi-Tenant Architecture

- **TENANT-01**: Separate database per tenant (schema-based isolation)
- **TENANT-02**: Tenant-aware routing and data access
- **TENANT-03**: Cross-tenant administration dashboard
- **TENANT-04**: Billing and subscription management

### Mobile Application

- **MOBILE-01**: React Native app for iOS/Android
- **MOBILE-02**: Push notifications for job completion
- **MOBILE-03**: Mobile-optimized chat interface

## Out of Scope

| Feature | Reason |
|---------|--------|
| Blockchain integration | Not relevant to e-commerce catalog management |
| Social media posting | Out of core value proposition (catalog management, not marketing) |
| Inventory forecasting | Complex ML requirement, defer to v3+ after product-market fit |
| Multiple Shopify stores per user | Single store sufficient for v1.0, multi-store in v2 with tenant architecture |
| White-label branding | Not needed until agency/reseller partnerships |
| GraphQL API | REST sufficient for v1.0, GraphQL adds complexity without clear benefit yet |
| Kubernetes | Docker Compose sufficient for initial scale (<100 concurrent users), K8s when needed |
| IP rotation for scraping | Manual politeness delays sufficient initially, add if bans occur |
| Custom AI model training | Use existing OpenAI/Gemini APIs, custom models v3+ |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLEAN-01 | Phase 1 | Complete |
| CLEAN-02 | Phase 1 | Complete |
| CLEAN-03 | Phase 1 | Complete |
| CLEAN-04 | Phase 1 | Complete |
| CLEAN-05 | Phase 1 | Complete |
| CLEAN-06 | Phase 1 | Complete |
| CLEAN-07 | Phase 1 | Complete |
| DOCKER-01 | Phase 2 | Complete |
| DOCKER-02 | Phase 2 | Complete |
| DOCKER-08 | Phase 2 | Complete |
| DOCKER-09 | Phase 2 | Complete |
| DOCKER-12 | Phase 2 | Complete |
| DOCKER-13 | Phase 2 | Pending |
| DOCKER-14 | Phase 2 | Complete |
| DOCKER-05 | Phase 3 | Complete |
| DOCKER-07 | Phase 3 | Complete |
| AUTH-01 | Phase 4 | Complete |
| AUTH-02 | Phase 4 | Complete |
| AUTH-03 | Phase 4 | Complete |
| AUTH-04 | Phase 4 | Complete |
| AUTH-05 | Phase 4 | Complete |
| AUTH-06 | Phase 4 | Pending |
| API-01 | Phase 5 | Complete |
| API-02 | Phase 5 | Complete |
| API-03 | Phase 5 | Complete |
| API-04 | Phase 5 | Complete |
| API-05 | Phase 5 | Complete |
| API-06 | Phase 5 | Complete |
| API-07 | Phase 5 | Complete |
| API-08 | Phase 5 | Complete |
| DOCKER-03 | Phase 6 | Pending |
| DOCKER-04 | Phase 6 | Pending |
| DOCKER-06 | Phase 6 | Complete |
| DOCKER-10 | Phase 6 | Pending |
| DOCKER-11 | Phase 6 | Pending |
| JOBS-01 | Phase 6 | Pending |
| JOBS-02 | Phase 6 | Pending |
| JOBS-03 | Phase 6 | Pending |
| JOBS-04 | Phase 6 | Pending |
| JOBS-05 | Phase 6 | Pending |
| JOBS-06 | Phase 6 | Pending |
| JOBS-07 | Phase 6 | Pending |
| JOBS-08 | Phase 6 | Pending |
| FRONTEND-01 | Phase 7 | Complete |
| FRONTEND-02 | Phase 7 | Complete |
| FRONTEND-03 | Phase 7 | Complete |
| FRONTEND-04 | Phase 7 | Complete |
| FRONTEND-05 | Phase 7 | Complete |
| FRONTEND-06 | Phase 7 | Complete |
| FRONTEND-07 | Phase 7 | Complete |
| FRONTEND-08 | Phase 7 | Complete |
| RESOLVE-01 | Phase 8 | Complete |
| RESOLVE-02 | Phase 8 | Complete |
| RESOLVE-03 | Phase 8 | Complete |
| RESOLVE-04 | Phase 8 | Complete |
| RESOLVE-05 | Phase 8 | Complete |
| RESOLVE-06 | Phase 8 | Complete |
| RESOLVE-07 | Phase 8 | Complete |
| RESOLVE-08 | Phase 8 | Complete |
| PROGRESS-01 | Phase 9 | Complete |
| PROGRESS-02 | Phase 9 | Complete |
| PROGRESS-03 | Phase 9 | Complete |
| PROGRESS-04 | Phase 9 | Complete |
| PROGRESS-05 | Phase 9 | Complete |
| PROGRESS-06 | Phase 9 | Complete |
| PROGRESS-07 | Phase 9 | Complete |
| CHAT-01 | Phase 10 | Complete |
| CHAT-02 | Phase 10 | Complete |
| CHAT-03 | Phase 10 | Complete |
| CHAT-04 | Phase 10 | Complete |
| CHAT-05 | Phase 10 | Complete |
| CHAT-06 | Phase 10 | Complete |
| CHAT-07 | Phase 10 | Complete |
| CHAT-08 | Phase 10 | Complete |
| SEARCH-01 | Phase 11 | Complete |
| SEARCH-02 | Phase 11 | Complete |
| SEARCH-03 | Phase 11 | Complete |
| SEARCH-04 | Phase 11 | Complete |
| SEARCH-05 | Phase 11 | Complete |
| SEARCH-06 | Phase 11 | Complete |
| SEARCH-07 | Phase 11 | Complete |
| SNAP-01 | Phase 11 | Complete |
| SNAP-02 | Phase 11 | Complete |
| SNAP-03 | Phase 11 | Complete |
| SNAP-04 | Phase 11 | Complete |
| TIER-01 | Phase 12 | Complete |
| TIER-02 | Phase 12 | Complete |
| TIER-03 | Phase 12 | Complete |
| TIER-04 | Phase 12 | Complete |
| TIER-05 | Phase 12 | Complete |
| TIER-06 | Phase 12 | Complete |
| TIER-07 | Phase 12 | Complete |
| TIER-08 | Phase 12 | Complete |
| INTEGRATE-01 | Phase 13 | Complete |
| INTEGRATE-02 | Phase 13 | Complete |
| INTEGRATE-03 | Phase 13 | Complete |
| INTEGRATE-04 | Phase 13 | Complete |
| INTEGRATE-05 | Phase 13 | Complete |
| INTEGRATE-06 | Phase 13 | Complete |
| INTEGRATE-07 | Phase 13 | Complete |
| INTEGRATE-08 | Phase 13 | Complete |
| DEPLOY-01 | Phase 13 | Complete |
| DEPLOY-02 | Phase 13 | Complete |
| DEPLOY-03 | Phase 13 | Complete |
| DEPLOY-04 | Phase 13 | Complete |
| DEPLOY-05 | Phase 13 | Complete |
| DEPLOY-06 | Phase 13 | Complete |
| DEPLOY-07 | Phase 13 | Complete |
| DEPLOY-08 | Phase 13 | Complete |
| ENRICHV2-01 | Phase 13.1 | Planned |
| ENRICHV2-02 | Phase 13.1 | Planned |
| ENRICHV2-03 | Phase 13.1 | Planned |
| ENRICHV2-04 | Phase 13.1 | Planned |
| ENRICHV2-05 | Phase 13.1 | Planned |
| ENRICHV2-06 | Phase 13.1 | Planned |
| ENRICHV2-07 | Phase 13.1 | Planned |
| ENRICHV2-08 | Phase 13.1 | Planned |
| ENRICHV2-09 | Phase 13.1 | Planned |
| ENRICHV2-10 | Phase 13.1 | Planned |

**Coverage:**
- v1.0 requirements: 96 total
- Mapped to phases: 96 (100% coverage)
- Unmapped: 0

## Recent Verification Updates (2026-02-16)

- Phase 7 verified complete: `FRONTEND-01` through `FRONTEND-08` closed and validated in UAT.
- Phase 8 verified complete: `RESOLVE-01` through `RESOLVE-08` closed and validated in UAT + verification artifacts.
- Phase 9 verified complete: `PROGRESS-01` through `PROGRESS-07` closed with backend/frontend targeted verification and typecheck evidence.
- Phase 11 verified complete: `SEARCH-01` through `SEARCH-07` and `SNAP-01` through `SNAP-04` closed with backend/frontend contract and typecheck evidence.
- Phase 12 verified complete: `TIER-01` through `TIER-08` closed with backend/frontend contract suites and queue/QoS delegation checks.
- Phase 13 verified complete: `13-01` through `13-04` closed `GREEN`, phase-level verification closed, and `INTEGRATE-*` + `DEPLOY-*` requirements marked complete with canonical evidence in `.planning/phases/13-integration-hardening-deployment/13-VERIFICATION.md`.
- Canonical evidence:
  - `.planning/phases/07-frontend-framework-setup/07-UAT.md`
  - `.planning/phases/08-product-resolution-engine/08-UAT.md`
  - `.planning/phases/08-product-resolution-engine/08-VERIFICATION.md`
  - `.planning/phases/09-real-time-progress-tracking/09-VERIFICATION.md`
  - `.planning/phases/11-product-search-discovery/11-01-SUMMARY.md`
  - `.planning/phases/11-product-search-discovery/11-02-SUMMARY.md`
  - `.planning/phases/11-product-search-discovery/11-03-SUMMARY.md`
  - `.planning/phases/11-product-search-discovery/11-VERIFICATION.md`
  - `.planning/phases/12-tier-system-architecture/12-01-SUMMARY.md`
  - `.planning/phases/12-tier-system-architecture/12-02-SUMMARY.md`
  - `.planning/phases/12-tier-system-architecture/12-03-SUMMARY.md`
  - `.planning/phases/12-tier-system-architecture/12-VERIFICATION.md`

---
*Requirements defined: 2026-02-03 after comprehensive questioning and research*
*Last updated: 2026-02-16 after Phase 13 verify-work closure*


