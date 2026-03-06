# Project Directory Structure

**Last updated:** 2026-03-06 (v1.1 - Agent Context OS & Sentry Intake Sync)

This document explains the purpose of the repository layout in its current state.
It is a human-readable guide (not a raw file dump). For the complete tracked tree,
see `docs/MASTER_MAP.md`.

## Root Directory Overview

The repository root includes governance/planning artifacts, product code,
frontend code, tests, operational scripts, and supporting assistant tooling.

### Essential Root Files

| File | Purpose |
|---|---|
| `README.md` | Project overview and onboarding entry point |
| `ARCHITECTURE.md` | System architecture and subsystem boundaries |
| `AGENTS.md` | Governance constitution and role boundaries |
| `STANDARDS.md` | Severity model and review/gate policy |
| `requirements.txt` | Python dependency lock/pin surface |
| `pyproject.toml` | Python tooling and pytest configuration |
| `docker-compose.yml` | Local stack orchestration |
| `docker-compose.secrets.yml` | Secrets-aware compose overlay |
| `Dockerfile.backend` | Backend image definition |
| `.env.example` | Environment variable template |
| `.rules` | Machine-checkable governance policy lines |
| `FAILURE_JOURNEY.md` | Failure memory and anti-loop learnings |
| `LEARNINGS.md` | Cumulative project learnings and patterns |
| `GEMINI.md` | Gemini CLI configuration and project context |

## Core Directories

### Governance and Planning

- **`.planning/`** - Canonical lifecycle + execution state
  - `ROADMAP.md` - phase/plan lifecycle source of truth
  - `STATE.md` - current operational project state
  - `phases/` - context, research, plans, and summaries per phase
- **`reports/`** - Governance gate evidence
  - `reports/<phase>/<task>/` - required four reports:
    - `self-check.md`
    - `review.md`
    - `structure-audit.md`
    - `integrity-audit.md`
- **`ops/`** - Governance structure and role definitions
  - `STRUCTURE_SPEC.md`
  - `governance/roles/*.md`
- **`docs/`** - Project documentation
  - `MASTER_MAP.md` - full tracked file tree + module map
  - `DIRECTORY_STRUCTURE.md` - this high-level structure guide
  - `AGENT_START_HERE.md` - Primary onboarding entrypoint
- **`solutionsos/`** - Governance policy blueprint references

### Application Code

- **`src/`** - Primary backend and orchestration code
  - API (`src/api/`) - Flask/OpenAPI endpoints
  - Assistant (`src/assistant/`) - Runtime tiers and governance
  - Auth (`src/auth/`) - Authentication and session management
  - Billing (`src/billing/`) - Stripe and billing logic
  - Core (`src/core/`) - Domain logic, embeddings, and constants
  - Graph (`src/graph/`) - Neo4j/Graphiti query interfaces
  - Integrations (`src/integrations/`) - External service connectors (Sentry, etc.)
  - Jobs (`src/jobs/`) - Background processing definitions
  - Memory (`src/memory/`) - Context memory and event journaling
  - Models (`src/models/`) - SQLAlchemy database models
  - Resolution (`src/resolution/`) - Self-healing and auto-resolution logic
  - Tasks (`src/tasks/`) - Celery task definitions
  - CLI (`src/cli/`) - CLI surfaces
- **`frontend/`** - Next.js frontend application
  - Feature modules (`frontend/src/features/`)
  - App routes (`frontend/src/app/`)
- **`scripts/`** - Operational and governance automation
  - `governance/` - Gate and validation scripts
  - `context/` - Context OS verification scripts
  - `harness/` - Testing and SLA verification
- **`migrations/`** - Alembic migrations and schema evolution
- **`tests/`** - Automated verification (unit/integration/API/graph/assistant)
- **`universal_vendor_scraper/`** - Specialized scraper implementations

### Infrastructure and Integrations

- **`.graph/`** - Graph-related configuration and local data
- **`.memory/`** - Persistent event memory and context snapshots
- **`config/`** - Config files and environment-specific settings
- **`nginx/`** - Reverse proxy config
- **`secrets/`** - Secret-management helper artifacts
- **`web/`** - Web/static assets used by legacy or operational flows
- **`seo/`** - SEO-related module/artifacts
- **`utils/`** - Utility scripts and helpers

### Tooling and Assistant Environments

- **`.agents/`** - Agent-specific skills and configurations
- **`.claude/`** - Claude workflows, hooks, skills, and command docs
- **`.codex/`** - Codex local hook/config artifacts
- **`.gemini/`** - Gemini local hook/config artifacts
- **`.tooling/`** - Local development and assistant tooling
- **`.sandbox/`** - Hardened execution environment for code testing
- **`.github/`** - GitHub workflows and repo automation
- **`.vscode/`** - Workspace settings and debugger configs

### Archive and Historical Assets

- **`archive/`** - Archived scripts/directories from cleanup phases
- **`backups/`** - Database and state backups
- **`Vektal/`** - Linked knowledge/workspace artifacts (Obsidian)

## Current Lifecycle Snapshot

- **Phases 1-16 Complete:** Core Infrastructure, API, Frontend, AI, Knowledge Graph, Self-Healing, and Agent Context OS are fully implemented and verified.
- **Phase 15.1 Complete:** Sentry autonomous intake and verified auto-resolution is operational.
- **Next Steps:** Future production refinement (Priority 2-3) including Dokploy E2E and native LLM capability context.
- **Current Gate Status:** `GREEN` as of 2026-03-04 (Context OS compatibility gate passed).

## Organization Principles

1. `.planning/ROADMAP.md` and `.planning/STATE.md` are canonical for lifecycle state.
2. Every closed task must have exactly four reports in `reports/<phase>/<task>/`.
3. Implementation code lives in `src/` and `frontend/`; operational code lives in `scripts/`.
4. The complete file-level inventory is maintained in `docs/MASTER_MAP.md`.
5. **Graph-First:** All context operations use the Neo4j/Graphiti knowledge graph as the primary source.

## Finding What You Need

| I need to... | Look in |
|---|---|
| Understand project status/lifecycle | `.planning/ROADMAP.md`, `.planning/STATE.md` |
| Check governance rules | `AGENTS.md`, `STANDARDS.md`, `ops/STRUCTURE_SPEC.md` |
| Find implementation code | `src/`, `frontend/` |
| Run/inspect operational automation | `scripts/` |
| Review task closure evidence | `reports/<phase>/<task>/` |
| View full tracked filesystem tree | `docs/MASTER_MAP.md` |

---

This document is intentionally concise and explanatory. For exhaustive file-by-file listing, use `docs/MASTER_MAP.md`.
