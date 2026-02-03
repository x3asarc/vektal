# Project Research Summary

**Project:** Shopify Multi-Supplier Platform
**Domain:** Brownfield Flask Application Modernization - Docker Containerization + Web Dashboard
**Researched:** 2026-02-03
**Confidence:** HIGH

## Executive Summary

This research covers the transformation of an existing Flask-based Shopify multi-supplier platform from a monolithic Python application into a containerized microservices architecture with a modern web dashboard. The platform currently handles product scraping from multiple vendors, AI-powered image enrichment (CLIP embeddings, visual search), and Shopify catalog synchronization through CLI tools and background jobs.

The recommended approach uses Docker Compose orchestration with React (Next.js 16) frontend, PostgreSQL replacing SQLite, Celery workers for async job processing, and a phased migration strategy that protects the production core (src/core/) while modernizing incrementally. This brownfield migration prioritizes safety through Plan-Then-Execute patterns, specialist agent orchestration for cleanup tasks, and comprehensive health checks and monitoring.

The critical risks center on three areas: (1) encryption key preservation during database migration (permanent credential loss if mishandled), (2) distributed monolith anti-pattern (containerizing without proper service boundaries), and (3) production server misconfiguration (Flask dev server, worker tuning, connection pooling). Mitigation requires explicit phase gates for verification, pre-migration key documentation, and architectural boundaries enforced from Phase 1.

## Key Findings

### Recommended Stack

The containerization stack leverages Docker Compose for development and production deployment (<20 services scale), with python:3.12-slim-bookworm base images for compatibility with ML dependencies (PyTorch, CLIP, Pillow). Gunicorn replaces Flask's development server, PostgreSQL replaces SQLite for multi-service concurrent access, and Redis serves dual purpose as Celery message broker and application cache.

**Core technologies:**
- **Docker Compose 3.8+**: Multi-container orchestration — 5x faster deployment than Kubernetes at this scale, production-ready for <20 services
- **Python 3.12-slim**: Container base — 149MB image with glibc compatibility for ML wheels (2min builds vs 15min with Alpine)
- **Gunicorn 22.0+**: WSGI server — production-grade Flask server with worker concurrency, better than uWSGI for 2026 containerized Flask
- **PostgreSQL 16+**: Primary database — replaces SQLite, provides concurrent multi-service access with row-level locking and JSONB flexibility
- **Celery 5.4+ + Redis 7.4+**: Background jobs — mature async task queue with simpler Redis broker vs RabbitMQ (already needed for caching)
- **Playwright 1.57+**: Browser automation — official Docker image, faster and more reliable than Selenium for containerized scraping
- **Nginx 1.27+**: Reverse proxy — load balancing, static files, SSL termination in 40MB Alpine image

**Version compatibility critical:** Celery 5.4+ requires Redis 7.x (avoid 6.0.x due to result backend issues); Playwright needs official mcr.microsoft.com/playwright/python image.

### Expected Features

The web dashboard targets non-technical craft/hobby store owners who need progressive onboarding, CSV upload with real-time progress monitoring, and approval workflows before applying changes to Shopify. Future expansion requires modular micro-frontend architecture for separate analytics, image management, scraping, and product apps.

**Must have (table stakes):**
- **User authentication (Flask OAuth)** — foundational for all features, already built in backend
- **CSV file upload with progress** — core workflow for 100+ product uploads with chunked uploads (500 KB), real-time progress bars, error handling
- **Real-time job monitoring** — live status updates (queued, processing, complete, error) for long-running scrape jobs to build user confidence
- **Progressive onboarding flow** — 3-step wizard (Connect Shopify → Upload CSV → Preview changes) to reduce anxiety for non-technical users
- **Product search/filtering** — verify uploaded products match Shopify catalog with debounced search
- **Approval workflow** — preview diff of changes before applying to Shopify to reduce accidental overwrite risk

**Should have (competitive):**
- **Bulk operations** — process 100+ products at once with queue visibility and optimistic updates
- **Image similarity detection** — auto-group visually similar products using existing CLIP embeddings with clustering visualization
- **Modular app switching** — seamless navigation between Analytics, Images, Scraping, Products apps via Module Federation

**Defer (v2+):**
- **Modular analytics app** — separate app for sales trends, inventory forecasting (trigger: 100+ active users)
- **Image management app** — bulk image uploads, similarity detection, alt-text generation (trigger: users managing 1000+ images)
- **Scraping job configurator** — visual builder for custom vendor rules (trigger: users want new vendors without developer help)
- **Multi-user collaboration** — real-time co-editing, comments, multi-reviewer workflows (trigger: enterprise customers with 10+ users)

