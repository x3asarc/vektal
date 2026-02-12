# MASTER_MAP

Last batch update: 2026-02-12
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
|   |   `-- 07.1-governance-baseline-dry-run/
|   |-- meta/
|   `-- templates/
|-- ops/
|   `-- STRUCTURE_SPEC.md
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
1. Phase 7:
   - `.planning/phases/07-frontend-framework-setup/07-02-PLAN.md`
   - `.planning/phases/07-frontend-framework-setup/07-03-PLAN.md`
   - `.planning/phases/07-frontend-framework-setup/07.1-governance-baseline/PLAN.md`

## Governance Links
1. Policy source: `solutionsos/compound-engineering-os-policy.md`
2. Governance baseline: `AGENTS.md`
3. Standards: `STANDARDS.md`
4. Structure spec: `ops/STRUCTURE_SPEC.md`
5. Canonical roadmap: `.planning/ROADMAP.md`
6. Canonical state: `.planning/STATE.md`

## Journey Synthesis Links
1. Template: `reports/meta/journey-synthesis-template.md`
2. Next required synthesis: end of current 3-phase window.
