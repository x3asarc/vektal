# Phase 17 Implementation Plan

Title: Product Data Command Center + Chat-First Product Ops
Date: 2026-03-05
Status: Planning only (no implementation changes in this phase artifact)

## 1) Objective

Implement a product-only operational loop where:

1. Onboarding triggers immediate Shopify product ingest into local DB.
2. Dashboard becomes the home command center with field-level completeness analytics.
3. Live listener keeps DB in sync with Shopify product changes.
4. Historical states are preserved for rollback (no destructive overwrite model).
5. Chat remains the core execution interface and clarifies ambiguous requests until executable.

## 2) Canonical references

- Roadmap/state anchors:
  - [.planning/ROADMAP.md](../../ROADMAP.md)
  - [.planning/STATE.md](../../STATE.md)
- UX spec for this phase:
  - [17-UX-SPEC.md](./17-UX-SPEC.md)
- Graphiti/Neo4j evidence map:
  - [17-GRAPH-LINKS.md](./17-GRAPH-LINKS.md)

## 3) What exists now (reuse map)

### Frontend reuse

- Dashboard shell and health matrix baseline:
  - [frontend/src/app/(app)/dashboard/page.tsx](../../../frontend/src/app/(app)/dashboard/page.tsx)
- Chat workspace and streaming fallback:
  - [frontend/src/features/chat/components/ChatWorkspace.tsx](../../../frontend/src/features/chat/components/ChatWorkspace.tsx)
  - [frontend/src/features/chat/hooks/useChatSession.ts](../../../frontend/src/features/chat/hooks/useChatSession.ts)
  - [frontend/src/features/chat/hooks/useChatStream.ts](../../../frontend/src/features/chat/hooks/useChatStream.ts)
- App shell and nav:
  - [frontend/src/shell/components/AppShell.tsx](../../../frontend/src/shell/components/AppShell.tsx)
  - [frontend/src/shell/components/Sidebar.tsx](../../../frontend/src/shell/components/Sidebar.tsx)

### Backend/data reuse

- Product model + enrichment fields:
  - [src/models/product.py](../../../src/models/product.py)
- Product change lineage model:
  - [src/models/product_change_event.py](../../../src/models/product_change_event.py)
- Snapshot/rollback chain primitives:
  - [src/models/resolution_snapshot.py](../../../src/models/resolution_snapshot.py)
  - [src/resolution/snapshot_lifecycle.py](../../../src/resolution/snapshot_lifecycle.py)
- Product API (search, detail, history, diff, enrichment lifecycle):
  - [src/api/v1/products/routes.py](../../../src/api/v1/products/routes.py)
  - [src/api/v1/products/schemas.py](../../../src/api/v1/products/schemas.py)
- Ingest orchestration + job runtime:
  - [src/api/v1/jobs/routes.py](../../../src/api/v1/jobs/routes.py)
  - [src/tasks/ingest.py](../../../src/tasks/ingest.py)
  - [src/jobs/orchestrator.py](../../../src/jobs/orchestrator.py)

### Chat execution reuse

- Chat API contracts, actions, and SSE:
  - [src/api/v1/chat/routes.py](../../../src/api/v1/chat/routes.py)
  - [src/api/v1/chat/orchestrator.py](../../../src/api/v1/chat/orchestrator.py)
  - [src/api/v1/chat/approvals.py](../../../src/api/v1/chat/approvals.py)

## 4) Confirmed gaps to close in Phase 17

1. Dashboard currently uses placeholder KPI values and does not expose full field completeness model.
2. Product ingest exists as job infrastructure, but no explicit product-data quality aggregate service for dashboard.
3. Product change history exists, but user-facing rollback entrypoint is not integrated into dashboard-home flow.
4. Shopify webhook coverage is incomplete for product-sync listener behavior (only legacy order example route exists in [src/app.py](../../../src/app.py)).
5. Product schema does not yet cover all desired fields (collections, unit-price semantics, full metafield coverage) as first-class normalized fields.
6. Chat clarifier loop exists implicitly, but no explicit dashboard-facing "pending clarification" contract.

## 5) Target architecture (Phase 17)

```text
Shopify Product Domain
   |
   |  (bootstrap ingest)
   v
Ingest Pipeline (Jobs + Celery + Redis)
   |
   +--> Product Core Tables
   +--> Product Field Coverage Aggregate
   +--> Product Version/Event Store

Shopify Change Listener
   |
   +--> Webhook Receiver (products/*)
   +--> Reconciliation Poller (safety net)
   +--> Versioned upsert + snapshot append

Read APIs
   |
   +--> Dashboard Metrics API (completeness, missing %, trends, distributions)
   +--> Product Timeline/Rollback API
   +--> Chat Clarifier Queue API

Frontend
   |
   +--> Dashboard Command Center (home)
   +--> Chat Dock + full /chat workspace
```

## 6) Data model plan (product-only)

### 6.1 Keep and extend existing `Product`

Current source:
- [src/models/product.py](../../../src/models/product.py)

Planned additions (exact schema names to be finalized during migration design):
- `collections_json` (or normalized join table in later wave)
- `metafields_json` (scoped to approved namespaces)
- `meta_title`, `meta_description`
- `price_per_unit_value`, `price_per_unit_unit`
- `field_presence_bitmap`/computed presence helper (optional optimization)

### 6.2 Version/state preservation model

Reuse + extend:
- Change events: [src/models/product_change_event.py](../../../src/models/product_change_event.py)
- Snapshot lifecycle: [src/resolution/snapshot_lifecycle.py](../../../src/resolution/snapshot_lifecycle.py)

Plan:
- On every Shopify-origin update: append a change event with `before_payload`, `after_payload`, `diff_payload`.
- Keep immutable historical snapshots (hash-addressed where feasible).
- Add rollback intent metadata linking dashboard action to reversible chain.