**Avoid (anti-features):**
- Real-time everything (WebSocket for all views) — use SSE for job progress, polling for product lists, WebSocket only when truly needed
- Inline spreadsheet editing — users prefer Excel then CSV upload over complex in-app grid editing
- Custom dashboard builder — non-technical users want simple layouts, not drag-drop widgets (2-3 months dev time for rarely-used feature)

### Architecture Approach

The architecture follows an agent-driven brownfield cleanup pattern with Plan-Then-Execute safety gates, specialist subagent orchestration, and explicit protection of production core modules. The transformation separates concerns into distinct Docker services (web UI, REST API, Celery workers, scraping service, data stores) while maintaining backwards compatibility during migration.

**Major components:**
1. **Discovery & Classification Agent** — AST analysis (vulture, deadcode) to classify scripts as production/experimental/one-off, map dependencies, generate cleanup plan (Plan Mode, read-only)
2. **Specialist Subagents** — domain-specific agents with limited scope: Archiver (move one-off scripts with metadata), Consolidator (merge duplicate CLIs), Test Migrator (pytest structure), Documentation (architecture updates)
3. **Safety Verification Layer** — import validation, test suite execution, production core shield to verify no breakage after each operation
4. **Docker Service Layer** — separate containers for web (Flask+Gunicorn), API (Flask-RESTX), celery_worker (async jobs), flower (monitoring), nginx (reverse proxy), PostgreSQL, Redis

**Key patterns:**
- **Plan-Then-Execute with gates:** Plan Mode generates human-reviewable roadmap before any file modifications, execution has checkpoints after each phase
- **Protected core:** src/core/ (18 production modules) explicitly marked untouchable without approval, hooks block unauthorized edits
- **Parallel worktree execution:** Independent cleanup tasks (archival, test migration, CLI consolidation) run in separate git worktrees for 3x parallelization
- **Code-simplifier post-merge:** Anthropic's code-simplifier plugin normalizes consolidated code after merging duplicates (20-30% token reduction)

**Data flow:** Discovery → Plan (human approval) → Specialist execution → Safety verification → Commit per phase with rollback capability

### Critical Pitfalls

Research identified 10 critical pitfalls with domain-specific prevention strategies. Top 5 by severity and recovery cost:

1. **Encryption key loss during SQLite→PostgreSQL migration** — Credentials encrypted with specific keys become permanently inaccessible if keys aren't documented before migration. Prevention: back up complete .env files, test decryption of sample credentials, use secrets manager (Vault, AWS Secrets Manager) before starting migration. Addressed in Phase 2 (Database Migration).

2. **Distributed monolith (containerization without service boundaries)** — Splitting code into containers but maintaining shared database, tight coupling, synchronous dependencies creates "worst of both worlds" (microservices complexity without benefits). Prevention: define service boundaries by business capability, database-per-service pattern, async communication (message queues), API contracts instead of shared imports. Addressed in Phase 1 (Architecture Planning).

3. **Environment variables exposing secrets in production** — Secrets in ENV vars are visible via docker inspect, process lists, logs, crash dumps with no access control or audit trail. Prevention: use Docker Secrets, external secrets manager (Vault, Doppler), file-based secret mounts, never embed in images. Addressed in Phase 1 (Containerization Setup).

4. **Database connection pool exhaustion across containers** — Multiple containerized services each create pools (5-10 connections) quickly exhausting PostgreSQL max_connections=100. Formula: (pool_size + max_overflow) × containers > max_connections = failures. Prevention: calculate total connection budget, configure SQLAlchemy conservatively (pool_size=2-5), implement PgBouncer sidecar, monitor pg_stat_activity. Addressed in Phase 2 (Database Migration).

5. **Missing rate limiting and circuit breakers for external APIs** — Shopify API rate limits, OpenAI/Gemini cost explosions, vendor IP bans from retry storms when microservices scale horizontally multiplying API calls. Prevention: respect X-Shopify-Shop-Api-Call-Limit headers, implement leaky bucket algorithm, set budget caps with token counting, add circuit breakers (fail X times → stop for Y duration). Addressed in Phase 3 (External Integration).

