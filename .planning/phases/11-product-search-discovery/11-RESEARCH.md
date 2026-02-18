# Phase 11: Product Search & Discovery - Research

**Researched:** 2026-02-15  
**Domain:** Precision workspace for search, bulk editing, diff review, and safe apply readiness  
**Confidence:** HIGH (contracts and architecture), MEDIUM-HIGH (throughput tuning depends on live shop/API telemetry)

<phase_context>
## Locked Context Inputs

- Shopify is source of truth.
- Precision workspace is the non-chat operator surface.
- Dry-run diff gate is mandatory for mutating operations.
- Admission controller is mandatory between staging and apply.
- Approval model is action-block with per-product include/exclude overrides.
- Bulk cap is up to 1000 SKUs with adaptive chunking/concurrency.
- Snapshot lifecycle is tiered:
  - periodic full-store baseline,
  - per-batch manifest,
  - touched-product pre-change snapshots,
  - hash dedupe and deterministic recovery chain.
- Retry policy is bounded for transient failures only (429/5xx/timeouts).
- Audit retention/export and protected-column/alt-text policies are mandatory.
- Execution mode is adaptive:
  - synchronous chunked path for smaller/safer sets,
  - staged upload + background bulk mutation path for larger sets.
- Recovery logs are actionable replay queues, not passive archives.
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
- Shopify bulk pipeline integration should model:
  - staged uploads,
  - bulk mutation submission,
  - current operation polling/cancel semantics,
  - explicit terminal summary and recovery routing.

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

### 4) Admission, Throughput, and Recovery Runtime (`11-03` cross-cutting)

- Admission controller stages:
  - schema check,
  - policy check,
  - conflict check,
  - commit eligibility decision.
- Throughput governor:
  - additive increase while healthy,
  - multiplicative decrease on 429,
  - bounded chunk/worker caps by operation complexity.
- Recovery engine behavior:
  - retry transient classes with bounded attempts and jitter,
  - route exhaustion to Recovery Logs with replay metadata,
  - keep non-retryable failures in fix queue with clear reason codes.

### 5) Vendor Mapping and Field Governance (`11-02` + `11-03`)

- Add versioned vendor mapping contract per `store + supplier + field_group`.
- Transform chain must remain deterministic:
  - supplier raw -> canonical model -> Shopify payload.
- Unmapped required fields must block dry-run completion with guided remediation.
- Protected-column enforcement is required in:
  - grid interaction layer,
  - API validation layer,
  - persistence layer.
- Alt-text governance:
  - preserve Shopify alt by default,
  - record source/generated candidates with provenance,
  - overwrite only by explicit rule/action approval.

## Data Model Changes Required

### Minimum Additions

1. `product_change_events` (or equivalent)
   - product_id, actor, source, before/after payload, rule/action refs, timestamps.
2. `search_saved_views`
   - user/store scoped saved filters/column presets/sort.
3. `vendor_field_mappings` (versioned)
   - store_id, supplier_id, field_group, mapping_version, mapping_rules, required_coverage_status.
4. Snapshot lifecycle enhancements
   - baseline snapshot type support,
   - optional pointer/dedupe relations from repeated pre-images.
5. Audit export job records
   - async export tracking and file references for CSV/JSON output.
6. Precision operation entities
   - `bulk_operation`: operation state machine + scope snapshot + config.
   - `preview_result`: per-product before/after + risk class + ttl marker.
   - `apply_result`: chunk outcomes + aggregate counters.
   - `recovery_log`: retry eligibility + replay pointer + reason code.

### Existing Model Extensions

- `resolution_snapshots`
  - allow baseline snapshot type,
  - strengthen checksum indexing for dedupe lookups.
- `recovery_logs`
  - ensure payload captures enough metadata to replay from staged failures.
- Product/media linkage
  - internal image asset references and hash metadata for no-passthrough image policy.

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
- `POST /api/v1/products/bulk/admission-check`
  - explicit schema/policy/conflict gate output prior to apply.
- `POST /api/v1/products/bulk/approve`
  - action-block approval with per-product overrides.

### Snapshot/Audit Lifecycle

- `POST /api/v1/resolution/snapshots/baseline/refresh`
- `GET /api/v1/resolution/snapshots/{batch_id}/chain`
- `GET /api/v1/audit/exports/{export_id}`
- `POST /api/v1/audit/exports`
- `GET /api/v1/products/bulk/{operation_id}/progress`
  - live progress stream contract (processed/total, ETA, active chunk, terminal status).

### Vendor Mapping Governance

- `GET /api/v1/vendors/{vendor_id}/mappings`
- `POST /api/v1/vendors/{vendor_id}/mappings/versions`
- `POST /api/v1/vendors/{vendor_id}/mappings/validate`

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
6. **Stale dry-run use after TTL expiry**
   - Mitigation: explicit TTL marker + hard preflight gate + required recompile path.
7. **Vendor mapping drift introducing bad payloads**
   - Mitigation: mapping version pinning in preview/apply + required-field coverage check.
8. **Protected-column accidental mutation by fill/operation**
   - Mitigation: lock in grid + server-side contract rejection + audit event on attempts.

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
| GOV-01 | Vendor mapping versioning and required-field coverage gate. |
| GOV-02 | Protected-column enforcement across UI/API/persistence. |
| GOV-03 | Alt-text preservation with explicit overwrite approval path. |
| REL-01 | Admission controller contract (schema/policy/conflict gates). |
| REL-02 | Bounded transient retry with deferred recovery replay path. |
| REL-03 | Progress/terminal summary contract with replayable recovery payload. |

## Verification Guidance for Planning

### Contract and Integration Tests

- Search API query parsing + cursor correctness + sort determinism.
- Scope snapshot correctness when filters/pages change.
- Dry-run payload correctness for semantic operation blocks.
- History/diff endpoint correctness for version lineage.
- Snapshot dedupe behavior and chain traversal integrity.
- Retry backoff policy behavior for transient failure simulations.
- Audit export schema integrity (CSV/JSON).
- Vendor mapping version pinning and required-field coverage checks.
- Protected-column hard lock tests (grid + API).
- Alt-text preservation/overwrite approval tests.
- Dry-run TTL expiry + forced recompile tests.

### Frontend Tests

- Search page renders cards/grid, filters, and scope banner.
- Selection persists during edits and freezes on dry-run.
- Diff panel renders side-by-side and risk badges.
- Action-block approval UI supports per-product overrides.
- Progress monitor renders processed/total, ETA, and terminal summary.
- Recovery queue UI supports retry-eligible vs non-retryable paths.

## Planning Defaults (from locked context + synthesis)

1. AG Grid path: start with Community baseline; escalate to Enterprise only if required features fail parity tests.
2. Execution mode switch: use synchronous chunk path for smaller low-complexity sets and bulk operation path for large/high-complexity sets.
3. Retention baseline: immutable 24-month audit retention; snapshot hot/cold tier policy finalized in implementation detail docs.
4. Guarded-edit behavior: one explicit elevated confirmation per action-block, not per cell.

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
