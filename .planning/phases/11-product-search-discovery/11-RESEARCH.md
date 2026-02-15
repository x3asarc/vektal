# Phase 11: Product Search & Discovery - Research

**Researched:** 2026-02-15  
**Domain:** Precision workspace for search, bulk editing, diff review, and safe apply readiness  
**Confidence:** HIGH (contracts and architecture), MEDIUM-HIGH (throughput tuning depends on live shop/API telemetry)

<phase_context>
## Locked Context Inputs

- Shopify is source of truth.
- Precision workspace is the non-chat operator surface.
- Dry-run diff gate is mandatory for mutating operations.
- Approval model is action-block with per-product include/exclude overrides.
- Bulk cap is up to 1000 SKUs with adaptive chunking/concurrency.
- Snapshot lifecycle is tiered:
  - periodic full-store baseline,
  - per-batch manifest,
  - touched-product pre-change snapshots,
  - hash dedupe and deterministic recovery chain.
- Retry policy is bounded for transient failures only (429/5xx/timeouts).
- Audit retention/export and protected-column/alt-text policies are mandatory.
</phase_context>

## Executive Summary

Phase 11 should deliver a production-grade precision workspace in three waves:

1. `11-01`: multi-field search, explicit scope selection, and high-fidelity grid foundation.
2. `11-02`: product detail lineage/diff and action-block bulk staging with dry-run previews.
3. `11-03`: snapshot lifecycle efficiency, retention/export contracts, and reliability hardening.

This should reuse existing Phase 8/10 infrastructure wherever possible:

- Phase 8 already provides dry-run/apply/preflight/recovery-log primitives.
- Phase 10 already provides typed diff/action/progress rendering patterns.
- Product APIs exist but are currently minimal and need significant extension for Phase 11 requirements.

## Internal Baseline Findings

### Backend

- Existing product list API is basic cursor pagination + vendor filter only:
  - `src/api/v1/products/routes.py`
  - `src/api/v1/products/schemas.py`
- Existing resolution stack already contains:
  - dry-run compiler, preflight, apply, recovery logs,
  - immutable snapshots (`batch_manifest`, `product_pre_change`) with checksum field.
- Snapshot model currently has a strict type check that excludes a baseline snapshot type:
  - `src/models/resolution_snapshot.py`
- Recovery log and retrieval endpoints already exist:
  - `src/api/v1/resolution/routes.py`
  - `src/models/recovery_log.py`

### Frontend

- `/search` route is guarded but page implementation does not exist yet:
  - guard references `/search` in `frontend/src/lib/auth/guards.ts`
  - app directory currently has no search page.
- Existing UI already includes shell/layout, chat diff renderers, and job progress patterns that can be reused.

## External Research Synthesis (with Context7)

### Context7 Evidence

1. **Shopify Admin GraphQL** (`/websites/shopify_dev_api_admin-graphql_2025-07`)
   - Product search/filtering uses query syntax in `products(...)` / count queries.
   - Cursor-based pagination is native through `pageInfo`.
   - Bulk mutation lifecycle requires staged upload path and `bulkOperationRunMutation`.
   - One bulk query + one bulk mutation operation per app/shop at a time.
   - `currentBulkOperation` and cancel endpoints are first-class.

2. **AG Grid React Data Grid** (`/websites/ag-grid_react-data-grid`)
   - Supports range selection, clipboard flows, batch editing, and fill-handle axis control.
   - Axis direction can be explicitly constrained (`x`, `y`, `xy`) which matches locked vertical-default policy.
   - Read-only/locked columns and keyboard-first table interactions are supported patterns.

3. **SQLAlchemy 2.x** (`/websites/sqlalchemy_en_21`)
   - Large result sets should use `yield_per`/streaming strategies to avoid memory blowups.
   - Dynamic filter composition and deterministic order-by contracts should be explicit for keyset/cursor behavior.

### Practical Implications

- Search API contracts should be keyset/cursor first with deterministic tie-breakers.
- Phase 11 bulk discovery/staging should not bypass Phase 8 mutation safety engine.
- Grid technology should support strong keyboard/selection/fill behavior from day one; AG Grid is a fit for the locked precision requirements.

## Recommended Architecture

### 1) Search and Scope Control Plane (`11-01`)

- Introduce a richer search contract in products domain:
  - multi-field text and exact identifiers (`sku`, `barcode`, `hs_code`, `vendor`, `tags`, ranges),
  - explicit sort contract,
  - cursor/keyset pagination contract,
  - selection scope state (`visible`, `filtered`, `explicit_ids`).
- Add saved filter presets per user/store for repeat operations.

### 2) Detail + Diff + Staging Plane (`11-02`)

- Add product detail API with:
  - complete field view,
  - change-history feed,
  - version-to-version diff payload.
- Add bulk action staging endpoints:
  - accept scope snapshot + semantic operation blocks,
  - compile proposed mutations,
  - emit side-by-side dry-run diffs with risk badges.
- Keep approval model action-block with per-product override/exclusion.

### 3) Snapshot and Reliability Plane (`11-03`)

- Extend snapshot model to support baseline lifecycle:
  - periodic full-store baseline snapshots,
  - pre-change product snapshots for touched items,
  - batch manifest records.
- Add checksum/pointer dedupe policy to avoid blob duplication.
- Enforce dry-run TTL (60 minutes) and mandatory preflight revalidation before apply.
- Add audit retention/export services and endpoints (CSV + JSON).

## Data Model Changes Required

### Minimum Additions

