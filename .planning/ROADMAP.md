# Roadmap: Shopify Multi-Supplier Platform v1.0

## Overview

This roadmap transforms an organically-grown monolithic Python application into a production-ready containerized SaaS platform. Starting with codebase cleanup to establish a maintainable foundation, we progress through Docker infrastructure setup, database migration to PostgreSQL, backend service containerization, modern Next.js frontend development, and the sophisticated conversational AI interface that serves as the platform's centerpiece. The journey concludes with tier system implementation, external API hardening, and production deployment readiness.

## Phases

**Phase Numbering:**
- Integer phases (1-13): Planned milestone work
- Decimal phases (e.g., 2.1): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Codebase Cleanup & Analysis** - Foundation cleanup before building
- [ ] **Phase 2: Docker Infrastructure Foundation** - Container orchestration and service architecture
- [ ] **Phase 3: Database Migration (SQLite to PostgreSQL)** - Production-grade data layer
- [ ] **Phase 4: Authentication & User Management** - User system in containerized environment
- [ ] **Phase 5: Backend API Design** - RESTful API structure and contracts
- [ ] **Phase 6: Job Processing Infrastructure (Celery)** - Async task processing foundation
- [ ] **Phase 7: Frontend Framework Setup (Next.js)** - Modern React-based UI foundation
- [ ] **Phase 8: Product Resolution Engine** - Intelligent product lookup and enrichment
- [ ] **Phase 9: Real-Time Progress Tracking** - Live job monitoring with WebSocket/SSE
- [ ] **Phase 10: Conversational AI Interface** - ChatGPT-style intelligent interface
- [ ] **Phase 11: Product Search & Discovery** - Advanced search and version tracking
- [ ] **Phase 12: Tier System Architecture** - Multi-tier capability routing (LLM to Full Agents)
- [ ] **Phase 13: Integration Hardening & Deployment** - Production readiness and external API robustness

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
**Plans**: TBD

Plans:
- [ ] 01-01: Agent-driven script classification and archival
- [ ] 01-02: CLI consolidation and test migration
- [ ] 01-03: Architecture documentation and scraper strategy

### Phase 2: Docker Infrastructure Foundation
**Goal**: Establish containerized service architecture with proper boundaries and production server configuration
**Depends on**: Phase 1
**Requirements**: DOCKER-01, DOCKER-02, DOCKER-08, DOCKER-09, DOCKER-12, DOCKER-13, DOCKER-14
**Success Criteria** (what must be TRUE):
  1. Developer can start entire stack with single docker compose up command
  2. All services respond to health check endpoints within 30 seconds of startup
  3. Secrets never appear in docker inspect output or container logs
  4. Hot reload works for backend code changes without container rebuild
  5. Nginx correctly routes requests to appropriate backend services
**Plans**: TBD

Plans:
- [ ] 02-01: Docker Compose multi-service setup with health checks
- [ ] 02-02: Secrets management and production WSGI configuration
- [ ] 02-03: Nginx reverse proxy and development workflow

### Phase 3: Database Migration (SQLite to PostgreSQL)
**Goal**: Replace SQLite with PostgreSQL while preserving encrypted credentials and establishing connection pooling
**Depends on**: Phase 2
**Requirements**: DOCKER-05, DOCKER-07
**Success Criteria** (what must be TRUE):
  1. All Shopify OAuth tokens and API keys remain decryptable after migration
  2. Multiple backend services can query database concurrently without connection errors
  3. Developer can restore database from backup within 5 minutes
  4. All production data migrated with zero data loss verified by row counts
  5. Connection pool limits prevent PostgreSQL max_connections exhaustion
**Plans**: TBD

Plans:
- [ ] 03-01: PostgreSQL container setup with migration scripts
- [ ] 03-02: Encryption key preservation and connection pool tuning

### Phase 4: Authentication & User Management
**Goal**: Implement user authentication system compatible with containerized architecture
**Depends on**: Phase 3
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06
**Success Criteria** (what must be TRUE):
  1. User can register account and log in with credentials persisted in PostgreSQL
  2. Shopify OAuth flow works from containerized Flask backend
  3. User sessions persist across backend container restarts
  4. API endpoints reject requests without valid authentication tokens
  5. User tier assignment determines which features are accessible
**Plans**: TBD

Plans:
- [ ] 04-01: User registration and session management
- [ ] 04-02: Shopify OAuth containerization and tier assignment

### Phase 5: Backend API Design
**Goal**: Define RESTful API structure with validation, documentation, and real-time capabilities
**Depends on**: Phase 4
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08
**Success Criteria** (what must be TRUE):
  1. Developer can explore all API endpoints via interactive OpenAPI documentation
  2. Invalid request payloads return structured error responses with field-level details
  3. API enforces tier-based rate limiting (different limits per user tier)
  4. Frontend can establish WebSocket connection for real-time updates
  5. CORS configuration allows frontend development server to call backend APIs
**Plans**: TBD

Plans:
- [ ] 05-01: API structure, validation, and documentation
- [ ] 05-02: Rate limiting and WebSocket endpoints

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
**Plans**: TBD

Plans:
- [ ] 06-01: Celery worker and Redis broker setup
- [ ] 06-02: Job tracking, prioritization, and Flower monitoring

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
**Plans**: TBD

