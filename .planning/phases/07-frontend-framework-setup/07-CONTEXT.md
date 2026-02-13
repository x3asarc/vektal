# Phase 7: Frontend Framework Setup (Next.js) - Context

**Gathered:** 2026-02-11
**Status:** Ready for research

<domain>
## Phase Boundary

Build the frontend foundation for routing, onboarding, API integration, responsive shell behavior, and refresh-safe state persistence.

Phase 7 clarifies UX, state, and architecture contracts only.
It does not add net-new product capabilities outside roadmap scope.
This document also carries previously agreed operational UX defaults for jobs tracking and ack-first writes. Values marked as defaults are tunable during research without breaking Phase 7 contract intent.

</domain>

<decisions>
## Implementation Decisions

### Frontend Architecture Posture
- Frontend is a thin orchestration and visibility layer.
- Heavy processing remains backend async jobs.
- UI mirrors backend state (not local simulated source of truth).

### Routing and Guard Model
- App Router only in Phase 7.
- Canonical entity routes are required (example: `/jobs/[id]`), and Phase 7 forbids intercepted/parallel route patterns for drawers (drawers remain UI-only).
- Route naming is locked to `/auth/verify`.
- Guard precedence is deterministic:
  1. `!A` -> `/auth/login?returnTo=...`
  2. `A && !V` -> `/auth/verify?returnTo=...`
  3. `A && V && !S` (for S-required routes) -> `/onboarding?returnTo=...`
  4. else allow
- Exemptions:
  - `/auth/*` exempt from A/V/S global checks (route-specific behavior allowed only if it still respects returnTo safety and loop protection rules)
  - `/onboarding` exempt from S check, not from A/V
- `/settings` requires A + V only (no S requirement) in Phase 7.
- `/auth/login` behavior when already authenticated:
  - redirect to safe `returnTo` if present
  - else redirect to `/dashboard`
- `returnTo` must be same-origin internal path only.
- Loop protection required for redirect logic.

### Onboarding Flow (3-Step)
- Step 1: Connect Shopify
- Step 2: Choose ingest path
  - Sync Store (primary CTA)
  - Upload CSV (button or drag-drop)
- Step 3: Preview and Start Import -> Import Progress
- Sync defaults to import everything.
- Advanced scope/filter options are hidden by default.
- If advanced options are opened, invalid/empty selections must be explicit and cannot silently change import intent.
- Completion rule: either Sync Store or Upload CSV path completes onboarding.

### Write Policy and Optimistic Updates
- Ack-first by default for backend writes.
- Never optimistic in Phase 7 for:
  - jobs (`/api/v1/jobs*`)
  - billing (`/api/v1/billing*`)
  - oauth (`/api/v1/oauth*`)
  - auth/session-changing actions
- Optimistic updates are allowlisted for low-risk local UI-only state.

### Pending Feedback and Job State UX
- Global non-blocking pending indicator exists for critical ack-first writes.
- Final visual style is deferred; behavior is locked.
- Job state flow:
  - `idle -> submitting -> accepted -> in_progress -> terminal`
  - terminal: `success | error | cancelled`
- Use a Starting buffer default (~2-3 seconds, tunable) before showing Queued.
- Realtime transport:
  - SSE primary
  - inactivity-probe triggers polling fallback
  - show transport degradation message only if polling also fails
- Cancellation is ack-first and can remain in `cancel_requested` until backend convergence.
- User can navigate away while cancellation converges.

### Global Recovery and Terminal Acknowledgment
- Layout-level global tracker rehydrates active jobs on mount, focus, reconnect, and refresh.
- Registry is lightweight and UI-tracking only; backend remains source of truth.
- On rehydrate, registry state must be re-derived from backend state.
- Ghost transitions:
  - success while away -> passive indicator
  - error while away -> prominent alert
- Adaptive observation:
  - focused tab/layout -> normal cadence
  - blurred/background -> backoff cadence
  - job detail context -> richer/faster observation
- Terminal retention:
  - success transient in global view (default ~10-15s, tunable), then auto-clear
  - cancelled transient (default ~5s, tunable), then auto-clear
  - error sticky until Retry or Dismiss
- If terminal events exceed a default threshold (3+ in ~10s, tunable), collapse into summary notifications.
- Phase 7 acknowledgment lock is local client tracking (backend acknowledge endpoint deferred).

### Persistence Boundaries
- Unsubmitted non-sensitive form drafts use sessionStorage.
- Draft policy includes 2-hour TTL and versioned keys.
- Drafts clear on submit success, explicit reset/cancel, logout, or tab close.
- Sensitive secrets are never stored in client draft persistence.
- Layout preferences (example: sidebar collapse) use localStorage and are device-specific.
- List filters/pagination/search state is URL-query-driven.
- Clean slate is explicit (`Reset Workspace` action), not logo/home navigation.

### TypeScript/Next Baseline Gates (FRONTEND-01)
- Baseline posture:
  - strict typing enabled (`strict: true`)
  - app-router-only delivery in Phase 7
  - lock reproducible Node/package-manager environment in CI
