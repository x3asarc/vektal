# Phase 8 Planning Coverage Map

**Created:** 2026-02-12  
**Purpose:** Verify Phase 8 plans cover locked context decisions and `RESOLVE-01..08`.

## Coverage Matrix

| 08-CONTEXT Area | Locked Decision Summary | Plan Coverage |
|---|---|---|
| Source trust order | Shopify -> supplier -> web, web only when supplier verified | `08-02` Task 1 |
| Approval baseline | No consented rules => explicit approval per changed field | `08-01` Task 2, `08-03` Task 1 |
| Rule scope + exclusions | Per supplier + field-group; exclusion overrides positive rules | `08-01` Task 2 and Task 3 |
| Dry-run semantics | Group by product; per-field approvals + bulk actions | `08-02` Task 2, `08-03` Task 1 |
| Explainability | Reason sentence, confidence factors, technical details toggle | `08-02` Task 1 and Task 3, `08-03` Task 1 |
| Structural conflicts | New/mismatched variants and option-schema mismatches explicit | `08-02` Task 2 |
| Missing product behavior | Route to `Draft New Product` flow marker | `08-02` Task 2 |
| Snapshot requirement | Batch + per-product pre-change snapshots before apply | `08-01` Task 1, `08-02` Task 2 |
| Scheduled race safety | Pre-flight validation before apply | `08-04` Task 1 |
| Recovery handling | Stale/deleted targets preserved in `Recovery Logs` | `08-04` Task 1 |
| Throughput policy | Adaptive concurrency + dynamic backoff + critical threshold pause | `08-04` Task 2 |
| Conflict-on-schedule | Re-run dry-run for conflicted items only | `08-04` Task 2 |
| Collaboration integrity | Single editor checkout lock; non-owner read-only | `08-01` Task 2, `08-03` Task 2 |
| Activity visibility | `Currently Happening` + `Coming Up Next` | `08-03` Task 2 |
| Strategy quiz | Structured machine-actionable preferences | `08-01` Task 3, `08-03` Task 3 |
| Rule-learning loop | Batched end-of-dry-run suggestions + settings inbox | `08-03` Task 3 |
| Image sovereignty | Download/hash/store/trace + controlled final push | `08-04` Task 3 |
| Deferred scope protection | Full vectorization tuning deferred | No Plan 8 task includes deferred tuning |

## Requirement Mapping (`RESOLVE-01..08`)

| Requirement | Plan Coverage |
|---|---|
| RESOLVE-01 Shopify catalog search | `08-02` Task 1 |
| RESOLVE-02 Supplier catalog search | `08-02` Task 1 |
| RESOLVE-03 Web search + relevance | `08-02` Task 1 |
| RESOLVE-04 Vendor detection + strategy selection | `08-02` Task 1 |
| RESOLVE-05 Field extraction and change modeling | `08-02` Task 2 |
| RESOLVE-06 Vision AI/image compatibility path | `08-04` Task 3 (media pipeline + traceable image handling) |
| RESOLVE-07 SEO generation integration surface | `08-02` Task 2 (change model carries SEO fields), `08-04` Task 2 (apply path) |
| RESOLVE-08 Dry-run preview before apply | `08-02` Task 2 and Task 3, `08-03` Task 1 |

## Wave Plan

| Wave | Plans | Rationale |
|---|---|---|
| 1 | `08-01` | Persistence/policy/locking foundation |
| 2 | `08-02` | Resolver + dry-run compiler depends on 08-01 contracts |
| 3 | `08-03`, `08-04` | UI collaboration and apply engine can execute in parallel on stable dry-run contracts |

## Risk Notes

- Highest execution risk: apply engine correctness under throttle pressure and stale-state drift (`08-04`).
- Highest UX risk: lock clarity and concurrent reviewer behavior (`08-03`).
- Mitigation: explicit contract tests in each plan and blocking human checkpoint in `08-03`.