**Additional high-impact pitfalls:**
- **Flask dev server in production** — single-threaded, blocks concurrent requests (use Gunicorn with workers: (2×cores)+1)
- **Gunicorn worker misconfiguration** — sync workers for I/O-bound scraping tasks block all requests (use gevent/eventlet async workers)
- **Logging to container filesystem** — logs lost on restart, no centralization (log to stdout/stderr, Docker json-file driver with rotation)
- **Monolith divergence during migration** — bug fixes only go to production monolith while microservices branch becomes outdated (use Strangler Fig pattern, backport critical fixes)

## Implications for Roadmap

Based on research, suggested phase structure prioritizes safety verification gates, incremental migration, and early establishment of architectural boundaries:

### Phase 1: Containerization Foundation
**Rationale:** Establish Docker infrastructure and service boundaries before migrating production data or users. This phase sets architectural constraints (no shared database, API contracts, health checks) that prevent distributed monolith anti-pattern.

**Delivers:**
- Docker Compose multi-service setup (web, worker, db, redis, nginx)
- Production WSGI server configuration (Gunicorn with worker tuning)
- Secrets management architecture (Docker secrets, not ENV vars)
- Health check endpoints (/health, /ready) for all services
- Logging to stdout/stderr with json-file rotation

**Addresses features:**
- User authentication (Flask OAuth integration in containerized environment)
- Foundation for CSV upload and job monitoring (service structure ready)

**Avoids pitfalls:**
- Flask dev server in production (Gunicorn configured from start)
- Environment variable secrets (secrets architecture designed before production)
- Distributed monolith (service boundaries enforced via architecture review)
- Missing health checks (required in Dockerfile and compose)

**Research flag:** STANDARD PATTERNS — Docker Compose + Flask containerization is well-documented, skip research-phase.

### Phase 2: Database Migration (SQLite → PostgreSQL)
**Rationale:** Must come after containerization (Phase 1) to have proper connection pooling and multi-service architecture in place. This is the highest-risk phase due to encryption key preservation requirement.

**Delivers:**
- PostgreSQL 16 container with persistent volumes
- SQLite data migration with encrypted credential verification
- Connection pool configuration (SQLAlchemy pool_size, max_overflow)
- Secrets manager implementation (Vault or AWS Secrets Manager)
- Migration rollback plan and backups

**Uses stack elements:**
- PostgreSQL 16-alpine container
- psycopg2-binary for Python adapter
- Docker volumes for data persistence

**Addresses pitfalls:**
- Encryption key loss (pre-migration checklist: document keys, test decryption, backup .env files)
- Connection pool exhaustion (calculate budget: max_connections / services, configure SQLAlchemy conservatively)

**Research flag:** NEEDS RESEARCH — Encryption key migration for Shopify/OpenAI credentials is domain-specific, use /gsd:research-phase for safe migration procedures.

### Phase 3: Background Job Processing (Celery + Redis)
**Rationale:** Depends on Phase 2 (PostgreSQL for job tracking) and Phase 1 (Docker services). Enables real-time job monitoring and CSV upload features by offloading scraping to async workers.

**Delivers:**
- Celery worker containers with async job queue
- Redis as message broker and cache (dual purpose)
- Flower monitoring dashboard at localhost:5555
- Long-running scraping task isolation from web requests

**Implements architecture components:**
- Celery workers with gevent async workers (for I/O-bound scraping)
- Redis broker configuration with proper queue limits
- Worker health checks and auto-scaling patterns

**Addresses features:**
- Real-time job monitoring (Celery task status tracking)
- CSV upload with progress (chunked upload → Celery job → progress updates)

**Avoids pitfalls:**
- Gunicorn worker misconfiguration (scraping offloaded to Celery, web uses sync workers)
- Synchronous scraping blocking API (async job pattern from start)

**Research flag:** STANDARD PATTERNS — Celery + Flask + Redis is established pattern, skip research-phase.

### Phase 4: React Dashboard Frontend
**Rationale:** Comes after backend services are stable (Phases 1-3) so API contracts are clear. React enables progressive onboarding, file upload with progress, and future modular micro-frontend architecture.

**Delivers:**
- Next.js 16 frontend with TypeScript
- CSV upload component (react-dropzone + axios chunked uploads)
- Real-time job monitoring (React Query + SSE/WebSocket)
- Progressive onboarding (Joyride library, 3-step wizard)
- Approval workflow (preview diff before Shopify apply)

**Uses stack elements:**
- Next.js 16 with Server Components and PPR
- Flask-CORS for API access
- WebSocket/SSE for real-time updates

