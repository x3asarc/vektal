# MASTER_MAP

Last batch update: 2026-02-16
Owner: ContextCurator

## TOC
1. Project Map (depth 3)
2. Module Index
3. Data and Logic Flow
4. Active Plans
5. Governance Links
6. Journey Synthesis Links

## Project Map (Depth 3)
```text
.
|-- AGENTS.md
|-- STANDARDS.md
|-- .rules
|-- FAILURE_JOURNEY.md
|-- solutionsos/
|   `-- compound-engineering-os-policy.md
|-- .planning/
|   |-- ROADMAP.md
|   |-- STATE.md
|   |-- PROJECT.md
|   |-- REQUIREMENTS.md
|   |-- phases/
|   |   |-- 07-frontend-framework-setup/
|   |   `-- ...
|   `-- archive/
|-- reports/
|   |-- 07/
|   |   |-- 07.1-governance-baseline-dry-run/
|   |   `-- 07.2-governance-operational-defaults/
|   |-- meta/
|   `-- templates/
|-- ops/
|   |-- STRUCTURE_SPEC.md
|   `-- governance/
|       `-- roles/
|-- docs/
|   |-- MASTER_MAP.md
|   `-- INDEX.md
|-- src/
|   `-- ...
|-- tests/
|   `-- ...
|-- frontend/
|   `-- ...
|-- scripts/
|   `-- ...
`-- config/
    `-- ...
```

## Module Index
1. Governance:
   - `AGENTS.md`: governance constitution and role boundaries.
   - `STANDARDS.md`: review severity model and two-pass review protocol.
   - `.rules`: machine-checkable policy lines.
   - `ops/governance/roles/README.md`: canonical role definitions and links.
2. Planning:
   - `.planning/ROADMAP.md`: canonical phase state and phase details.
   - `.planning/STATE.md`: live state, blockers, gate snapshots.
   - `.planning/phases/`: phase-level plans, context, and research artifacts.
3. Evidence:
   - `reports/<phase>/<task>/`: four required closure reports.
   - `reports/meta/`: cross-phase synthesis reports.
   - `scripts/governance/validate_governance.py`: task gate validator.
4. Structure and context:
   - `ops/STRUCTURE_SPEC.md`: placement and protected path contract.
   - `docs/MASTER_MAP.md`: this project map and links.
5. Product code:
   - `src/`: backend/core implementation.
   - `frontend/`: Next.js UI implementation.
   - `tests/`: automated verification.

## Data and Logic Flow
1. Requirements and decisions are captured in `.planning`.
2. A task plan is created under `.planning/phases/<phase>/<task>/PLAN.md`.
3. Builder executes and publishes task evidence in `reports/<phase>/<task>/`.
4. Reviewer performs blind-first then context-fit two-pass audit.
5. StructureGuardian and IntegrityWarden publish final compliance reports.
6. PhaseManager updates `.planning/STATE.md` and `.planning/ROADMAP.md`.
7. ContextCurator updates this map at daily batch and phase close.

## Active Plans
1. Phase 13 canonical artifacts:
   - `.planning/phases/13-integration-hardening-deployment/13-PRE-CONTEXT-SCOPE.md`
   - `.planning/phases/13-integration-hardening-deployment/13-CONTEXT.md`
   - `.planning/phases/13-integration-hardening-deployment/13-RESEARCH.md`
   - `.planning/phases/13-integration-hardening-deployment/13-PLANNING-COVERAGE.md`
   - `.planning/phases/13-integration-hardening-deployment/13-01-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-02-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-03-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-04-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-01-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-02-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-03-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-04-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-VERIFICATION.md`
2. Phase 13 governance evidence:
   - `reports/13/13-01/self-check.md`
   - `reports/13/13-01/review.md`
   - `reports/13/13-01/structure-audit.md`
   - `reports/13/13-01/integrity-audit.md`
   - `reports/13/13-02/self-check.md`
   - `reports/13/13-02/review.md`
   - `reports/13/13-02/structure-audit.md`
   - `reports/13/13-02/integrity-audit.md`
   - `reports/13/13-03/self-check.md`
   - `reports/13/13-03/review.md`
   - `reports/13/13-03/structure-audit.md`
   - `reports/13/13-03/integrity-audit.md`
   - `reports/13/13-04/self-check.md`
   - `reports/13/13-04/review.md`
   - `reports/13/13-04/structure-audit.md`
   - `reports/13/13-04/integrity-audit.md`
3. Phase 13.1 closure artifacts:
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-PRE-CONTEXT-SCOPE.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-CONTEXT.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-RESEARCH.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-PLANNING-COVERAGE.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-01-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-02-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-03-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-04-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-01-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-02-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-03-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-04-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-VERIFICATION.md`
4. Canonical trackers:
   - `.planning/ROADMAP.md` (Phase 13.1 marked complete `4/4`)
   - `.planning/STATE.md` (current atomic task: `phase-13.2-pre-context-scope-gate`)
5. Governance closure evidence:
   - `reports/07/07.2-governance-operational-defaults/self-check.md`
   - `reports/07/07.2-governance-operational-defaults/review.md`
   - `reports/07/07.2-governance-operational-defaults/structure-audit.md`
   - `reports/07/07.2-governance-operational-defaults/integrity-audit.md`

## Governance Links
1. Policy source: `solutionsos/compound-engineering-os-policy.md`
2. Governance baseline: `AGENTS.md`
3. Standards: `STANDARDS.md`
4. Structure spec: `ops/STRUCTURE_SPEC.md`
5. Canonical roadmap: `.planning/ROADMAP.md`
6. Canonical state: `.planning/STATE.md`
7. Canonical role definitions: `ops/governance/roles/README.md`

## Journey Synthesis Links
1. Template: `reports/meta/journey-synthesis-template.md`
2. Next required synthesis: end of current 3-phase window.
