Phase 17.1 Data Contract (Wave 17.1)
Date: 2026-03-05
Status: Planning

Objective
- Define and lock the data contracts and event schemas required to support the field-coverage completeness metrics and versioning for onboarding and dashboard.

Outputs
- Final field catalog for completeness scoring (list of fields and presence semantics)
- Migration plan for product fields (backward/forward compatible changes)
- Event and snapshot contract for Shopify-origin changes (before/after payloads)
- Updated API contracts alignment for completeness-related endpoints (if needed)

Plan
- Audit current Product model and related events: src/models/product.py, src/models/product_change_event.py
- Propose new fields: collections_json, metafields_json, meta_title, meta_description, price_per_unit_value, price_per_unit_unit
- Define event payload shape: before_payload, after_payload, diff_payload within src/models/product_change_event.py
- Define snapshot contract and lifecycle expectations in src/resolution/snapshot_lifecycle.py
- Draft a non-destructive migration plan and versioning scheme
- Draft contract tests for completeness scoring and compatibility checks
- Align with Phase 17 UX/GRAPH references: 17-UX-SPEC.md, 17-GRAPH-LINKS.md

Acceptance Criteria
- Data contracts are locked and versioned; no breaking changes to existing readers/writers
- Ingest and event streams can support completeness metrics with the new fields
- Migration plan is approved and references are in place for rollout with minimal risk

Risks
- Schema drift and migration conflicts
- Backward compatibility concerns with existing readers
- Field coverage definitions may require iteration

References
- .planning/phases/17-product-data-command-center/17-UX-SPEC.md
- .planning/phases/17-product-data-command-center/17-GRAPH-LINKS.md
- .planning/phases/17-product-data-command-center/README.md

UX Alignment
- Desktop Wireframe 4.2 (ASCII) from 17-UX-SPEC.md is the UX target; integrated into this planning wave.