Plans:
- [ ] 07-01: Next.js setup with routing and API client
- [ ] 07-02: Progressive onboarding and responsive layout
- [ ] 07-03: State management and Module Federation preparation

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
**Plans**: TBD

Plans:
- [ ] 08-01: Multi-source product search implementation
- [ ] 08-02: Vendor detection, field extraction, and dry-run preview

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
**Plans**: TBD

Plans:
- [ ] 09-01: WebSocket/SSE connection and progress components
- [ ] 09-02: Step transitions, time estimates, and error states

### Phase 10: Conversational AI Interface
**Goal**: Build ChatGPT-style interface for natural language product management
**Depends on**: Phase 8, Phase 9
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08
**Success Criteria** (what must be TRUE):
  1. User types "update SKU 12345" and chat responds with product found in Shopify
  2. Chat streams responses in real-time like ChatGPT (not all-at-once)
  3. User provides 10 SKUs in one message and chat processes all in parallel
  4. Chat maintains context within conversation (remembers previous queries)
  5. Complex data (product tables, price comparisons) displays in structured format
**Plans**: TBD

Plans:
- [ ] 10-01: Chat UI and streaming response infrastructure
- [ ] 10-02: Natural language parsing and single SKU workflow
- [ ] 10-03: Bulk processing with parallel agent spawning

### Phase 11: Product Search & Discovery
**Goal**: Enable advanced product search with version history and bulk operations
**Depends on**: Phase 8
**Requirements**: SEARCH-01, SEARCH-02, SEARCH-03, SEARCH-04, SEARCH-05, SEARCH-06, SEARCH-07
**Success Criteria** (what must be TRUE):
  1. User searches by HS code and finds all products in that tariff category
  2. Filter by vendor, price range, and stock level returns accurate results
  3. Product cards display image, name, SKU, price, and stock at a glance
  4. User views product detail and sees complete change history (what changed when)
  5. User selects 50 products with checkboxes and initiates bulk update operation
**Plans**: TBD

Plans:
- [ ] 11-01: Multi-field search and advanced filtering
- [ ] 11-02: Version history, diff visualization, and bulk selection

### Phase 12: Tier System Architecture
**Goal**: Implement multi-tier capability routing from basic LLM calls to full Claude Code agents
**Depends on**: Phase 10
**Requirements**: TIER-01, TIER-02, TIER-03, TIER-04, TIER-05, TIER-06, TIER-07, TIER-08
**Success Criteria** (what must be TRUE):
  1. Tier 1 user queries route to OpenRouter LLM API (no agent capabilities)
  2. Tier 2 user can trigger agentic workflows that execute in background
  3. Tier 3 user has access to full Claude Code agents with GSD skills
  4. UI shows/hides features based on user tier (Tier 1 sees simplified interface)
  5. Tier 3 agent can call Tier 2 workflows during complex operations
**Plans**: TBD

Plans:
- [ ] 12-01: Tier detection and routing logic
- [ ] 12-02: Tier 1 (LLM) and Tier 2 (Agentic) implementation
- [ ] 12-03: Tier 3 (Full Agents) and cross-tier interaction

### Phase 13: Integration Hardening & Deployment
**Goal**: Harden external API integrations and prepare production deployment infrastructure
**Depends on**: Phase 11, Phase 12
**Requirements**: INTEGRATE-01, INTEGRATE-02, INTEGRATE-03, INTEGRATE-04, INTEGRATE-05, INTEGRATE-06, INTEGRATE-07, INTEGRATE-08, DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06, DEPLOY-07, DEPLOY-08
**Success Criteria** (what must be TRUE):
  1. Shopify API rate limiting respects X-Shopify-Shop-Api-Call-Limit header automatically
  2. OpenAI/Gemini API costs stop at configured budget cap per day/month
  3. External service failures trigger circuit breaker after 3 consecutive errors
  4. Production deployment includes automated database backups every 6 hours
  5. Health monitoring alerts developer when any service is down for 2+ minutes
**Plans**: TBD

Plans:
- [ ] 13-01: API rate limiting and circuit breakers
- [ ] 13-02: Cost monitoring and fallback strategies
- [ ] 13-03: Production deployment and monitoring infrastructure

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → ... → 13

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Codebase Cleanup & Analysis | 0/3 | Not started | - |
| 2. Docker Infrastructure Foundation | 0/3 | Not started | - |
| 3. Database Migration (SQLite to PostgreSQL) | 0/2 | Not started | - |
| 4. Authentication & User Management | 0/2 | Not started | - |
| 5. Backend API Design | 0/2 | Not started | - |
| 6. Job Processing Infrastructure (Celery) | 0/2 | Not started | - |
| 7. Frontend Framework Setup (Next.js) | 0/3 | Not started | - |
| 8. Product Resolution Engine | 0/2 | Not started | - |
| 9. Real-Time Progress Tracking | 0/2 | Not started | - |
| 10. Conversational AI Interface | 0/3 | Not started | - |
| 11. Product Search & Discovery | 0/2 | Not started | - |
| 12. Tier System Architecture | 0/3 | Not started | - |
| 13. Integration Hardening & Deployment | 0/3 | Not started | - |
