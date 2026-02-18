# Repository Structure Specification v1

## Canonical map
1. Planning and lifecycle state:
   - `.planning/ROADMAP.md`
   - `.planning/STATE.md`
   - `.planning/phases/`
   - `.planning/archive/`
2. Governance and standards:
   - `AGENTS.md`
   - `STANDARDS.md`
   - `.rules`
   - `ops/governance/roles/`
   - `solutionsos/`
3. Execution evidence:
   - `reports/<phase>/<task>/`
   - `reports/meta/`
4. Product and runtime code:
   - `src/`
   - `tests/`
   - `frontend/`
   - `config/`
   - `scripts/`
5. Documentation and context:
   - `docs/`
   - `FAILURE_JOURNEY.md`

## Naming rules
1. Use `kebab-case` for new files and directories unless ecosystem convention requires otherwise.
2. Keep task identifiers in file/folder names (`07.1`, `07-02`, etc.) for traceability.
3. Avoid ambiguous names (`temp`, `misc`, `new`).

## File placement rules
1. Task plan files belong under `.planning/phases/<phase>/<task>/PLAN.md`.
2. Task reports belong under `reports/<phase>/<task>/`.
3. Meta synthesis reports belong under `reports/meta/`.
4. Long-term context indexes belong under `docs/`.
5. Governance policy source lives under `solutionsos/`.
6. Canonical role definitions live under `ops/governance/roles/`.

## Protected paths
1. `.planning/`
2. `.rules`
3. `AGENTS.md`

StructureGuardian must not auto-move files in protected paths.

## Auto-move policy
1. Auto-moves are allowed only for non-protected paths.
2. Every move requires a `Moved Files` entry in `structure-audit.md`.
3. Every move requires a one-line rationale.
4. Every move is mirrored into `.planning/STATE.md` under `StructureGuardian Audit Trail`.
