# Shopify Multi-Supplier Platform

## What This Is

A production SaaS platform for craft/hobby stores to automate multi-vendor product management on Shopify. The system intelligently scrapes supplier data, enriches products with AI-powered SEO and image analysis, and maintains 4,000+ SKU catalogs with minimal manual intervention. Currently deployed at Bastelschachtel.at, transitioning from CLI-based tool to multi-tenant web platform with modular apps (analytics, image management, scraping jobs, product management).

## Core Value

Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, image editing, or content writing.

## Current Milestone: v1.0 Production-Ready Architecture

**Goal:** Transform organic codebase into maintainable, containerized architecture ready for SaaS scaling.

**Target outcomes:**
- Clean, organized codebase (30+ scripts archived, duplicates consolidated)
- Docker-based microservices architecture (frontend, backend, scrapers, workers)
- Modern web dashboard with progressive onboarding (starting with simplified MVP)
- Agent-driven cleanup and migration (autonomous refactoring where possible)
- Production deployment-ready containers with clear boundaries

## Requirements

### Validated

**Production Infrastructure (Currently Working):**
- ✓ Flask OAuth app with Shopify integration
- ✓ Pipeline orchestration engine (CSV → scrape → enrich → approve → apply)
- ✓ Vision AI image analysis (Gemini) + SEO generation (GPT-4)
- ✓ Safety mechanisms (dry-run, approval workflow, rollback, safeguards doc)
- ✓ Multi-vendor scraping (Python BeautifulSoup/Selenium + JS Playwright)
- ✓ Image processing framework (YAML-driven transformations)
- ✓ Shopify GraphQL API integration (products, variants, media, inventory)
- ✓ Job tracking and resume capability (SQLite databases)

**Proven Workflows:**
- ✓ Bulk CSV upload → automated processing → results tracking
- ✓ Single product CLI operations with approval workflow
- ✓ Image replacement with vision AI verification
- ✓ German SEO content generation

### Active

<!-- Milestone v1.0 scope - building toward these -->

**Phase 1: Codebase Cleanup & Analysis**
- [ ] Archive 30+ one-off scripts (apply_*, scrape_*, fix_*, dry_run_*)
- [ ] Consolidate duplicate CLI tools (5 update scripts → unified interface)
- [ ] Organize tests (move to tests/, adopt pytest)
- [ ] Document architecture (create comprehensive ARCHITECTURE.md)
- [ ] Agent-driven code analysis (identify dead code, dependencies, patterns)

**Phase 2: Python vs JavaScript Scraper Strategy**
- [ ] Agent analysis of both implementations (performance, maintainability, coverage)
- [ ] Clear boundary definition (what stays Python, what stays JS, integration points)
- [ ] Unified vendor configuration (single YAML source of truth)
- [ ] Scraper interface standardization (input/output contracts)

**Phase 3: Docker Architecture Design**
- [ ] Container strategy (services: frontend, API, scrapers, workers, databases)
- [ ] Network and data flow design (how containers communicate)
- [ ] Configuration management (env vars, secrets, volume mounts)
- [ ] Development vs production environments
- [ ] Docker Compose orchestration

**Phase 4: Backend Containerization**
- [ ] Flask API container (src/core/* modules exposed as REST/GraphQL)
- [ ] Worker container (job processing, background tasks)
- [ ] Database containers (PostgreSQL for app data, Redis for queues)
- [ ] Scraper container (unified scraping service)
- [ ] API documentation (OpenAPI/Swagger)

**Phase 5: Frontend Framework & Architecture**
- [ ] Agent analysis and recommendation (React/Vue/Svelte vs Flask+HTMX)
- [ ] Frontend container setup
- [ ] Progressive onboarding UI (simplified initial experience)
- [ ] Core navigation structure (routing to future modular apps)
- [ ] API integration layer

**Phase 6: MVP Web Dashboard**
- [ ] Simplified onboarding flow (connect Shopify, understand your products)
- [ ] Single unified interface (Phase 1 of modular vision)
- [ ] Job submission and monitoring (upload CSV, track progress)
- [ ] Results view (success/failure, preview changes, approve)
- [ ] Basic product search and view

**Phase 7: Deployment & Integration**
- [ ] Docker Compose for full stack (all containers working together)
- [ ] Environment configuration (dev, staging, production)
- [ ] Data migration from current setup (databases, CSVs)
- [ ] Integration testing (end-to-end workflows)
- [ ] Production deployment readiness (CI/CD, monitoring, logs)

### Out of Scope

<!-- Explicitly excluded from v1.0 -->

- **Modular app separation (Analytics, Image Mgmt, Scraping, Products)** — v1.0 has unified interface; modularization comes in v2.0
- **Multi-tenant architecture** — v1.0 is single-tenant ready for SaaS; multi-tenancy in v2.0
- **Mobile app** — Web-first, mobile later
- **Real-time notifications** — Email/polling sufficient for v1.0
- **Advanced analytics** — Basic reporting only; full analytics in v2.0
- **Multiple Shopify store support** — Single store per instance in v1.0
- **User management/teams** — Single user per instance for now
- **Billing/subscriptions** — Not needed for v1.0 (single deployment)

## Context

### Current State

- **Deployment:** Production use at Bastelschachtel.at (4,000 SKUs)
- **Architecture:** Monolithic Python app + scattered CLI scripts
- **Codebase:** Organic growth; 50 root scripts, 18 core modules, production-tested but needs organization
- **Technical debt:** Duplication (5 update scripts, 2 scraper implementations), scattered tests, no containerization
- **Strengths:** Battle-tested safety mechanisms, advanced AI integration, configuration-driven

### User Feedback Themes

1. **"Too many scripts"** - Need unified interface, not 10 different CLI tools
2. **"Hard to see what will happen"** - Want preview before changes (dry-run exists but CLI-only)
3. **"Onboarding is complex"** - Need simpler initial experience for new users
4. **"Want to monitor jobs"** - Web UI for progress tracking essential

### Technical Environment

- **Current:** Python 3.12+, Flask, SQLite, Selenium/Playwright, OpenAI/Gemini APIs
- **Target:** Containerized microservices, modern frontend framework, PostgreSQL, Redis
- **External:** Shopify GraphQL API, 8 vendor websites, AI APIs (OpenAI, Gemini)

## Constraints

- **Shopify API**: GraphQL only, rate limits (throttling logic required)
- **AI Budget**: Vision AI capped at €1/day, €30/month (caching critical)
- **Vendor Scraping**: Respect robots.txt, implement delays, handle anti-scraping
- **Data Privacy**: Store credentials securely, no API keys in code
- **Backward Compatibility**: Existing Bastelschachtel.at deployment must continue working during migration
- **German Language**: SEO and content generation must support German e-commerce conventions

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cleanup before features | 30+ scripts make codebase unmaintainable; organize first, then build | — Pending |
| Agent-driven refactoring | Leverage awesome-claude-code + GSD for autonomous cleanup | — Pending |
| Docker-first architecture | Scalability requirement; separates concerns, enables multi-tenant future | — Pending |
| Progressive onboarding | Users overwhelmed by modular apps immediately; start simple, grow complexity | — Pending |
| Python scraper vs JS scraper | Both exist; agents will analyze and recommend clear strategy | — Pending |
| Frontend framework | React/Vue/Svelte vs Flask templates; agents will evaluate and recommend | — Pending |

---
*Created: 2026-02-03 after repository evaluation*
*Last updated: 2026-02-03 during milestone v1.0 initialization*
