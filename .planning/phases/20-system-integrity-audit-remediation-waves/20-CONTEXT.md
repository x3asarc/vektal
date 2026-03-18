# Phase 20 Amendment Context

## Date: 2026-03-18

---

## Discussion Evidence

**Discussion areas (at least 1):** Scope definition and folder verification

**Questions answered (4+):**
1. **Scope:** "Most folders (~20 folders)" selected for 8-surface audit
2. **Completeness:** "All 8 surfaces per folder" - ownership, blast-radius, import-chain, data-access, api-surface, async-surface, config-surface, cross-domain
3. **Depth:** "Deep analysis" - full dependency graphs, cross-domain coupling maps, comprehensive blast-radius analysis
4. **Confirmation:** Scope confirmed after verification - user requested verify-and-confirm loop
5. **Refinement:** Frontend was initially missed, user corrected. src/graph/, src/memory/, src/auth/, src/billing/ discovered during verification and added.
6. **Granularity:** User confirmed "do both" - src/ as one unit AND src/graph/, src/memory/, etc. as separate units
7. **Tests:** User confirmed "keep tests as one" - all subdirs under tests/ treated as single unit
8. **Final confirmation:** User said "yes" after verified scope presentation

**User answers captured:** yes

**Notes on discussion process:**
- User insisted on reading ARCHITECTURE.md first before confirming scope
- User requested folder-by-folder verification before final confirmation
- User caught that frontend/ was missing from initial proposal
- Multiple rounds of verification until user said "yes"

---

## Discussion Summary

This document captures the discussion and decisions made during the Phase 20 amendment planning session.

---

## Scope Definition

### Initial Proposal (Rejected)
- Broad scope with uncertain folder list
- Lacked verification of folder existence and content

### Refinement Process
1. Read `ARCHITECTURE.md` to understand project structure
2. Read existing Phase 20 audit documentation (`audit/README.md`)
3. Verified each proposed folder exists
4. Counted files in each folder
5. Split `src/` into individual sub-modules where meaningful

### Final Scope: 22 Logical Audit Units

#### Core Application (12 units)
| # | Folder | Key Content | File Count |
|---|--------|-------------|------------|
| 1 | `src/core/` | Production pipeline, shopify, vision, scraping, image | ~25 modules |
| 2 | `src/` | Root modules: app, celery_app, database, models, etc. | ~10 subdirs |
| 3 | `src/api/` | REST API endpoints | app, core, jobs, v1 |
| 4 | `src/jobs/` | Celery orchestrator, dispatcher, queueing | ~10 modules |
| 5 | `src/graph/` | MCP server, sentry ingestion, sandbox, perf profiler | 40+ files |
| 6 | `src/memory/` | Memory manager, event log, task manager | ~6 modules |
| 7 | `src/auth/` | OAuth, login, email verification | ~4 modules |
| 8 | `src/billing/` | Stripe checkout, subscriptions, webhooks | ~5 modules |
| 9 | `src/integrations/` | Perplexity client | 1 file |
| 10 | `universal_vendor_scraper/` | JS scrapers, strategies, vendors | 3 subdirs |
| 11 | `frontend/` | Next.js/React, components, features, lib, shell, state | ~7 subdirs |
| 12 | `seo/` | SEO generator, prompts, validator | 6 files |

#### Configuration & Data (3 units)
| # | Folder | Content |
|---|--------|---------|
| 13 | `config/` | YAML vendor/image/quality rules |
| 14 | `data/` | Logs, CSV exports, vision cache |
| 15 | `utils/` | shopify_utils, pentart_db |

#### Testing (1 unit)
| # | Folder | Content |
|---|--------|---------|
| 16 | `tests/` | unit(50), integration(13), e2e(3), graph(17), daemons(2), planning |

#### Documentation & Operations (5 units)
| # | Folder | Content |
|---|--------|---------|
| 17 | `docs/` | Guides, phase-reports, implementation |
| 18 | `ops/` | Governance, scripts, hooks |
| 19 | `scripts/` | Deployment, debug, checkpoints |
| 20 | `reports/` | Phase reports |
| 21 | `migrations/` | Alembic DB migrations |

#### Agent Frameworks (1 logical unit)
| # | Folder | Content |
|---|--------|---------|
| 22 | `.agents/`, `.claude/`, `.codex/`, `.gemini/`, `.letta/` | Skills, agents, hooks, settings |

---

## Key Decisions

### Decision 1: Scope Granularity
**Choice:** Split `src/` into individual sub-modules  
**Rationale:** Each sub-module has distinct purpose (graph, memory, auth, billing) and should be audited separately for precise blast-radius and cross-domain analysis.

### Decision 2: Tests as One Unit
**Choice:** Keep `tests/` as single logical unit  
**Rationale:** All test subdirectories share ownership patterns and testing conventions. No cross-domain coupling concerns.

### Decision 3: Agent Frameworks Combined
**Choice:** Treat 5 agent framework directories as 1 logical unit  
**Rationale:** They share skills, agents, hooks, and settings patterns. Auditing as one provides coherent surface coverage.

### Decision 4: Exclusions
**Excluded Folders:**
| Folder | Reason |
|--------|--------|
| `Vektal/` | 1 markdown file only |
| `web/` | 4 legacy HTML/JS files |
| `nginx/` | 1 config file |
| `instance/` | 1 test db |
| `archive/` | Historical reference only |
| `seo/images/` | Image files only |
| `secrets/` | No code, secret files only |
| `skills/`, `solutionsos/` | Low code volume |
| `.planning/` | Already audited in Phase 20 |

---

## Audit Parameters

### Depth: Deep Analysis
- Full dependency graphs
- Comprehensive cross-domain coupling maps
- Complete blast-radius analysis

### Surfaces: All 8 Per Unit
1. **ownership** - git blame, file headers, maintainer patterns
2. **blast-radius** - what breaks if changed (imports, function calls)
3. **import-chain** - dependency tree
4. **data-access** - DB models, query patterns
5. **api-surface** - REST endpoints
6. **async-surface** - Celery tasks, queue consumers
7. **config-surface** - env vars, secrets, YAML
8. **cross-domain** - coupling to other subsystems

### Output Format
```
audit/
├── src-core/
│   ├── ownership.json
│   ├── blast-radius.json
│   ├── import-chain.json
│   ├── data-access.json
│   ├── api-surface.json
│   ├── async-surface.json
│   ├── config-surface.json
│   └── cross-domain.json
├── src/
│   └── [8 surfaces]
... (22 units total)
```

---

## Previous Audit Status

- **Original Phase 20 goal:** 813 folders
- **Achieved:** 48 folders (6% coverage)
- **Problem:** Incomplete coverage, inconsistent surface coverage

### This Amendment
- **New goal:** 22 logical units with complete 8-surface coverage
- **Coverage:** All meaningful code directories
- **Output:** 22 units × 8 surfaces = 176 JSON files

---

## Notes

- User confirmed scope via multiple verification rounds
- User insisted on verifying folder contents before confirming
- Frontend was initially missed, then added
- src/graph/, src/memory/, src/auth/, src/billing/ were discovered during verification and added
