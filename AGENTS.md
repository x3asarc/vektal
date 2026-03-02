# Compound Engineering Governance Baseline v1

## Mission and non-negotiables
1. Deliver every task with binary gate outcomes (`GREEN` or `RED`).
2. Treat `.planning/ROADMAP.md` as canonical lifecycle state.
3. Do not close a task without all required evidence artifacts.
4. Do not bypass gates except PhaseManager emergency protocol.
5. Keep implementation simple and auditable under KISS policy.

## Role authority boundaries
1. `PhaseManager`: owns phase state, gate decisions, and closure in `.planning/ROADMAP.md` and `.planning/STATE.md`.
   - Canonical definition: `ops/governance/roles/phase-manager.md`
2. `Builder`: implements scoped task from plan and publishes `self-check.md`.
   - Canonical definition: `ops/governance/roles/builder.md`
3. `Reviewer`: performs two-pass review and publishes findings; cannot merge or close phase.
   - Canonical definition: `ops/governance/roles/reviewer.md`
4. `StructureGuardian`: audits placement/naming/spec, proposes moves through traceable reports.
   - Canonical definition: `ops/governance/roles/structure-guardian.md`
5. `IntegrityWarden`: verifies dependencies/imports/licenses/secrets and blocks unsafe package changes.
   - Canonical definition: `ops/governance/roles/integrity-warden.md`
6. `ContextCurator`: owns `docs/MASTER_MAP.md` and three-phase journey synthesis.
   - Canonical definition: `ops/governance/roles/context-curator.md`

## Gate policy and blocking rules
1. Block on `Critical` and `High`.
2. Block on `Medium` when category is `Security` or `Dependency`.
3. Require exactly four task reports at `reports/<phase>/<task>/`:
   - `self-check.md`
   - `review.md`
   - `structure-audit.md`
   - `integrity-audit.md`
4. Required report fields cannot be empty; use explicit `N/A` when non-applicable.
5. `review.md` must include blind-review ordering evidence:
   - `pass_1_timestamp`
   - `pass_2_timestamp`
   - `plan_context_opened_at`
   - Pass 1 must predate plan-context access by git evidence.

## Emergency bypass protocol
1. Only PhaseManager may invoke bypass.
2. Bypass expires in 24 hours.
3. Bypass requires rollback owner and rollback plan.
4. Post-mortem must be logged in `.planning/STATE.md` within 48 hours.

## KISS limits
1. No minimum LOC requirement applies to implementation files.
2. Hard threshold: any source file `>500 LOC` is a blocking violation.
3. Any file `>500 LOC` must be refactored into at least two modules before the task/phase can be closed.
4. Verification gates must not fail or pass based on minimum LOC targets.

## Artifact contract
1. Canonical phase state: `.planning/ROADMAP.md`.
2. Current execution state: `.planning/STATE.md`.
3. Standards rubric: `STANDARDS.md`.
4. Structure contract: `ops/STRUCTURE_SPEC.md`.
5. Context map: `docs/MASTER_MAP.md`.
6. Failure memory: `FAILURE_JOURNEY.md`.
7. Task plans: `.planning/phases/<phase>/<task>/PLAN.md`.
8. Task reports: `reports/<phase>/<task>/`.
9. Three-phase synthesis: `reports/meta/journey-synthesis-<phase-range>.md`.
10. Governance blueprint reference: `solutionsos/compound-engineering-os-policy.md`.
11. Canonical role definitions: `ops/governance/roles/README.md`.
