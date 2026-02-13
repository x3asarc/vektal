# Phase 6 Post-UAT Worktree Inventory

status: snapshot
captured_at: 2026-02-10
captured_from: `git status --short`
related_commit: `c6c7dcc` (Phase 6 closure checkpoint)

## Why this file exists

After Phase 6 closure, the repository still contains a large set of unrelated local changes.  
This inventory is a reminder/reference so we can triage and commit intentionally during Phase 7+.

## Summary

- Tracked modified files (not in `c6c7dcc`): `22`
- Untracked paths: `132`
- Largest untracked groups:
  - `.planning`: 53
  - `src`: 34
  - `docs`: 15

## Tracked Modified Files (22)

### Planning / docs
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/phases/05-backend-api-design/05-04-01-SUMMARY.md`

### Runtime / infra
- `Dockerfile.backend`
- `docker-compose.yml`
- `requirements.txt`

### DB / migrations
- `migrations/versions/e6eec7532bd6_initial_schema_users_stores_vendors_.py`

### Backend app/API
- `src/app.py`
- `src/database.py`
- `src/api/app.py`
- `src/api/core/rate_limit.py`
- `src/api/core/versioning.py`
- `src/api/jobs/events.py`
- `src/api/jobs/schemas.py`
- `src/api/v1/jobs/schemas.py`
- `src/api/v1/vendors/routes.py`
- `src/api/v1/versioning/routes.py`
- `src/models/__init__.py`
- `src/models/job.py`

### Tests
- `tests/api/conftest.py`
- `tests/api/test_endpoints.py`
- `tests/api/test_versioning.py`

## Untracked Paths (Grouped)

### Planning artifacts (`.planning/*`)

Large backlog of plan/summaries across phases 02, 02.1, 03, 04, 05, 06, and 14.
Examples:
- `.planning/phases/02-docker-infrastructure-foundation/*`
- `.planning/phases/03-database-migration-sqlite-to-postgresql/*`
- `.planning/phases/04-authentication-user-management/*`
- `.planning/phases/05-backend-api-design/*`
- `.planning/phases/06-job-processing-infrastructure-celery/*` (many plan/summary/context files)
- `.planning/phases/14-continuous-optimization-learning/`

### Source code (`src/*`)

Many untracked modules/directories exist beyond the Phase 6 checkpoint.
Examples:
- `src/auth/`, `src/billing/`, `src/config/`, `src/tasks/`, `src/utils/`
- `src/core/*` (many modules)
- `src/jobs/{__init__.py,dispatcher.py,finalizer.py,metrics.py,queueing.py}`
- `src/models/{audit_checkpoint.py,ingest_chunk.py,oauth_attempt.py}`

### Documentation/content

- `docs/*` (15 untracked paths including implementation/setup/report docs)
- `archive/*` additions
- `results/`, `data/`, `logs/`, `seo/`, `utils/`, `web/`

### Misc / tooling

- `.claude/`, `awesome-claude-code/`, `codexclaude/`
- `quickcleanup/`, `side-project/`, `universal_vendor_scraper/`
- `frontend/package-lock.json`
- Script files (`*.bat`, `install-scoop.ps1`)
- Suspicious loose files: `=3.1.0`, `=4.0.0`, `=42.0.0`

## Suggested triage order

1. Decide what belongs to current product scope vs archived experiments.
2. Split by theme into small commits:
   - planning/docs
   - backend runtime/API
   - tests
   - migrations/models
3. Handle suspicious loose files (`=3.1.0`, `=4.0.0`, `=42.0.0`) explicitly.
4. Keep using scoped commits to avoid mixing Phase 7 work with historical leftovers.

## Regenerate snapshot

Run:

```powershell
git status --short
```
