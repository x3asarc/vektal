# Governance Role Definitions

Canonical role definitions for Compound Engineering OS.

If any role text conflicts with other files, this directory is the source of truth.

## Roles
1. `phase-manager.md`
2. `builder.md`
3. `reviewer.md`
4. `structure-guardian.md`
5. `integrity-warden.md`
6. `context-curator.md`

## Source Links
1. Policy blueprint: `solutionsos/compound-engineering-os-policy.md`
2. Governance baseline: `AGENTS.md`
3. Structure contract: `ops/STRUCTURE_SPEC.md`

## Usage
1. Compound execution workflows must read all role files before gate orchestration.
2. Gate evidence in `reports/<phase>/<task>/` should align to the role that owns each gate.
3. Role changes must update `AGENTS.md` and the policy references in the same change.
