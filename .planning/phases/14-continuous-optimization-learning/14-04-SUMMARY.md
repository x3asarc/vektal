# Phase 14 Plan 04 - Planning Docs as Central Nodes

## Summary

Implemented auto-linking and natural reference detection to make planning documents central hubs in the codebase knowledge graph. Every code change can now be traced back to the "why" (the planning doc) via `IMPLEMENTS` edges from commits and `REFERENCES` edges from comments.

## What Was Built

### Commit Message Parser (`src/graph/commit_parser.py`)
- `parse_commit_message()`: Extracts phase, plan, and requirement references from git commit messages.
- Supports patterns: `feat(13.2-03)`, `docs(phase-12)`, `refactor(CHAT-05)`, and `feat(14-01): implement GRAPH-01`.
- `get_commits_for_files()`: Uses `git log --follow` to extract history for specific files.

### Planning Linker (`src/graph/planning_linker.py`)
- `link_commit_to_plan()`: Automatically creates `ImplementsEdge` for files changed in a commit referencing a plan.
- `detect_natural_references()`: Scans file content for comments like `# Related to Phase 13.2-01` or `# See .planning/phases/...`.
- `resolve_plan_path()`: Intelligent path resolution that handles subphases (13.1, 13.2) and various directory naming conventions.
- Deduplication logic ensures same document isn't linked multiple times on the same line.

### Integration Tests (`tests/integration/test_planning_linker.py`)
- Verified commit extraction across multiple formats.
- Verified auto-linking of changed files.
- Verified natural reference detection in comments and docstrings.
- Verified subphase path resolution (13.2-03 != 13-03).

## Verification

- `python -m pytest tests/integration/test_planning_linker.py -v` -> `5 passed`
- `python -m pytest tests/core/ -v` -> `26 passed`
- Commit parser verified with `feat(13.2-03)` -> `Phase: 13.2, Plan: 03`
- Planning linker verified to create compliant `ImplementsEdge` with `from_entity_id`/`to_entity_id`.

## Files Created

- `src/graph/commit_parser.py`
- `src/graph/planning_linker.py`
- `tests/integration/test_planning_linker.py`

**Phase:** 14-04 | **Status:** Complete | **Tests:** 31 passed (core + integration)
