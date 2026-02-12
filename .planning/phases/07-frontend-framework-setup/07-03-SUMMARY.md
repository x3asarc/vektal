# 07-03 Summary: Persistence, Job Recovery, and Boundary Hardening

## Completed
- Implemented Phase 7 persistence boundaries:
  - `frontend/src/state/ui-prefs-store.ts`
    - device-specific UI preferences in `localStorage`
    - explicit `resetWorkspace` behavior
  - `frontend/src/state/drafts-store.ts`
    - session draft persistence with `ttlMs` (2-hour TTL), versioned keys, and sensitive-draft rejection
  - `frontend/src/features/jobs/hooks/useJobListStateFromUrl.ts`
    - list/search/filter/pagination state from URL query params
    - explicit reset-workspace query clear path
- Implemented global job reliability layer:
  - `frontend/src/features/jobs/observer/transport-ladder.ts`
    - SSE primary, inactivity fallback to polling, degraded state only when polling also fails
  - `frontend/src/features/jobs/hooks/useJobRehydrate.ts`
    - rehydrate on mount/focus/reconnect from backend jobs API
  - `frontend/src/features/jobs/hooks/useJobDetailObserver.ts`
    - `/jobs/[id]` observer wired for SSE stream with polling fallback path
  - `frontend/src/features/jobs/components/GlobalJobTracker.tsx`
    - layout-level tracker with rehydrate flow and terminal event projection
  - `frontend/src/features/jobs/components/JobTerminalNotifications.tsx`
    - terminal policy defaults: success/cancel transient, error sticky, burst collapse support
  - `frontend/src/shared/errors/error-presenter.ts`
    - unknown field errors surfaced at page scope and logged diagnostically
- Implemented module-boundary preparedness and documentation:
  - `frontend/src/features/manifest.ts` + `frontend/src/features/manifest.contract.test.ts`
    - static feature contracts with `requiredState`
  - `frontend/eslint.config.mjs`
    - seam-oriented restrictions for cross-feature and shared-layer violations
  - `.planning/phases/07-frontend-framework-setup/07-MODULE-BOUNDARY-MAP.md`
    - ownership/import direction map with “no cross-feature imports” rule

## Verification
- `npm.cmd run test -- src/state/drafts-store.test.ts src/state/ui-prefs-store.test.ts src/features/jobs/hooks/useJobListStateFromUrl.test.ts src/features/jobs/observer/transport-ladder.test.ts src/features/jobs/hooks/useJobRehydrate.test.ts src/features/jobs/components/JobTerminalNotifications.test.ts src/features/manifest.contract.test.ts` passed (17 tests).
- `npm.cmd run lint` passed (with seam rules active).
- `npm.cmd run typecheck` passed.
- `npm.cmd run build` passed.
- Integration evidence:
  - `/jobs/[id]` page now uses `useJobDetailObserver` with SSE stream URL and polling fallback path.
  - Job rehydration uses backend jobs endpoints as source of truth.

## Decisions
- Kept runtime module federation explicitly out of scope in Phase 7; delivered contract-only manifest + boundary governance.
- Enforced strict separation between persistence types (URL/session/local) to reduce state drift and stale-secret risk.

## Rollback Path
- Disable job tracker + terminal notification rendering in shell while preserving route skeleton.
- Revert to baseline route pages without observer hooks.
- Keep backend `/api/v1/jobs*` contract unchanged and continue serving source-of-truth job status.

## Notes
- `07-02` was closed with known backend OAuth/store-linking blocker documented in `07-02-SUMMARY.md`.
- `07-03` deliverables complete the planned Phase 7 hardening scope for frontend reliability and seam governance.