1. `product_change_events` (or equivalent)
   - product_id, actor, source, before/after payload, rule/action refs, timestamps.
2. `search_saved_views`
   - user/store scoped saved filters/column presets/sort.
3. Snapshot lifecycle enhancements
   - baseline snapshot type support,
   - optional pointer/dedupe relations from repeated pre-images.
4. Audit export job records
   - async export tracking and file references for CSV/JSON output.

### Existing Model Extensions

- `resolution_snapshots`
  - allow baseline snapshot type,
  - strengthen checksum indexing for dedupe lookups.
- `recovery_logs`
  - ensure payload captures enough metadata to replay from staged failures.

## API Contract Targets

### Search and Discovery

- `GET /api/v1/products/search`
  - query, filters, sort, cursor, limit.
- `POST /api/v1/products/search/selection-snapshots`
  - freeze scope for dry-run consistency.
- `GET /api/v1/products/{id}`
  - full detail payload for precision side panel.
- `GET /api/v1/products/{id}/history`
  - paginated change history.
- `GET /api/v1/products/{id}/diff`
  - compare versions / timestamps / snapshots.

### Bulk Staging and Preview

- `POST /api/v1/products/bulk/stage`
  - semantic action blocks + scope snapshot.
- `POST /api/v1/products/bulk/dry-run`
  - compile and return per-product diff/risk payload.
- `POST /api/v1/products/bulk/approve`
  - action-block approval with per-product overrides.

### Snapshot/Audit Lifecycle

- `POST /api/v1/resolution/snapshots/baseline/refresh`
- `GET /api/v1/resolution/snapshots/{batch_id}/chain`
- `GET /api/v1/audit/exports/{export_id}`
- `POST /api/v1/audit/exports`

## Risk Areas and Mitigations

1. **Large filter result sets and memory pressure**
   - Mitigation: keyset/cursor pagination and `yield_per` streaming query paths.
2. **Concurrent catalog drift between dry-run and apply**
   - Mitigation: TTL + preflight edge revalidation + conflicted-item holds.
3. **Selection blast radius mistakes**
   - Mitigation: always-visible scope banner + immutable selection snapshot for dry-run/apply.
4. **Snapshot storage explosion**
   - Mitigation: baseline+delta architecture with checksum dedupe and pointer reuse.
5. **Retry storms on transient API failures**
   - Mitigation: bounded retry + jitter + queue backpressure + deferred recovery routing.

## Requirement Mapping

| Requirement | Research-Derived Contract |
|---|---|
| SEARCH-01 | Multi-field filter grammar with explicit query operator mapping. |
| SEARCH-02 | Advanced filter sets and saved views with deterministic scope behavior. |
| SEARCH-03 | Product card/grid payload model with configurable columns and protected field indicators. |
| SEARCH-04 | Product detail endpoint and panel contract with full field payload. |
| SEARCH-05 | Change-event lineage model and retrieval API. |
| SEARCH-06 | Side-by-side diff contract with risk/conflict annotations. |
| SEARCH-07 | Bulk selection snapshot and semantic action staging contracts. |
| SNAP-01 | Periodic baseline snapshot scheduler/service contract. |
| SNAP-02 | Mandatory batch manifest + touched-product pre-change capture contract. |
| SNAP-03 | Checksum dedupe and pointer reuse strategy. |
| SNAP-04 | Retention/export and deterministic recovery-chain retrieval contracts. |

## Verification Guidance for Planning

### Contract and Integration Tests

- Search API query parsing + cursor correctness + sort determinism.
- Scope snapshot correctness when filters/pages change.
- Dry-run payload correctness for semantic operation blocks.
- History/diff endpoint correctness for version lineage.
- Snapshot dedupe behavior and chain traversal integrity.
- Retry backoff policy behavior for transient failure simulations.
- Audit export schema integrity (CSV/JSON).

### Frontend Tests

- Search page renders cards/grid, filters, and scope banner.
- Selection persists during edits and freezes on dry-run.
- Diff panel renders side-by-side and risk badges.
- Action-block approval UI supports per-product overrides.

## Open Questions to Resolve During Planning

1. Whether AG Grid Community capabilities are sufficient or Enterprise modules are required for v1 feature parity.
2. Threshold policy for switching from synchronous chunked mutations to Shopify bulk operation mode.
3. Exact retention tiering for snapshots vs audit exports (hot vs cold storage behavior).
4. UI behavior for guarded-edit columns in mixed bulk operations (single additional confirmation vs per-action confirmation).

## Sources

### Context7 Sources
- `/websites/shopify_dev_api_admin-graphql_2025-07` (products query/filter, cursor pagination, bulk operations lifecycle)
- `/websites/ag-grid_react-data-grid` (cell/range selection, fill-handle axis control, clipboard and batch editing patterns)
- `/websites/sqlalchemy_en_21` (large-result streaming and ORM query performance practices)

### Internal Sources
- `.planning/phases/11-product-search-discovery/11-CONTEXT.md`
- `precisionworkspace.md`
- `src/api/v1/products/routes.py`
- `src/api/v1/products/schemas.py`
- `src/api/v1/resolution/routes.py`
- `src/models/product.py`
- `src/models/resolution_snapshot.py`
- `src/models/recovery_log.py`
- `frontend/src/lib/auth/guards.ts`

## Metadata

- Research method: internal code audit + external benchmark synthesis + Context7 primary-doc extraction.
- Context7 applicability: applicable and used (3 libraries).
- Planning recommendation: proceed with 3-wave Phase 11 execution aligned to roadmap (`11-01`, `11-02`, `11-03`).

