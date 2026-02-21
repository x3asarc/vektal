# Session Primer Template

Copy this file to `.gemini/SESSION_PRIMER_<phase>-<task>.md` and fill in before each session.
Paste the filled primer as the first message in Gemini CLI.

---

```markdown
# Session Primer: Phase <X.Y> Task <N>

## One-sentence goal
<What does done look like in a single sentence?>

## Current state (from STATE.md)
Phase: <X.Y> of 15
Last completed: <task and what it did>
Gate board: <GREEN/RED status>

## Files to read FIRST, in this order
1. `.planning/phases/<phase>/<task>/PLAN.md` — task specification
2. <file 1> — <why it matters>
3. <file 2> — <why it matters>
(Keep this list ≤5. If you need more than 5 to start, scope is too broad.)

## What done looks like (acceptance criteria)
- [ ] <criterion 1>
- [ ] <criterion 2>
- [ ] Tests pass: `python -m pytest tests/<path> -x --tb=short -q`
- [ ] LOC on modified files all ≤400 (warn), none ≥800 (block)
- [ ] Four gate reports published at `reports/<phase>/<task>/`

## Known failure modes — do not repeat
<Copy relevant entries from FAILURE_JOURNEY.md and learnings.md here>

## Out of scope (do not touch)
- <file or system that must not change>
- <file or system that must not change>

## Task mode: ASYNC / SYNCHRONOUS
<Pick one. See GEMINI.md Task Mode table.>
```

---

## Filled Example — Phase 13.2 Task 01 (Oracle Framework Reuse)

```markdown
# Session Primer: Phase 13.2 Task 01 — Oracle Adapter Protocol

## One-sentence goal
Extract a shared Protocol interface from the existing verification oracle so that
resolution, enrichment, and assistant governance all consume a single typed contract.

## Current state (from STATE.md)
Phase: 13.2 of 15 (Oracle Framework Reuse)
Last completed: Phase 13.1-04 — enrichment quality gates and lineage audit export (GREEN)
Gate board: 13.1 fully GREEN; 13.2 pending discuss + plan + execute

## Files to read FIRST, in this order
1. `.planning/phases/13.2-oracle-framework-reuse/13.2-01-PLAN.md` — task specification
2. `src/assistant/governance/verification_oracle.py` — existing oracle implementation
3. `src/resolution/contracts.py` — existing resolution contract types (PolicyDecision, RuleContext)
4. `tests/api/test_verification_oracle_contract.py` — existing oracle test surface
5. `tests/api/test_oracle_signal_join_contract.py` — signal join contract to keep green

## What done looks like
- [ ] `src/resolution/oracle_protocol.py` (or similar) defines a typed Protocol class
- [ ] `src/assistant/governance/verification_oracle.py` implements that protocol
- [ ] At least one resolution module imports the protocol instead of the concrete class
- [ ] All existing oracle tests still pass (zero regressions)
- [ ] LOC on new file ≤400; no existing file pushed above 500
- [ ] Four gate reports at `reports/13.2/13.2-01/`

## Known failure modes — do not repeat
- Do not create a new module if `src/resolution/contracts.py` can absorb the protocol
  (KISS — check absorption first)
- Do not bypass the kill-switch or field-policy contracts while refactoring oracle paths
- Tier semantics tests must stay isolated: Tier 1 assertions in tier-runtime contract,
  Tier 2 mutation assertions in single-sku-workflow (learned 2026-02-16)

## Out of scope
- `src/assistant/instrumentation/` — oracle signals are a separate concern
- `src/api/v1/ops/routes.py` — no new endpoints in this task
- `FAILURE_JOURNEY.md` and `docs/MASTER_MAP.md` — update at session END, not during

## Task mode: SYNCHRONOUS
Oracle interface changes affect assistant, resolution, and enrichment simultaneously.
Stay in loop. Do not run to completion without check-in after file theory confirmed.
```