## 7) Ingest and sync plan

### 7.1 Bootstrap ingest on onboarding

Reuse:
- [frontend/src/features/onboarding/components/OnboardingWizard.tsx](../../../frontend/src/features/onboarding/components/OnboardingWizard.tsx)
- [src/api/v1/jobs/routes.py](../../../src/api/v1/jobs/routes.py)
- [src/jobs/orchestrator.py](../../../src/jobs/orchestrator.py)

Plan:
- Keep job submission flow but introduce product ingest mode that computes completeness aggregates as part of finalization.
- Persist ingest watermark (`last_full_ingest_at`, `last_shopify_cursor`) for listener handoff.

### 7.2 Live listener / heartbeat

Plan components:
1. Shopify webhook receiver for product create/update/delete topics.
2. Signature verification path with store credential lookup.
3. Idempotency keying by webhook event id + store.
4. Reconciliation poller (daemon) to backfill missed webhooks.

Expected persistence behavior:
- No destructive overwrite-only path.
- Every applied delta writes event + optional snapshot pointer.

## 8) Dashboard metrics API plan

New API surface (under `/api/v1/dashboard/*` or `/api/v1/products/metrics/*`):

1. `GET completeness/summary`
- total products
- catalog completeness %
- missing critical %
- SEO readiness %

2. `GET completeness/by-field`
- field fill-rate rows
- sorted by lowest fill-rate

3. `GET completeness/distribution`
- histogram buckets by per-product completeness

4. `GET activity/recent`
- latest Shopify/platform events + source labels

5. `GET clarifications/pending`
- unresolved chat clarifier prompts tied to session/action ids

## 9) Dashboard frontend implementation plan

Primary target file:
- [frontend/src/app/(app)/dashboard/page.tsx](../../../frontend/src/app/(app)/dashboard/page.tsx)

Plan:
1. Replace static KPI placeholders with API-backed data.
2. Implement ASCII-specified command-center block structure from [17-UX-SPEC.md](./17-UX-SPEC.md).
3. Add embedded Chat Command Dock on dashboard (not replacing `/chat`, just making chat primary from home).
4. Add product-data visualizations:
- field coverage matrix
- completeness distribution
- trend micrographs
5. Add activity timeline with rollback launch actions.

Design constraints:
- Keep current token system and forensic style from:
  - [frontend/src/app/design-tokens.css](../../../frontend/src/app/design-tokens.css)
  - [frontend/src/app/globals.css](../../../frontend/src/app/globals.css)

## 10) Chat behavior plan

Backend references:
- [src/api/v1/chat/routes.py](../../../src/api/v1/chat/routes.py)
- [src/api/v1/chat/orchestrator.py](../../../src/api/v1/chat/orchestrator.py)

Plan:
1. Introduce explicit clarifier-state contract (pending questions, required slots).
2. Expose clarifier backlog for dashboard widget.
3. Keep mutation governance path: dry-run -> approval -> apply.
4. Add command scaffolds for common dashboard quick actions.

## 11) Phase 17 execution waves

### Wave 17.1 - Data contract + schema extension

Outputs:
- Final tracked field catalog for completeness scoring.
- Product schema/migration plan for missing product-domain fields.
- Event/snapshot contract for Shopify-origin changes.

Acceptance:
- Deterministic completeness score can be computed for every product.

### Wave 17.2 - Onboarding ingest hardening

Outputs:
- Bootstrap ingest writes product records + completeness aggregates.
- Ingest watermark persisted.

Acceptance:
- Freshly connected store has dashboard metrics without manual refresh tasks.

### Wave 17.3 - Shopify listener + reconciliation daemon

Outputs:
- Webhook receiver for product changes.
- Reconciliation poller for missed events.
- Idempotent event ingestion.

Acceptance:
- Product changes from Shopify appear in platform state with traceable event lineage.

### Wave 17.4 - Dashboard metrics APIs

Outputs:
- Summary/by-field/distribution/activity/clarifier endpoints.

Acceptance:
- APIs can render all required dashboard blocks from UX spec.

### Wave 17.5 - Dashboard command-center UI

Outputs:
- Dashboard fully aligned to ASCII UX layout.
- Chat dock integrated into dashboard home.
- Visualizations and timeline active.

Acceptance:
- User can initiate primary workflows directly from dashboard.

### Wave 17.6 - Rollback UX integration

Outputs:
- Dashboard-to-rollback flow integrated with snapshot/event chain.

Acceptance:
- User can select historical product state and trigger governed rollback flow.

## 12) Verification strategy for Phase 17

1. Contract tests
- completeness calculations
- API schema consistency
- clarifier-state contract

2. Integration tests
- onboarding ingest -> metrics availability
- webhook event -> version/event append
- reconciliation catches missed updates

3. UI tests
- dashboard block rendering states (loading/empty/error/success)
- chat dock interactions
- launchpad to chat prefill

4. Safety checks
- no history loss under repeated updates
- rollback path references valid prior states only

## 13) Risks and controls

1. Risk: webhook misses or duplication.
- Control: idempotency keys + reconciliation poller.

2. Risk: metric drift due asynchronous updates.
- Control: deterministic recompute job + watermark-based audits.

3. Risk: dashboard complexity regression.
- Control: block-level UX contract + strict state handling.

4. Risk: historical storage growth.
- Control: hashed dedupe for snapshots and retention policy tuning.

## 14) Deliverables created in this planning task

- [17-UX-SPEC.md](./17-UX-SPEC.md)
- [17-GRAPH-LINKS.md](./17-GRAPH-LINKS.md)
- [17-PLAN.md](./17-PLAN.md)

No application code was implemented in this task.
