# Learnings

Triage rule: every finding is Apply now / Capture here / Dismiss (with reason).
Promotion rule: any learning that changes behaviour 2+ times → extract to a rule in AGENTS.md.
Review cadence: consolidate when entries exceed 30.

## Format
`YYYY-MM-DD | Source | Learning | Status`

---

## Entries

### 2026-02-12 | 07.1-governance-baseline-dry-run
**Learning:** Report schema must be bootstrapped from templates before first task closes.
Without template enforcement, required fields drift and block gate closure.
**Applied:** Four report templates standardised in `reports/templates/`. Strict N/A policy added
to AGENTS.md gate policy. Anti-stubborn rule added: two failed closures → scope reset.
**Status:** Promoted → AGENTS.md gate policy rule #4.

### 2026-02-12 | Phase 6 UAT (Celery)
**Learning:** Celery tasks running inside Flask context fail silently without an app-context wrapper.
Race condition between cancel and start requires row-level locking.
**Applied:** App-context wrapper added to all Celery tasks. Row locks added to cancel path.
Duplicate active-ingest returns deterministic 409.
**Status:** Applied.

### 2026-02-16 | Phase 13.1 execution
**Learning:** Enrichment pipeline tests that reference Tier semantics must distinguish
Tier 1 (read-safe) from Tier 2 (mutation path). Mixing them causes fixture drift on every
semantic-firewall change.
**Applied:** `test_chat_single_sku_workflow.py` refactored to run mutation assertions under Tier 2;
Tier 1 write-block behavior isolated to `test_chat_tier_runtime_contract.py`.
**Status:** Applied. Watch for recurrence in Phase 14 when adding new tier routing rules.

### 2026-02-16 | Session workflow observation
**Learning:** When a session ends without updating STATE.md and MASTER_MAP.md, the next session
wastes 10–15 minutes re-orienting. The cost of the closing ritual is ~3 minutes.
**Applied:** Session end ritual codified in GEMINI.md.
**Status:** Applied — monitor compliance across sessions.

### 2026-02-16 | Phase 13.1 test patterns
**Learning:** Contract tests that import from `src.assistant.governance` need the full Flask
app context via `tests/api/conftest.py`. Without it, SQLAlchemy sessions are uninitialised.
**Applied:** All governance contract tests inherit from `api` conftest scope.
**Status:** Applied.

---

## Promotion Candidates (hit count ≥ 2 = promote to AGENTS.md)

| Learning | Hit count | Action |
|---|---|---|
| Tier semantics isolation in tests | 1 | Watch |
| App-context wrapper for Celery | 1 | Watch |
| State file update at session end | 1 | Watch |

### 2026-02-20 | test-test-01
**Learning:** Execution failed - Add sentry-sdk to requirements.txt
**Root cause:** missing_dependency:sentry-sdk
**Status:** First occurrence (watch for pattern)
