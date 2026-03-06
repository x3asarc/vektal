# Gemini CLI — Vektal (Shopify Multi-Supplier Platform)

> You are a learning system. Read this completely before touching anything.

## What This Is

Multi-tenant SaaS platform (Vektal) automating Shopify product management for craft/hobby stores (8+ vendors,
4,000+ SKUs). Production: Bastelschachtel.at. **Phase 16 - Agent Context OS - COMPLETE.**
Next: Future production refinement (Priority 2-3).

**Read first on every session:**
- `docs/AGENT_START_HERE.md` — Primary onboarding entrypoint
- `.planning/STATE.md` — Current phase, gate status, last completed work
- `.planning/ROADMAP.md` — Phase definitions and success criteria
- Active task: `.planning/phases/<phase>/<task>/PLAN.md`

---

## Safety Protocols (Production Protection)

Vektal employs a multi-layered safety architecture to prevent accidental data loss or corruption:

1.  **Tiered Assistant Architecture:**
    *   **Tier 1 (Read-Safe):** Only allowed to read files and query the graph. Zero mutation capability.
    *   **Tier 2 (Dry-Run Gated):** Performs changes in a dry-run mode first. Requires explicit human approval via the `verification_oracle` before any application to production/master.
    *   **Tier 3 (Delegated Workers):** Specialized agents for high-volume tasks. depth ≤2, fan-out ≤5, budget 20 steps / 120s.
2.  **Kill-Switch (`kill_switch.py`):** A global circuit breaker that gates every Tier 2/3 mutation. If the system detects anomalous behavior, the kill-switch engages automatically.
3.  **Field Policy (`field_policy.py`):** Hard-blocks mutations to immutable fields (e.g., historical audit logs). Price and inventory threshold breaches trigger mandatory HITL (Human-In-The-Loop) review.
4.  **Sandbox Execution:** All code execution and script testing occurs within a hardened Docker-based sandbox with 6-gate validation.
5.  **Context OS Gate:** `python scripts/governance/context_os_gate.py` ensures all changes are backed by canonical lifecycle events and verified via the graph before completion.

---

## Before Writing Anything

1. State which files you will touch — trace the call chain, do not guess
2. State the test command you will run
3. Then implement

**Backend call chain:** `src/api/v1/` → `src/tasks/` → `src/resolution/` + `src/jobs/` → `src/core/`
**Assistant chain:** `src/api/v1/chat/` → `src/tasks/assistant_runtime.py` → `src/assistant/`

---

## Verification Loop (self-sufficient — never break to ask)

```
1. Make change
2. python -m pytest tests/ -x --tb=short -q     # stop on first fail
3. RED → read error, fix in-place, re-run. Do not ask.
4. GREEN → count LOC on every modified file
5. LOC >500 → evaluate split before continuing
   LOC >800 → hard stop, open architecture note, ask
6. Report: files changed · test result · LOC counts
```

Frontend (unit + type):
```
npm --prefix frontend run test -- <ComponentName>
npm --prefix frontend run typecheck
```

Frontend (browser E2E — Playwright):
```
npm --prefix frontend run test:e2e                   # headless, all tests
npm --prefix frontend run test:e2e:headed            # visible browser (dev)
bash scripts/harness/ui/run_e2e.sh --test <pattern>  # single test
python scripts/governance/check_harness_slas.py       # SLA gap report
```

Risk / CI gate:
```
python scripts/governance/risk_tier_gate.py --changed-files <file1> <file2>
python scripts/governance/risk_tier_gate.py --from-git-diff
```

---

## KISS Policy

Target 150–400 LOC per file. Before creating a new module ask: "Can an existing file absorb this?"
Default is yes. New module needs explicit justification.

---

## Governance Gates (every task, no exceptions)

Four reports at `reports/<phase>/<task>/`:
1. `self-check.md` — Builder self-review
2. `review.md` — Two-pass (`pass_1_timestamp` must predate `plan_context_opened_at`)
3. `structure-audit.md` — StructureGuardian placement/naming
4. `integrity-audit.md` — IntegrityWarden dependencies/licenses/secrets

Outcome: `GREEN` or `RED`. Block on Critical/High. Block on Medium for Security/Dependency.

Roles: `ops/governance/roles/` · Severity: `STANDARDS.md` · Structure: `ops/STRUCTURE_SPEC.md`

---

## Stack

**Backend:** Flask · Flask-OpenAPI3 · PostgreSQL (psycopg3) · SQLAlchemy · Celery + Redis
**Frontend:** Next.js 14 · TypeScript · App Router → `frontend/src/features/<feature>/`
**Infra:** Docker Compose (nginx, backend, celery_worker, celery_scraper, flower, db, redis)
**AI:** OpenRouter/Gemini Flash · Neo4j/Graphiti · sentence-transformers · Vision AI (cached)

