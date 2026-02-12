# Phase 07 Module Boundary Map

## Ownership
- `shell/`: app composition, global chrome, route-level orchestration.
- `features/`: domain modules (`onboarding`, `jobs`, etc.) with explicit contracts.
- `shared/`: cross-feature primitives only (types, error adapters, utils).

## Import Direction Rules
- `shell` may import:
  - `shared/*`
  - top-level feature contracts (`@/features` or `@/features/manifest`)
- `features/*` may import:
  - `shared/*`
  - same feature internals
- `shared/*` may import:
  - `shared/*` only

## Forbidden
- no cross-feature imports (`features/onboarding` must not import `features/jobs`, and vice versa).
- no shell imports of deep feature internals.
- no shared imports of shell or feature modules.

## Runtime Federation Scope
- Phase 07 is contract-only.
- No runtime remotes, hosts, or dynamic remote loaders are introduced here.
- Feature ownership is represented via static manifests (`frontend/src/features/manifest.ts`).

## Route/Module Alignment
- `/dashboard` remains shell-owned composition surface.
- `/onboarding` is feature-owned flow rendered through shell.
- `/jobs/[id]` is canonical entity route with observer hooks under `features/jobs`.