- Phase 7 TypeScript gates:
  - strict baseline plus intent-aligned safety flags
  - defer high-friction strictness flags (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`) to later hardening unless velocity remains high
- Phase 7 lint gates:
  - disallow `@ts-ignore`
  - disallow `any` in feature modules
  - no unused imports/vars
- Escape hatch policy:
  - `@ts-expect-error` only in boundary modules
  - must include ticket id, narrow-scope reason, and removal condition
  - feature modules must consume typed boundary outputs

### API Client, Query Keys, and State Boundaries
- React Query-style server-state management is the canonical server-state layer.
- Query key shape is locked:
  - `[resource, scope, ...rest]`
  - segment 2 is always scope object (`storeId` and/or `userId`)
- Invalidation must be targeted, not root-level blanket invalidation.
- State ownership boundaries:
  - server state -> query cache
  - global UI state -> Zustand-like store
  - wiring concerns -> context providers
  - local component interaction state -> local state

### Module Federation Preparedness (FRONTEND-08)
- Phase 7 is contract-only preparedness (no runtime federation wiring).
- Explicitly out of scope in Phase 7:
  - runtime remotes/hosts
  - dynamic remote loading
  - runtime shared-version negotiation
  - multi-build deployment federation topology
- Required architecture seams:
  - `shell/`
  - `features/`
  - `shared/`
- Dependency direction:
  - shell imports shared + feature contracts only
  - feature imports shared + itself only
  - shared imports shared only
  - no cross-feature imports
- Feature manifests are static TypeScript objects in Phase 7.
- Dashboard remains shell-owned as a composition surface, with feature-provided widget contracts.
- Minimum widget contract includes:
  - stable `id`
  - `requiredState` or inherited guard requirement
  - render entry
  - optional metadata/data dependency hints
- Shared promotion rule:
  - promote only when used by 2+ features or truly platform-level
- Barrel/entry discipline required to prevent deep-internal cross-boundary imports.
- Required artifact: module-boundary map documenting route/module ownership and import-direction rules.

### Shell IA + Responsive Contract (FRONTEND-05/06)
- Density posture:
  - Phase 7 default is Balanced for clarity
  - compact/operator mode is considered later
- Chat surface model:
  - docked on desktop
  - overlay on mobile/tablet
  - canonical full route at `/chat`
  - all chat entry surfaces share one underlying chat state/surface contract
- Navigation emphasis:
  - onboarding-first until activation
  - jobs-first after activation
- Landing rules:
  - if not store-connected: default to `/onboarding`
  - after activation: default to `/dashboard` as jobs-health status hub
- `/jobs` remains primary operational navigation item.
- Mobile strategy is status-first with quick recovery actions, not full desktop parity.
- Breakpoint guidance:
  - sm < 640
  - md 640-1024
  - lg >= 1024
- Region behavior:
  - sidebar: off-canvas on small, non-persistent on medium, persistent on large
  - chat: overlay on small/medium, docked on large
- Notification priority model:
  - global blocking banner > page banner > inline field > toast

### Dashboard Minimum Contract (for `/dashboard` default)
- Dashboard must function as a real jobs-health hub in Phase 7.
- Must include:
  - global health summary by relevant job states
  - needs-attention queue with direct recovery actions
  - in-progress visibility
  - fast recovery actions (view/retry/acknowledge path)
- Must not be decorative-only or non-actionable.

### RFC 7807 Error UX Contract
- Taxonomy axes:
  - scope: `field | page | global`
  - severity: `blocking | degrading | info`
- Status mapping must follow a canonical decision table (Phase 7 artifact).
- UI surfaces:
  - field -> inline errors
  - page -> page banner
  - global/systemic -> shell-level banner/toast rules
- Internal normalized error object is required in API client.
- Phase 7 compatibility rule:
  - accept both backend field error shapes (`errors` map and `violations` list)
  - normalize into one frontend `fieldErrors` contract
- Unknown field errors must not be dropped; surface at page level and log diagnostically.
- Retry copy rule is deterministic: only suggest retry when a retry affordance exists.

### Implementation Discretion
- Final visual styling, motion, and microcopy aesthetics.
- Default interval values for probes/backoff may be tuned during research/implementation while preserving behavior contracts.
- Exact component composition details that do not violate locked boundaries.

</decisions>

<specifics>
## Specific Ideas

- The UI should feel clean under load: background jobs continue while navigation stays responsive.
- A progress mirror model is preferred over frontend-heavy processing.
- Context should remain stable across refreshes without surprising destructive resets.

</specifics>

<deferred>
## Deferred Ideas

- Runtime Module Federation host/remote loading and deployment topology.
- Cross-tab leader election optimization (for high tab-count polling reduction).
- Backend-enforced single field-error extension format.
- Backend terminal acknowledgment endpoint for global seen-state synchronization.
- Compact operator-mode launch timing.

</deferred>

---

*Phase: 07-frontend-framework-setup*
*Context gathered: 2026-02-11*
