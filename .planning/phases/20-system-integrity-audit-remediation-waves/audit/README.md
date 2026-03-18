# Phase 20 Audit Architecture

> Machine-generated audit of 48 codebase folders across 8 critical surfaces.  
> **Goal was 813 folders; 48 achieved (6% coverage).**  
> **Purpose:** Enable Agent SDK to understand codebase structure for intelligent routing.

---

## What This Is

Phase 20 produced a complete codebase audit across all meaningful folders. Each folder has 8 JSON files documenting:

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

## Files

| File | Purpose |
|------|---------|
| [INDEX.md](./INDEX.md) | Master folder list with coverage |
| [README.md](./README.md) | This file - surface explanations |
| [SURFACE_REGISTRY.json](./SURFACE_REGISTRY.json) | Machine-readable navigation |
