# Phase 7 Planning Coverage Map

**Created:** 2026-02-11  
**Purpose:** Verify that planning artifacts cover all locked context decisions from `07-CONTEXT.md`.

## Coverage Matrix

| 07-CONTEXT Area | Locked Decision Summary | Plan Coverage |
|---|---|---|
| Frontend architecture posture | Frontend is orchestration layer; backend jobs are source of truth | `07-01` Task 2, `07-03` Task 2 |
| Routing and guard model | App Router only, deterministic A/V/S guard precedence, route exemptions, same-origin `returnTo`, loop protection | `07-01` Task 2 and Task 3, `07-02` Task 1 |
| Onboarding flow | 3-step flow (Connect Shopify, ingest path, preview/start import), advanced options hidden by default | `07-02` Task 2 |
| Write policy | Ack-first writes; never optimistic for jobs/billing/oauth/auth/session writes | `07-02` Task 2, `07-03` Task 2 |
| Pending feedback and job state UX | Non-blocking pending indicator, lifecycle states, SSE primary + polling fallback policy | `07-02` Task 2, `07-03` Task 2 |
| Global recovery and terminal acknowledgment | Rehydrate on mount/focus/reconnect/refresh, backend re-derivation, ghost/terminal handling and burst collapse | `07-03` Task 2 |
| Persistence boundaries | Session drafts (TTL/version), local UI prefs, URL-query state, explicit reset workspace | `07-03` Task 1 |
| TS/Next baseline gates | Next + strict TS, lint gates (`@ts-ignore` ban, `any` restrictions, unused imports/vars) | `07-01` Task 1 |
| API client / query key / state boundaries | React Query server state, scoped query keys, targeted invalidation, normalized error boundary | `07-01` Task 2 |
| Module federation preparedness | Contract-only MF, static manifests, shell/features/shared seams, no cross-feature imports, boundary map artifact | `07-03` Task 3 |
| Shell IA and responsive contract | Onboarding-first before activation, jobs-first after activation, responsive sidebar/chat behavior, notification priority | `07-02` Task 1 and Task 3 |
| Dashboard minimum contract | Dashboard must be actionable jobs-health hub | `07-02` Task 3 |
| RFC 7807 error UX | Normalized error object, field/page/global surfacing, compatibility with `errors` and `violations` shapes | `07-01` Task 2, `07-03` Task 2 |
| Deferred ideas protection | Runtime federation and other deferred items stay out of Phase 7 | `07-03` Task 3 (explicit out-of-scope enforcement) |

## Requirement Mapping (FRONTEND-01..08)

| Requirement | Plan Coverage |
|---|---|
| FRONTEND-01 Next.js + TypeScript setup | `07-01` Task 1 |
| FRONTEND-02 API client + React Query | `07-01` Task 2 |
| FRONTEND-03 Routing structure | `07-01` Task 3, `07-02` Task 1 |
| FRONTEND-04 Progressive onboarding | `07-02` Task 2 |
| FRONTEND-05 Layout components | `07-02` Task 3 |
| FRONTEND-06 Responsive design | `07-02` Task 3 |
| FRONTEND-07 State management | `07-03` Task 1 and Task 2 |
| FRONTEND-08 Module federation preparation | `07-03` Task 3 |

## Sequential-Thinking Decisions Applied

1. Risk class: **medium-high** (routing/auth/state-cutover risk).
2. Rejected branch: one-shot all-in-one frontend plan.
3. Selected branch: **Foundation -> Integration -> Hardening** across `07-01`, `07-02`, `07-03`.
4. Compatibility rule: backend contracts unchanged; frontend-only migration.
5. Rollback rule: feature-flagged route/observer behavior with fast default-route reversion path.
