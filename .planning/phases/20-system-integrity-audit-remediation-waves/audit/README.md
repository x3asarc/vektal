# Phase 20 Audit Architecture

> Phase 20 amendment navigation and architecture notes for the completed audit.  
> **Amended scope:** 22 logical units across 8 critical surfaces = 176 JSON files.  
> **Purpose:** Enable Agent SDK and operators to navigate the completed audit output accurately.

---

## What This Is

Phase 20 ended with a completed audit across 22 logical units. The canonical machine-readable audit payload lives in the repository-root `audit/` directory.

This phase-local folder exists to hold the planning-side navigation artifacts for that work, especially:

- `INDEX.md` — human-readable unit coverage index
- `SURFACE_REGISTRY.json` — machine-readable coverage registry
- `README.md` — architecture and interpretation guide

Each audited unit is represented across 8 surfaces:

1. **Ownership** - Who owns/maintains each file
2. **Blast Radius** - Impact analysis: what breaks if you change X
3. **Import Chain** - Dependency tree: what imports what
4. **Data Access** - Database models and query patterns
5. **API Surface** - REST endpoints and handlers
6. **Async Surface** - Celery tasks and queue consumers
7. **Config Surface** - Environment variables and secrets
8. **Cross-Domain** - Cross-subsystem coupling

---

## For Agent SDK

Agents use this audit to:
1. Find who owns a file → `ownership.json`
2. Understand impact before changes → `blast-radius.json`
3. Trace dependencies → `import-chain.json`
4. Find related functionality → cross-reference surfaces

---

## Surface Definitions

### ownership
Who owns this code? (git blame, file headers, pattern matching)

### blast-radius
What breaks if I change this? (import chains, function calls)

### import-chain
What does this file depend on?

### data-access
What database operations does this perform?

### api-surface
What API endpoints does this define?

### async-surface
What background tasks does this trigger?

### config-surface
What configuration does this use?

### cross-domain
How does this couple to other subsystems?

---

## Scope Notes

- **Original Phase 20 attempt:** 48 folders captured against a much larger 813-folder goal.
- **Phase 20 amendment:** normalized the audit into 22 logical units with full 8-surface coverage.
- **Canonical closure state:** 22/22 units complete, 176/176 surface JSON files present in `audit/`.
- **Naming note:** some historical artifacts use `universal_vendor_scraper`; the canonical final audit unit is `universal-vendor-scraper`.

## Files

| File | Purpose |
|------|---------|
| [INDEX.md](./INDEX.md) | Master folder list with coverage |
| [README.md](./README.md) | This file - surface explanations |
| [SURFACE_REGISTRY.json](./SURFACE_REGISTRY.json) | Machine-readable navigation |