**Entry points:**
- API: `src/api/app.py` → blueprints at `src/api/v1/`
- Celery tasks: `src/tasks/` (queues: `assistant.t1` / `.t2` / `.t3` / `scrape` / `ingest`)
- Assistant tiers: `src/assistant/runtime_tier1.py` / `runtime_tier2.py` / `runtime_tier3.py`
- Governance: `src/assistant/governance/` (kill_switch · field_policy · verification_oracle)
- Models: `src/models/` — **never add columns without an Alembic migration**

API contracts: RFC 7807 errors · cursor pagination · SSE at `/<job_id>/stream`
Auth: Flask-Login + Redis sessions · rate limits 100/500/2000 req/day by tier

---

## Knowledge Graph — Primary Context Source

**Neo4j/Graphiti knowledge graph is the DEFAULT for ALL context operations.**

Every code search, file exploration, import tracing, and context gathering MUST use the graph first.
This is not optional — it's the root configuration for how this system understands the codebase.

### Configuration (Required)

Environment variables in `.env`:
```
GRAPH_ORACLE_ENABLED=true
NEO4J_URI=neo4j+s://5953bf18.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<your-password>
```

### What's in the Graph

- **2,784 nodes**: File, Class, Function, PlanningDoc, Tool, Convention, Entity, Community
- **6,254 relationships**: IMPORTS, CALLS, DEFINES_CLASS, DEFINES_FUNCTION, CONTAINS, RELATES_TO
- **Full codebase**: All Python/TypeScript files, their relationships, and semantic embeddings
- **Live data**: Synced with current codebase state

### How to Use It

```python
from src.graph.query_interface import query_graph

# Find what imports a file
result = query_graph("imported_by", {"file_path": "src/core/embeddings.py"})

# Find what a file imports
result = query_graph("imports", {"file_path": "src/core/embeddings.py"})

# Trace impact radius (what depends on this)
result = query_graph("impact_radius", {"file_path": "src/core/embeddings.py"})

# Find similar files (semantic search)
result = query_graph("similar_files", {"file_path": "path/to/file.py", "limit": 5, "threshold": 0.7})

# Find function callers
result = query_graph("function_callers", {"function_name": "my_function"})

# Find function callees
result = query_graph("function_callees", {"function_name": "my_function"})
```

### Integration Points

**Always use graph queries for:**
- Dead code investigation — trace where code SHOULD be called, why it's not
- Import analysis — understand dependency chains
- Code exploration — find related files and patterns
- Context retrieval — gather relevant code for assistant responses
- Impact analysis — understand what breaks if you change something
- Duplication detection — find similar code patterns across codebase

---

## Branch Workflow (always — no direct commits to master)

```
git checkout -b <type>/<short-description>   # start every piece of work on a branch
# ... make changes, run tests ...
git add <files>
git commit -m "type: description"
git push -u origin <branch-name>             # opens PR link on GitHub
# CI runs automatically → merge when green → delete branch
git checkout master && git pull              # sync master after merge
git branch -d <branch-name>                 # clean up local branch
```

**Branch naming:**
- `feat/` — new feature or phase work
- `fix/` — bug fix
- `phase/` — full GSD phase (e.g. `phase/16-agent-context-os`)
- `chore/` — tooling, config, docs

**Rule:** `master` = always deployable. Never commit half-finished work directly to master.

---

## Anti-Patterns

- No `cd` — use full paths from project root
- No `python run` — use `python -m pytest`
- No `src/models/` changes without a migration
- No task closure without all four gate reports
- No new top-level files/dirs without asking
- No guessing at state — read `STATE.md` and `AGENT_START_HERE.md` first
- No direct commits to `master` — always use a branch + PR

**Protected paths** (never auto-move): `.planning/` · `.rules` · `AGENTS.md`

---

## Pointers

`AGENTS.md` · `STANDARDS.md` · `ops/STRUCTURE_SPEC.md` · `ops/governance/roles/README.md`
`FAILURE_JOURNEY.md` · `LEARNINGS.md` · `docs/MASTER_MAP.md` · `docs/AGENT_START_HERE.md`

**Code Factory CI layer:**
`risk-policy.json` · `scripts/governance/risk_tier_gate.py` · `scripts/governance/sha_gate.py`
`scripts/governance/check_harness_slas.py` · `HARNESS_GAPS.md`
`playwright.config.ts` · `tests/e2e/` · `scripts/harness/ui/`
`.github/workflows/` → `risk-policy-gate` · `ci-backend` · `review-agent-rerun` · `auto-remediate` · `resolve-bot-threads`

**Session primer template:** `.gemini/SESSION_PRIMER_TEMPLATE.md`
