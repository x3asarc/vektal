---
phase: 11-product-search-discovery
plan: 02
subsystem: lineage-and-staging
tags: [products, history, diff, bulk-staging, governance, admission]
requires:
  - phase: 11-product-search-discovery
    provides: "11-01 search scope freeze and protected-column metadata"
  - phase: 08-product-resolution-engine
    provides: "dry-run compiler + safety/preflight contracts reused by staging"
provides:
  - "Product detail/history/diff contracts for precision review surfaces"
  - "Semantic bulk staging endpoint with admission policy outputs"
  - "Vendor field-mapping governance endpoints and mapping-gap remediation responses"
  - "Frontend bulk action builder + detail/diff panels wired in search workspace"
key-files:
  created:
    - src/models/product_change_event.py
    - src/models/vendor_field_mapping.py
    - src/api/v1/products/staging.py
    - migrations/versions/a7b8c9d0e1f2_phase11_product_history_and_staging.py
    - tests/api/test_products_history_diff_contract.py
    - tests/api/test_products_bulk_staging_contract.py
    - frontend/src/features/search/hooks/useBulkStaging.ts
    - frontend/src/features/search/components/ProductDetailPanel.tsx
    - frontend/src/features/search/components/ProductDiffPanel.tsx
    - frontend/src/features/search/components/ApprovalBlockCard.tsx
    - frontend/src/features/search/components/BulkActionBuilder.tsx
    - frontend/src/features/search/components/BulkActionBuilder.test.tsx
  modified:
    - src/models/__init__.py
    - src/api/v1/products/routes.py
    - src/api/v1/products/schemas.py
    - src/api/v1/vendors/routes.py
    - src/api/v1/vendors/schemas.py
    - frontend/src/features/search/components/SearchWorkspace.tsx
completed: 2026-02-15
---

# Phase 11-02 Summary

Implemented Phase `11-02` lineage + precision staging scope across backend contracts, frontend review/staging surfaces, and targeted verification.

## Delivered

- Added product lineage contracts:
  - `GET /api/v1/products/{id}` detail payload for precision review,
  - `GET /api/v1/products/{id}/history`,
  - `GET /api/v1/products/{id}/diff`.
- Added semantic bulk staging flow:
  - `POST /api/v1/products/bulk/stage` with frozen selection snapshot and action-block grammar (`set/replace/add/remove/clear/increase/decrease/conditional_set`),
  - admission controller output (`schema_ok`, `policy_ok`, `conflict_state`, `eligible_to_apply`, reasons),
  - policy blocks for protected fields and explicit alt-text overwrite governance.
- Added vendor mapping governance endpoints:
  - `GET /api/v1/vendors/{vendor_id}/mappings`
  - `POST /api/v1/vendors/{vendor_id}/mappings/versions`
- Added frontend precision staging UX:
  - detail panel, diff panel, approval outcome card, bulk action builder, and staging hook integration in search workspace.
- Added persistence models and migration:
  - `product_change_events`
  - `vendor_field_mappings`

## Verification

- Backend:
  - `python -m pytest -q -p no:cacheprovider tests/api/test_products_history_diff_contract.py tests/api/test_products_bulk_staging_contract.py tests/api/test_products_search_contract.py`
  - Result: `13 passed`, `0 failed`
- Frontend:
  - `cd frontend && npm.cmd run test -- "src/features/search/components/BulkActionBuilder.test.tsx" "src/app/(app)/search/page.test.tsx"`
  - Result: `6 passed`, `0 failed`
  - `cd frontend && npm.cmd run typecheck`
  - Result: pass

## Binary Gates

- `SEARCH-04` (detail payload): `GREEN`
- `SEARCH-05` (history): `GREEN`
- `SEARCH-06` (diff): `GREEN`
- `SEARCH-07` (bulk staging + scope): `GREEN`
- `GOV-01` (vendor mapping versioning): `GREEN`
- `GOV-02` (protected-column policy guard): `GREEN`
- `GOV-03` (alt-text preservation/overwrite guard): `GREEN`
- `REL-01` (admission controller): `GREEN`

## Notes

- Test harness stability fix: committed seed records in `tests/api/test_products_bulk_staging_contract.py` fixture to prevent nested app-context rollback from invalidating FK assumptions.
- Frontend test stability fix: enforced cleanup between tests in `frontend/src/features/search/components/BulkActionBuilder.test.tsx`.
