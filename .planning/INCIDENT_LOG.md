# Incident Log

## 2026-02-13 - Accidental gsd-tools commit invocation

- Accidental commit: `704afbe` (`--help`)
- Scope: large `.planning/` docs-only sweep (multi-phase planning artifacts), not intended for commit.
- Cause: `node codexclaude/get-shit-done/bin/gsd-tools.js commit --help` executed by assistant and interpreted as an actual commit action.
- Correction: reverted with a dedicated follow-up commit (this commit) to preserve history and remove unintended changes.
- User direction: keep auditable history (no history rewrite), explicitly record event.

## Impact

- Runtime/source code paths were not part of the accidental commit.
- The accidental commit affected planning/documentation files only.
