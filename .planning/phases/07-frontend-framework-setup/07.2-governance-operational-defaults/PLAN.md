# PLAN: 07.2 Governance Operational Defaults

## Objective
Operationalize approved governance defaults from the `07.1` baseline so policy, trackers, and closure evidence are consistent and executable.

## Scope In
1. Record approved defaults (SLO handling, pinning scope, license scope, dev-bypass policy) in canonical governance policy.
2. Register `07.2` in `.planning/ROADMAP.md` governance task board.
3. Sync `.planning/STATE.md` with `07.2` completion and explicit evidence links.
4. Publish a complete four-report governance evidence set for `07.2`.

## Scope Out
1. Product-code changes in backend/frontend features.
2. CI/CD workflow automation beyond current policy text.
3. New package/dependency introductions.

## Atomic Checklist
1. Governance defaults are codified in `solutionsos/compound-engineering-os-policy.md`.
2. `ROADMAP.md` includes `07.2` task tracking and status.
3. `STATE.md` includes `07.2` status and report evidence references.
4. Report set exists with exact required files and no empty required fields.
5. Governance validator passes for `07.2`.

## Risks
1. Tracker drift if status is updated in policy but not mirrored in `ROADMAP.md`/`STATE.md`.
2. Report schema drift if evidence fields are omitted or renamed.
3. Ambiguity between SLO tracking and hard merge-gate semantics.

## Definition of Done
1. `reports/07/07.2-governance-operational-defaults/` contains exactly:
   - `self-check.md`
   - `review.md`
   - `structure-audit.md`
   - `integrity-audit.md`
2. All four reports are binary status (`GREEN`/`RED`) and satisfy required fields.
3. `.planning/ROADMAP.md` and `.planning/STATE.md` reflect `07.2` completion.
4. `python scripts/governance/validate_governance.py --phase 07 --task 07.2-governance-operational-defaults --mode full-loop` passes.

## Gate Evidence Links
1. `reports/07/07.2-governance-operational-defaults/self-check.md`
2. `reports/07/07.2-governance-operational-defaults/review.md`
3. `reports/07/07.2-governance-operational-defaults/structure-audit.md`
4. `reports/07/07.2-governance-operational-defaults/integrity-audit.md`
