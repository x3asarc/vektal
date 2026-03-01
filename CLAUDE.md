# Claude Code — Shopify Multi-Supplier Platform

> You are a learning system. Read this completely before touching anything.

## What This Is

Multi-tenant SaaS platform automating Shopify product management for craft/hobby stores (8+ vendors,
4,000+ SKUs). Production: Bastelschachtel.at. **Phase 13.2 of 15. 95/106 plans complete.**
Remaining phases: 13.2 (Oracle Framework Reuse), 14 (Continuous Optimization), 15 (Self-Healing).

**Read first on every session:**
- `.planning/STATE.md` — current phase, gate status, last completed work
- `.planning/ROADMAP.md` — phase definitions and success criteria
- Active task: `.planning/phases/<phase>/<task>/PLAN.md`

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
**AI:** OpenRouter/Gemini Flash · sentence-transformers · Vision AI (cached)

**Entry points:**
- API: `src/api/app.py` → blueprints at `src/api/v1/`
- Celery tasks: `src/tasks/` (queues: `assistant.t1` / `.t2` / `.t3` / `scrape` / `ingest`)
- Assistant tiers: `src/assistant/runtime_tier1.py` / `runtime_tier2.py` / `runtime_tier3.py`
- Governance: `src/assistant/governance/` (kill_switch · field_policy · verification_oracle)
- Models: `src/models/` — **never add columns without an Alembic migration**

API contracts: RFC 7807 errors · cursor pagination · SSE at `/<job_id>/stream`
Auth: Flask-Login + Redis sessions · rate limits 100/500/2000 req/day by tier

---

## Assistant Tier Rules (production safety — never bypass)

- **Tier 1:** read-safe only, zero mutations
- **Tier 2:** dry-run first, explicit approval before any apply
- **Tier 3:** delegated workers — depth ≤2, fan-out ≤5, budget 20 steps / 120s
- **Kill-switch** (`kill_switch.py`) gates every Tier 2/3 mutation
- **Field policy** (`field_policy.py`) — immutable fields hard-blocked; price/inventory
  threshold breaches trigger HITL before apply

---

## Task Mode

| Work type | Mode |
|---|---|
| New tests, vendor adapters, KISS audits | Async — run to completion |
| Oracle/verifier interface changes | Synchronous — stay in loop |
| Tier routing, kill-switch, field policy | Synchronous — highest risk |
| Phase 13.2 / 14 / 15 architectural scope | Synchronous |

**Slot Machine Protocol (high-complexity tasks):**
Commit checkpoint → run autonomously 30 min → if wrong direction: `git reset --hard <checkpoint>`,
re-prompt with one new constraint learned from the failure. Log in `FAILURE_JOURNEY.md`.

---

## Session Rituals

**Start:** Read `STATE.md` → read active PLAN.md → state file theory → begin.

**End:**
1. Update `docs/MASTER_MAP.md` if any module changed
2. Update `STATE.md`: what done, what next, open questions
3. Learning loop — for every finding, triage as one of:
   - **Apply now** → make the change
   - **Capture** → add to `LEARNINGS.md` with date + context
   - **Dismiss** → say why, move on

---

## Anti-Patterns

- No `cd` — use full paths from project root
- No `python run` — use `python -m pytest`
- No `src/models/` changes without a migration
- No task closure without all four gate reports
- No new top-level files/dirs without asking
- No guessing at state — read `STATE.md` first

**Protected paths** (never auto-move): `.planning/` · `.rules` · `AGENTS.md`

---

## Pointers

`AGENTS.md` · `STANDARDS.md` · `ops/STRUCTURE_SPEC.md` · `ops/governance/roles/README.md`
`FAILURE_JOURNEY.md` · `LEARNINGS.md` · `docs/MASTER_MAP.md`

**Code Factory CI layer:**
`risk-policy.json` · `scripts/governance/risk_tier_gate.py` · `scripts/governance/sha_gate.py`
`scripts/governance/check_harness_slas.py` · `HARNESS_GAPS.md`
`playwright.config.ts` · `tests/e2e/` · `scripts/harness/ui/`
`.github/workflows/` → `risk-policy-gate` · `ci-backend` · `review-agent-rerun` · `auto-remediate` · `resolve-bot-threads`

**Session primer template:** `.claude/SESSION_PRIMER_TEMPLATE.md`
