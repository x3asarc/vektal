# Project Directory Structure

**Last updated:** 2026-03-02 (v1.0 complete)

This document explains the purpose of the repository layout in its current state.
It is a human-readable guide (not a raw file dump). For the complete tracked tree,
see `docs/MASTER_MAP.md`.

## Root Directory Overview

The repository root currently includes governance/planning artifacts, product code,
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
  - `reports/meta/` - journey synthesis and meta artifacts
- **`ops/`** - Governance structure and role definitions
  - `STRUCTURE_SPEC.md`
  - `governance/roles/*.md`
- **`docs/`** - Project documentation
  - `MASTER_MAP.md` - full tracked file tree + module map
  - `DIRECTORY_STRUCTURE.md` - this high-level structure guide
- **`solutionsos/`** - Governance policy blueprint references

### Application Code

- **`src/`** - Primary backend and orchestration code
  - API (`src/api/`)
  - Core domain/runtime logic (`src/core/`)
  - Graph/self-healing systems (`src/graph/`)
  - Data models (`src/models/`)
  - Assistant runtime/governance (`src/assistant/`)
  - CLI surfaces (`src/cli/`)
- **`frontend/`** - Next.js frontend application
  - Feature modules (`frontend/src/features/`)
  - App routes (`frontend/src/app/`)
- **`scripts/`** - Operational and governance automation
  - graph bootstrap/status/remediation scripts
  - governance gate and validation scripts
  - hook-related scripts
- **`migrations/`** - Alembic migrations and schema evolution
- **`tests/`** - Automated verification (unit/integration/API/graph/assistant)

### Infrastructure and Integrations

- **`config/`** - Config files and environment-specific settings
- **`nginx/`** - Reverse proxy config
- **`secrets/`** - Secret-management helper artifacts
- **`web/`** - Web/static assets used by legacy or operational flows
- **`seo/`** - SEO-related module/artifacts
- **`utils/`** - Utility scripts and helpers

### Tooling and Assistant Environments

- **`.claude/`** - Claude workflows, hooks, skills, and command docs
- **`.codex/`** - Codex local hook/config artifacts
- **`.gemini/`** - Gemini local hook/config artifacts
- **`.github/`** - GitHub workflows and repo automation
- **`.obsidian/`** and **`Vektal/`** - linked knowledge/workspace artifacts

### Archive and Historical Assets

- **`archive/`** - Archived scripts/directories from cleanup phases

## Current Lifecycle Snapshot

- Phases `1` through `15` are complete (`GREEN`) in `.planning/ROADMAP.md`.
- v1.0 state is marked complete in `.planning/STATE.md`.
- No active phase execution is open; next work is in future phases:
  - Production Refinement & Integration Cleanup
  - User Data Knowledge Graph & Semantic Search

## Organization Principles

1. `.planning/ROADMAP.md` and `.planning/STATE.md` are canonical for lifecycle state.
2. Every closed task must have exactly four reports in `reports/<phase>/<task>/`.
3. Governance, standards, and structure contracts are rooted in:
   - `AGENTS.md`
   - `STANDARDS.md`
   - `ops/STRUCTURE_SPEC.md`
4. Implementation code lives in `src/` and `frontend/`; operational code lives in `scripts/`.
5. The complete file-level inventory is maintained in `docs/MASTER_MAP.md`.

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
