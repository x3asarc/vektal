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

- [ ] **SEARCH-01**: Multi-field search (HS code, SKU, EAN, name, country, stock, price)
- [ ] **SEARCH-02**: Advanced filtering (by vendor, collection, tags, price range, stock level)
- [ ] **SEARCH-03**: Search results with product cards (image, name, SKU, price, stock)
- [ ] **SEARCH-04**: Product detail view with all fields
- [ ] **SEARCH-05**: Version history ("what used to exist" vs "what now exists")
- [ ] **SEARCH-06**: Diff visualization for product changes
- [ ] **SEARCH-07**: Bulk selection for batch operations (checkboxes)

### Snapshot Lifecycle & Recovery Efficiency (SNAP)

- [ ] **SNAP-01**: Periodic full-store baseline snapshots (not per apply)
- [ ] **SNAP-02**: Mandatory per-batch manifest + touched-product pre-change snapshots
- [ ] **SNAP-03**: Hash-based snapshot dedupe with pointer reuse (no duplicate blobs)
- [ ] **SNAP-04**: Re-baseline triggers + retention policy + Recovery Log restore chain (`batch -> pre-image -> baseline`)

### Tier System Architecture (TIER)

- [ ] **TIER-01**: Define tier capabilities (Tier 1: LLM orchestrator, Tier 2: Agentic workflows, Tier 3: Full Claude Code agents)
- [ ] **TIER-02**: Implement tier detection and routing logic
- [ ] **TIER-03**: Tier 1: OpenRouter LLM integration (API calls only)
- [ ] **TIER-04**: Tier 2: Agentic workflow spawning (background task execution)
- [ ] **TIER-05**: Tier 3: Full Claude Code agent execution with GSD skills
- [ ] **TIER-06**: Tier-based feature gating (UI shows/hides based on user tier)
- [ ] **TIER-07**: Cross-tier interaction (Tier 3 agents can call Tier 2 workflows)
- [ ] **TIER-08**: Tier upgrade prompts (show value of higher tiers contextually)

### External API Integration Hardening (INTEGRATE)

- [ ] **INTEGRATE-01**: Shopify API rate limiting (leaky bucket algorithm, respect headers)
- [ ] **INTEGRATE-02**: OpenAI/Gemini cost monitoring and budget enforcement
- [ ] **INTEGRATE-03**: Circuit breakers for external services (Shopify, AI APIs, vendor sites)
- [ ] **INTEGRATE-04**: Retry logic with exponential backoff
- [ ] **INTEGRATE-05**: Vision AI response caching verification (already built, needs audit)
- [ ] **INTEGRATE-06**: Vendor scraping politeness delays (robots.txt respect)
- [ ] **INTEGRATE-07**: Error logging and alerting for API failures
- [ ] **INTEGRATE-08**: Fallback strategies when services unavailable

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

- [ ] **DEPLOY-01**: Production Docker Compose configuration
- [ ] **DEPLOY-02**: Environment variable management (dev, staging, production)
- [ ] **DEPLOY-03**: Database backup and restore scripts
- [ ] **DEPLOY-04**: CI/CD pipeline setup (GitHub Actions or similar)
- [ ] **DEPLOY-05**: Health monitoring and alerting
- [ ] **DEPLOY-06**: Log aggregation and analysis
- [ ] **DEPLOY-07**: Performance monitoring (APM)
- [ ] **DEPLOY-08**: Security hardening (non-root containers, secrets scanning)

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
| SEARCH-01 | Phase 11 | Pending |
| SEARCH-02 | Phase 11 | Pending |
| SEARCH-03 | Phase 11 | Pending |
| SEARCH-04 | Phase 11 | Pending |
| SEARCH-05 | Phase 11 | Pending |
| SEARCH-06 | Phase 11 | Pending |
| SEARCH-07 | Phase 11 | Pending |
| SNAP-01 | Phase 11 | Pending |
| SNAP-02 | Phase 11 | Pending |
| SNAP-03 | Phase 11 | Pending |
| SNAP-04 | Phase 11 | Pending |
| TIER-01 | Phase 12 | Pending |
| TIER-02 | Phase 12 | Pending |
| TIER-03 | Phase 12 | Pending |
| TIER-04 | Phase 12 | Pending |
| TIER-05 | Phase 12 | Pending |
| TIER-06 | Phase 12 | Pending |
| TIER-07 | Phase 12 | Pending |
| TIER-08 | Phase 12 | Pending |
| INTEGRATE-01 | Phase 13 | Pending |
| INTEGRATE-02 | Phase 13 | Pending |
| INTEGRATE-03 | Phase 13 | Pending |
| INTEGRATE-04 | Phase 13 | Pending |
| INTEGRATE-05 | Phase 13 | Pending |
| INTEGRATE-06 | Phase 13 | Pending |
| INTEGRATE-07 | Phase 13 | Pending |
| INTEGRATE-08 | Phase 13 | Pending |
| DEPLOY-01 | Phase 13 | Pending |
| DEPLOY-02 | Phase 13 | Pending |
| DEPLOY-03 | Phase 13 | Pending |
| DEPLOY-04 | Phase 13 | Pending |
| DEPLOY-05 | Phase 13 | Pending |
| DEPLOY-06 | Phase 13 | Pending |
| DEPLOY-07 | Phase 13 | Pending |
| DEPLOY-08 | Phase 13 | Pending |

**Coverage:**
- v1.0 requirements: 86 total
- Mapped to phases: 86 (100% coverage)
- Unmapped: 0

## Recent Verification Updates (2026-02-15)

- Phase 7 verified complete: `FRONTEND-01` through `FRONTEND-08` closed and validated in UAT.
- Phase 8 verified complete: `RESOLVE-01` through `RESOLVE-08` closed and validated in UAT + verification artifacts.
- Phase 9 verified complete: `PROGRESS-01` through `PROGRESS-07` closed with backend/frontend targeted verification and typecheck evidence.
- Canonical evidence:
  - `.planning/phases/07-frontend-framework-setup/07-UAT.md`
  - `.planning/phases/08-product-resolution-engine/08-UAT.md`
  - `.planning/phases/08-product-resolution-engine/08-VERIFICATION.md`
  - `.planning/phases/09-real-time-progress-tracking/09-VERIFICATION.md`

---
*Requirements defined: 2026-02-03 after comprehensive questioning and research*
*Last updated: 2026-02-15 after Phase 10 closure + Phase 11 snapshot lifecycle insertion*