**Addresses features:**
- Progressive onboarding flow (React onboarding libraries: Joyride, Shepherd)
- CSV upload with progress (axios onUploadProgress + React hooks)
- Product search (debounced search with React state management)
- Approval workflow (diff viewer components from React ecosystem)

**Research flag:** STANDARD PATTERNS — React + Flask integration has Miguel Grinberg 2025 guide and established patterns, skip research-phase.

### Phase 5: Brownfield Cleanup (Automated)
**Rationale:** After containerization and frontend are stable, use agent-driven cleanup to remove one-off scripts, consolidate duplicate CLIs, migrate tests to pytest structure. This phase has high automation potential with low user-facing risk.

**Delivers:**
- Archive of one-off scripts (apply_*, scrape_*, fix_*, dry_run_*) with manifest
- Consolidated CLI tools (unified cli/products.py with subcommands)
- Pytest test structure (tests/unit/, tests/integration/, conftest.py)
- Pruned dependencies (requirements.txt cleanup)
- Updated documentation (ARCHITECTURE.md, README.md)

**Uses architecture patterns:**
- Plan-Then-Execute with specialist subagents (Archiver, Consolidator, Test Migrator)
- Safety verification after each operation (import checks, test runs)
- Git worktree parallel execution for independent tasks
- Code-simplifier post-consolidation normalization

**Avoids pitfalls:**
- Autonomous delete without human review (Plan Mode generates candidates, human approves)
- Production core modifications (src/core/ explicitly protected)
- Missing safety verification (tests run after every change)

**Research flag:** STANDARD PATTERNS — Awesome-claude-code workflows and Python cleanup tools documented, skip research-phase.

### Phase 6: External API Integration Hardening
**Rationale:** Must come after service scaling (multiple containers calling external APIs concurrently). Implements rate limiting, circuit breakers, cost monitoring to prevent Shopify bans and OpenAI bill surprises.

**Delivers:**
- Shopify API rate limiting (leaky bucket, respect X-Shopify-Shop-Api-Call-Limit)
- OpenAI/Gemini budget caps and token counting
- Vendor scraping rate limits (per-vendor delays, user agent rotation)
- Circuit breakers (pybreaker library, fail-fast patterns)
- Cost monitoring dashboard (real-time API usage tracking)

**Addresses pitfalls:**
- Missing rate limiting (429 errors, IP bans, cost explosions)
- Circuit breakers for external failures (services degrade gracefully, don't crash)

**Research flag:** NEEDS RESEARCH — Shopify API rate limit strategies and OpenAI cost control for production scale warrant /gsd:research-phase.

### Phase Ordering Rationale

- **Phase 1 first (Containerization):** Establishes architectural boundaries and production server config before data migration or user traffic, preventing distributed monolith and Flask dev server pitfalls.
- **Phase 2 before 3 (Database before Jobs):** PostgreSQL must be ready for Celery to track job state; encryption key preservation is critical checkpoint before async processing.
- **Phase 3 before 4 (Backend before Frontend):** API contracts must be stable before React integration; job processing infrastructure needed for CSV upload feature.
- **Phase 4 before 5 (Features before Cleanup):** Deliver user value (dashboard) before internal refactoring; cleanup happens when system is stable and testable.
- **Phase 6 last (API Hardening):** Rate limiting only matters at scale; implement after horizontal scaling reveals concurrency issues.

**Dependency chain:** Containerization → Database → Background Jobs → Frontend → Cleanup → API Hardening

**Parallel opportunities:** Phase 5 (Cleanup) can partially overlap Phase 4 (Frontend) if frontend and backend teams are separate; use git worktrees.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Database Migration):** Encryption key migration for Shopify OAuth, OpenAI API keys is high-risk and domain-specific; research safe migration procedures and test decryption workflows.
- **Phase 6 (API Hardening):** Shopify rate limit algorithms (leaky bucket implementation) and OpenAI cost control at production scale need /gsd:research-phase for optimal strategies.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Containerization):** Docker Compose + Flask + Gunicorn is extensively documented (official Docker docs, Miguel Grinberg guides, TestDriven.io tutorials).
- **Phase 3 (Celery + Redis):** Mature pattern with official Celery docs and Flask integration guides.
- **Phase 4 (React + Flask):** Miguel Grinberg's 2025 guide provides step-by-step brownfield migration patterns; Next.js 16 integration well-documented.
- **Phase 5 (Cleanup):** Awesome-claude-code workflows (Plan Mode, specialist subagents, code-simplifier) and Python tools (vulture, deadcode) are established.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified with official docs (Docker, Celery, Flask), 2026 sources for Playwright over Selenium, python:slim vs Alpine rationale backed by ML dependency research |
| Features | HIGH | React vs Vue vs Svelte comparison based on multiple 2026 sources, Miguel Grinberg's authoritative 2025 Flask+React guide, SaaS UX patterns from design research |
| Architecture | HIGH | Agent-driven cleanup patterns verified with official Claude Code workflows, awesome-claude-code community resources, Plan Mode documented in official docs |
| Pitfalls | MEDIUM-HIGH | Critical pitfalls sourced from official docs (Docker, Flask, Gunicorn) and recent 2026 production deployment sources; encryption key loss and distributed monolith from migration case studies |

