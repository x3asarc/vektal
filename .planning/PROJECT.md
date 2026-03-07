# Vektal (Shopify Multi-Supplier Platform)

## What This Is

Vektal is a production-grade SaaS platform that automates multi-vendor Shopify product management for craft and hobby stores. It uses a graph-grounded AI assistant and an autonomous self-healing runtime to maintain accurate, SEO-optimized catalogs for 4,000+ SKUs across 8+ suppliers with minimal human intervention.

## Core Value

Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, image editing, or content writing, backed by a system that autonomously detects and resolves issues.

## Requirements

### Validated

- ✓ **Multi-Vendor Scraping** — Python (BS4/Selenium) and JS (Playwright) engines for 8+ suppliers.
- ✓ **AI Enrichment Pipeline** — Vision AI (Gemini) for images and GPT-4 for German SEO content.
- ✓ **Graph-First Context OS** — Neo4j/Graphiti knowledge graph as the primary context source for AI agents.
- ✓ **Self-Healing Runtime** — Sentry-driven intake and autonomous remediation for infrastructure issues.
- ✓ **Conversational Interface** — Real-time chat for product resolution, updates, and bulk imports.
- ✓ **Safety Gates** — Binary governance gates (Structure/Integrity) and multi-tier (T1/T2/T3) AI routing.

### Active

- [ ] **Unified Command Center** — Real-time dashboard for catalog integrity and ingestion health.
- [ ] **Hardened Ingestion Contracts** — Pydantic-based validation for all incoming vendor data.
- [ ] **Live Ingestion Listener** — SSE-based stream for tracking bulk jobs in the UI.
- [ ] **Rollback UX** — One-click restoration for low-confidence enrichment jobs.
- [ ] **Production Deployment** — Full-stack rollout to Dokploy with verified E2E browser tests.

### Out of Scope

- **Multi-Store Management** — v1.0 is strictly single-tenant (one Shopify store per instance) to ensure stability.
- **Native Mobile App** — Focus remains on a high-fidelity web dashboard; mobile is deferred to v2.0.
- **Third-Party Marketplace Integration** — Integration with Amazon/eBay is excluded to maintain focus on Shopify excellence.

## Context

- **Current State**: Transitioning from a verified v1.0 architecture to a production-refined command center.
- **User Feedback**: Operators need better visibility into "what the system is doing" during autonomous cycles.
- **Technical Debt**: Legacy scripts (30+) have been archived, but some integration hardening remains in Phase 17.
- **Ecosystem**: Relies on Shopify GraphQL API, Neo4j/Graphiti, and multi-model AI orchestration (Gemini/Claude).

## Constraints

- **Budget**: Vision AI processing is budget-capped at €1/day (enforced by `vision_cache`).
- **API Limits**: Shopify GraphQL rate limits require adaptive throttling (enforced in `shopify_apply.py`).
- **Language**: All SEO and enrichment content must be generated in German for the target market.
- **Security**: Binary context gate (`scripts/governance/context_os_gate.py`) must pass before any production mutation.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Graph-First RAG | Codebase complexity exceeded lexical search limits; Neo4j provides 100% awareness. | ✓ Good |
| Sentry-Driven Intake | Manual issue reporting was too slow for a self-healing system. | ✓ Good |
| Vanilla CSS over Tailwind | Maximum flexibility for distinctive frontend design without utility-class bloat. | ✓ Good |
| Tiered AI Routing | Balances cost (T1) with reasoning depth (T3) for complex tasks. | ✓ Good |

---
*Last updated: 2026-03-06 after Phase 16 closure & Phase 17 activation*
