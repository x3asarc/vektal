# Phase 11 GOV / REL Glossary

**Phase:** 11-product-search-discovery  
**Created:** 2026-02-15  
**Purpose:** Single reference for governance (`GOV-*`) and reliability (`REL-*`) contracts used across Phase 11 planning and execution.

## GOV Contracts (Governance)

Governance contracts define policy boundaries: what changes are allowed, how they are controlled, and where enforcement must happen.

### GOV-01: Vendor Mapping Versioning + Coverage Gate
- Definition:
  - Vendor mappings are versioned per `store + supplier + field_group`.
  - Required-field mapping coverage must pass before dry-run can complete.
- Why:
  - Prevent silent bad payloads from drifting mapping logic.
- Enforcement points:
  - Mapping service lookup,
  - dry-run compile gate,
  - admission controller policy stage.
- Expected evidence:
  - Mapping version id in dry-run/apply records,
  - machine-readable blocking errors for unmapped required fields.

### GOV-02: Protected Column Enforcement
- Definition:
  - Protected/system columns cannot be overwritten by fill, bulk ops, or direct API mutation.
- Why:
  - Prevent catastrophic corruption of identifiers/lineage keys.
- Enforcement points:
  - UI grid locks and indicators,
  - API contract validation,
  - persistence/model-level guards.
- Expected evidence:
  - Rejected mutation attempts with explicit error codes,
  - tests proving locks at UI + API.

### GOV-03: Alt-Text Preservation Policy
- Definition:
  - Existing Shopify alt text is preserved by default.
  - Overwrite allowed only via explicit rule or explicit action approval.
- Why:
  - Avoid accidental SEO/accessibility regressions.
- Enforcement points:
  - Staging/diff representation,
  - approval workflow,
  - apply payload construction.
- Expected evidence:
  - Diff rows showing `preserved` vs `approved overwrite`,
  - audit records including actor and reason.

## REL Contracts (Reliability)

Reliability contracts define operational safety under load/failure: admission checks, retry behavior, and deterministic runtime status.

### REL-01: Admission Controller Gate
- Definition:
  - Every mutation set must pass four gates before apply eligibility:
    - `schema_ok`
    - `policy_ok`
    - `conflict_state`
    - `eligible_to_apply`
- Why:
  - Prevent unsafe apply paths and force consistent pre-apply decisions.
- Enforcement points:
  - bulk staging compile,
  - pre-apply readiness checks,
  - approval transition.
- Expected evidence:
  - Admission output persisted and returned in contracts,
  - blocked applies when any gate fails.

### REL-02: Bounded Transient Retry + Deterministic Defer
- Definition:
  - Retry only transient classes: `429`, `timeout`, `5xx`.
  - Use bounded attempts with exponential backoff + jitter.
  - On exhaustion, route item/chunk to Recovery Logs with replay metadata.
- Why:
  - Avoid retry storms while preserving recoverability.
- Enforcement points:
  - apply engine execution loop,
  - retry policy utility,
  - recovery logging path.
- Expected evidence:
  - Retry attempt counters and terminal reason code,
  - deterministic defer entries for exhausted retries.

### REL-03: Progress + Terminal Summary Contract
- Definition:
  - Runtime status must expose machine-readable progress and terminal outcomes:
    - `processed`, `total`, `eta`,
    - active chunk/item,
    - final `success`, `failed`, `deferred`, `retryable`.
- Why:
  - Give operators predictable control and observable execution state.
- Enforcement points:
  - progress endpoints/streams,
  - apply completion aggregation,
  - summary and export payloads.
- Expected evidence:
  - stable response schema in tests,
  - terminal summary parity with recovery/export records.

## Quick Mapping (Phase 11)

- `11-01`: `GOV-02` foundation via protected-column UI/contract metadata.
- `11-02`: `GOV-01`, `GOV-02`, `GOV-03`, `REL-01`.
- `11-03`: `REL-02`, `REL-03` + snapshot/audit chain reliability.

## Canonical Phase References

- `.planning/phases/11-product-search-discovery/11-CONTEXT.md`
- `.planning/phases/11-product-search-discovery/11-RESEARCH.md`
- `.planning/phases/11-product-search-discovery/11-PLANNING-COVERAGE.md`
- `.planning/phases/11-product-search-discovery/11-01-PLAN.md`
- `.planning/phases/11-product-search-discovery/11-02-PLAN.md`
- `.planning/phases/11-product-search-discovery/11-03-PLAN.md`