**Overall confidence:** HIGH

Research is comprehensive across all four domains with verification from official sources (Docker, Flask, Celery, Claude Code), authoritative community guides (Miguel Grinberg), and 2026-current best practices. Medium-HIGH for pitfalls reflects that some risks (encryption key loss, distributed monolith) are inferred from general migration challenges rather than domain-specific documented cases.

### Gaps to Address

**Gap 1: Shopify OAuth encryption specifics**
- **Issue:** Research confirms encryption key preservation is critical but doesn't specify which fields in SQLite are encrypted or how Shopify OAuth tokens are stored.
- **Handling:** During Phase 2 planning, audit existing SQLite schema to identify encrypted columns, document encryption library used (cryptography, PyCrypto), test decryption in staging before production migration.

**Gap 2: React Module Federation at brownfield scale**
- **Issue:** Module Federation is proven at enterprise scale (Spotify, ByteDance) but research doesn't cover integration complexity for this specific Flask backend.
- **Handling:** Defer to Phase 4+ (post-MVP); if modular apps become priority, use /gsd:research-phase for Flask + Module Federation + shared auth patterns.

**Gap 3: Optimal Gunicorn worker count for scraping + API hybrid**
- **Issue:** Research provides formula (2×cores)+1 for sync workers and recommends gevent for I/O-bound tasks, but doesn't specify configuration for services that handle both API requests and scraping tasks.
- **Handling:** During Phase 1, configure separate services: web service (sync workers for API) and scraper service (gevent workers for browser automation); avoid hybrid workers.

**Gap 4: PgBouncer vs SQLAlchemy pooling trade-offs**
- **Issue:** Research mentions both PgBouncer sidecar and SQLAlchemy pool configuration but doesn't specify when to use which.
- **Handling:** During Phase 2, start with SQLAlchemy pooling (simpler); add PgBouncer only if connection exhaustion occurs despite conservative pool config (indicates need for connection multiplexing).

## Sources

### Primary (HIGH confidence)
- [Docker Compose Official Documentation](https://docs.docker.com/compose/) — service orchestration, networking, volumes
- [Celery Official Documentation](https://docs.celeryq.dev/en/stable/getting-started/introduction.html) — async task queues, broker configuration
- [Flask Official Deployment Guide](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/) — Gunicorn/uWSGI production server setup
- [Playwright Python Docker](https://playwright.dev/python/docs/docker) — official containerization guide
- [Claude Code Official Workflows](https://code.claude.com/docs/en/common-workflows) — Plan Mode, refactoring patterns
- [Miguel Grinberg: Create a React + Flask Project in 2025](https://blog.miguelgrinberg.com/post/create-a-react-flask-project-in-2025) — authoritative brownfield migration guide

### Secondary (MEDIUM confidence)
- React vs Vue vs Svelte 2026 comparisons (Medium articles, Merge.rocks, H7W team rebuild analysis)
- Docker best practices (TestDriven.io, OneUpTime blog, Cyberpanel)
- Microservices migration challenges (NG Logic, HQ Software Lab, Komodor)
- Secrets management 2026 (Security Boulevard, GitGuardian, Phase.dev)
- Python static analysis tools (vulture GitHub, deadcode PyPI, Meta's SCARF system)

### Tertiary (LOW confidence)
- SaaS UX patterns 2026 (OneThing Design, Orbix Studio) — informed feature prioritization but not technical implementation
- Awesome-claude-code community workflows — patterns verified against official docs before recommendation

---
*Research completed: 2026-02-03*
*Ready for roadmap: yes*
