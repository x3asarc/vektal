# PLAN: 07.1 Governance Baseline Dry-Run

## Objective
Implement and validate the governance baseline artifacts defined in `solutionsos/compound-engineering-os-policy.md` without product-code changes.

## Scope In
1. Create governance files (`AGENTS.md`, `STANDARDS.md`, `.rules`, `ops/STRUCTURE_SPEC.md`, `docs/MASTER_MAP.md`, `FAILURE_JOURNEY.md`).
2. Create report templates and one dry-run evidence set.
3. Add governance sections into canonical planning files (`.planning/ROADMAP.md`, `.planning/STATE.md`).

## Scope Out
1. Product feature implementation for frontend Phase 7 plans (`07-02`, `07-03`).
2. CI/CD and GitHub delegation wiring.
3. Runtime scanner automation scripts.

## Atomic Checklist
1. Governance artifact files created.
2. Dry-run task report folder created with exact four reports.
3. Blind-review ordering fields added in review report schema.
4. Structure protected-path policy encoded.
5. Integrity policy and license constraints encoded.

## Risks
1. Existing planning conventions may conflict with new task-path conventions.
2. Manual report population may drift if templates are not enforced.
3. Blind-review ordering proof is dependent on commit discipline.

## Definition of Done
1. Task folder has exactly four reports and no empty required fields.
2. All four reports show `GREEN` or documented `RED` with action items.
3. `.planning/ROADMAP.md` and `.planning/STATE.md` include governance baseline sections.
4. `docs/MASTER_MAP.md` references all new governance artifacts.

## Gate Evidence Links
1. `reports/07/07.1-governance-baseline-dry-run/self-check.md`
2. `reports/07/07.1-governance-baseline-dry-run/review.md`
3. `reports/07/07.1-governance-baseline-dry-run/structure-audit.md`
4. `reports/07/07.1-governance-baseline-dry-run/integrity-audit.md`

