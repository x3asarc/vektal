# Phase 7 Discovery: Frontend Contract Baseline

status: draft
phase: 07
type: discovery
updated: 2026-02-11

## Summary

Local repository inspection confirms backend API foundations from Phases 4-6 are present and mostly frontend-consumable under `/api/v1/*` with session-cookie auth.

Frontend is currently a minimal Next.js placeholder (`frontend/pages/index.js`) and has no typed client, route shell, or onboarding state model yet.

Recommendation: run Phase 7 as a research-first implementation sequence, starting with contract-safe foundation work before UI breadth.

## Current Frontend Baseline

- Framework: Next.js 14.1.0 + React 18.2.0
- Routing mode: Pages Router (`frontend/pages/*`)
- Existing UI: single placeholder page only
- Missing for Phase 7:
  - TypeScript setup
  - route architecture
  - API client abstractions
  - persistent frontend state model
  - responsive layout system

## Backend Contract Inventory (Initial)

### Auth and Identity

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/auth/verify-email`
- `POST /api/v1/auth/resend-verification`
- `GET /api/v1/auth/account-status`

Observed behavior notes:
- Session-cookie authentication (`SessionAuth`)
- Account warnings exposed for onboarding guidance

### Shopify OAuth

- `GET /api/v1/oauth/shopify`
- `GET /api/v1/oauth/callback`
- `GET /api/v1/oauth/status`
- `POST /api/v1/oauth/disconnect`

Observed behavior notes:
- OAuth flow writes user/account progression states needed by onboarding UX

### Billing

- `GET /api/v1/billing/plans`
- `POST /api/v1/billing/create`
- `POST /api/v1/billing/check-email`
- `GET /api/v1/billing/subscription`
- `POST /api/v1/billing/upgrade`
- `POST /api/v1/billing/downgrade`
- `POST /api/v1/billing/cancel-downgrade`

### Jobs and Realtime

- `GET /api/v1/jobs`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/cancel`
- `GET /api/v1/jobs/{job_id}/stream` (SSE)
- `GET /api/v1/jobs/{job_id}/status` (polling fallback)

Observed behavior notes:
- Job creation is non-blocking (`202`)
- Stream URL is returned by job payloads
- Cancellation supports active states only

### Domain Data

- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `GET /api/v1/vendors`
- `GET /api/v1/vendors/{vendor_id}`
- `GET /api/v1/vendors/{code}`
- `GET /api/v1/user/version`
- `POST /api/v1/user/migrate-to-v2`
- `POST /api/v1/user/rollback-to-v1`

## Primary Recommendation

Start Phase 7 with a foundation-first plan:
1. Establish TypeScript + route shell + API client conventions.
2. Implement onboarding and auth-aware navigation with strict contract handling.
3. Layer job execution and realtime progress UI with explicit SSE-to-poll fallback.

This order minimizes risk while directly satisfying FRONTEND-01..08.

## Risks and Unknowns

1. Pages Router vs App Router migration timing is unresolved.
2. Error normalization strategy (RFC 7807 to UI-friendly model) is not yet codified.
3. SSE reconnect/backoff behavior is not yet standardized in frontend code.
4. Existing legacy Flask UI parity requirements are not fully mapped.

## Confidence

Level: Medium
Reason: Backend contracts are concrete in local code, but frontend architectural choices and migration sequencing still need explicit decisions.

## Next Artifact

Create `07-01-PLAN.md` with implementation tasks driven by this discovery.
