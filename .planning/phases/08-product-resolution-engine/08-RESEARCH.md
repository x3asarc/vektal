# Phase 8: Product Resolution Engine - Research

**Researched:** 2026-02-12  
**Domain:** Product resolution, dry-run governance, and controlled Shopify apply execution  
**Confidence:** HIGH (repo-pattern fit), MEDIUM (throughput tuning needs runtime calibration)

## User Constraints

Copied from Phase 8 context decisions and treated as locked:

- Shopify is source of truth.
- Source priority is Shopify -> supplier data -> web; web is only eligible when supplier is user-verified.
- Unknown suppliers at CSV upload must trigger verification + 1-3 field sample mapping check.
- Auto-apply consent is per supplier + per field group (`images`, `text`, `pricing`, `ids`).
- If no consented rules exist, every changed field requires explicit approval.
- Dry-run default grouping is by product; approval granularity is per field with bulk actions.
- Rule suggestions are batched at end of dry-run and available in Settings.
- Pre-change snapshots are mandatory (batch manifest + per-product pre-change snapshot).
- Pre-flight validation is required before apply (target within 60 seconds of first mutation call).
- Missing/deleted Shopify targets after approval must not be pushed and must be preserved in `Recovery Logs`.
- Active dry-run review is single-editor checkout (batch lock); non-owners are read-only.
- Variant mismatch policy is explicit: new variants are structural conflicts, prompt for creation, and use safe defaults (`draft` and/or zero inventory) unless user rule allows auto-create.
- Exclusion/negative rules must be supported and override positive rules.
- Image sovereignty is mandatory: download/hash/store assets, no vendor URL passthrough at final push.
- Deferred: full embedding/vector tuning remains out of scope for this phase.

## Summary

Phase 8 should be implemented as a governed pipeline, not a one-off matcher:
1) resolve candidates across approved sources,
2) build a persisted dry-run with field-level diffs and reasons,
3) require explicit approvals (or consented auto-rules),
4) run guarded apply with pre-flight validation, adaptive throttling, and recovery logging.

The current codebase already has strong primitives we should extend, not replace: Flask v1 API blueprint structure, SQLAlchemy models/migrations, and Celery orchestration from Phase 6. Phase 8 should add a new bounded context (`resolution`) with explicit persistence for batches, changes, rules, locks, snapshots, and recovery logs.

Primary planning decision: use a four-plan execution split to maintain quality and reduce context overload:
- `08-01`: persistence + policy + locks foundation.
- `08-02`: multi-source resolver + structural conflict + dry-run compiler APIs.
- `08-03`: collaborative review UX + strategy quiz + suggestion inbox.
- `08-04`: guarded apply engine + pre-flight/recovery + image sovereignty.

**Primary recommendation:** execute in dependency waves (`08-01` -> `08-02` -> parallel `08-03`/`08-04`) instead of collapsing into one or two oversized plans.

## External Deep-Dive (Shopify 2026-Relevant)

### 1. API Direction (Critical)
- Shopify REST Admin is explicitly legacy (as of 2024-10-01), and new public apps are expected to use GraphQL Admin.
- Product variant/image REST resources are deprecated in newer REST versions.
- Implication for Phase 8: design resolution/apply contracts around GraphQL Admin first; treat REST compatibility as fallback only.

### 2. Rate Limits and Throughput (Confirms Locked Policy)
- GraphQL Admin uses calculated query cost and throttle metadata in response `extensions.cost.throttleStatus`.
- REST uses leaky bucket with `X-Shopify-Shop-Api-Call-Limit` and `Retry-After` on `429`.
- Shopify docs explicitly recommend dynamic backoff/queuing behavior.
- Implication for Phase 8: adaptive concurrency and dynamic backoff policy in context is correct and should be codified in execution tasks.

### 3. Variant Creation and Structural Changes
- `productVariantsBulkCreate` / `productVariantsBulkUpdate` and `productSet` support large-scale variant workflows.
- Current latest docs indicate default per-product variant support at 2048 for these bulk variant workflows.
- Additional resource throttle exists for very large variant stores (50k+ variants -> additional creation caps).
- Implication for Phase 8: structural conflict states must include variant-cap guardrails and bulk mutation path selection.

### 4. Media Ingestion and Sovereignty (Strong Match)
- Official media workflow is file-based: `fileCreate` or `stagedUploadsCreate`, poll readiness (`fileStatus`), then attach media to products/variants.
- File processing is asynchronous and reusable across resources via file IDs.
- Implication for Phase 8: your "download/hash/store/trace then push controlled assets" requirement maps cleanly to Shopify’s file pipeline and should avoid URL passthrough finalization.

### 5. Concurrency-Safe Inventory Writes
- `inventorySetQuantities` supports compare-and-set semantics to prevent clobbering concurrent writes.
- 2026 API versions add/require `changeFromQuantity` semantics and require idempotency for affected inventory mutations.
- Implication for Phase 8: add CAS-safe path for inventory adjustments in apply stage, especially for scheduled batches with delayed execution windows.

### 6. Asynchronous Product Operations
- `productSet` can run asynchronously and return operation IDs; `productOperation` is used for status polling/results.
- Implication for Phase 8: scheduled apply + recovery handling should support async operation tracking in addition to synchronous mutation responses.

## Versioned Compatibility Matrix (Important for Plan 8 Execution)

| Concern | 2025-10 (legacy-latest) | 2026-01 | 2026-04+ | Execution Guidance |
|---|---|---|---|---|
| Inventory CAS field | `compareQuantity` / `ignoreCompareQuantity` | `changeFromQuantity` introduced | legacy CAS fields removed | Prefer `changeFromQuantity` contract now; keep shim only if pinned to older version |
| Inventory idempotency | Optional/limited | Optional via `@idempotent` for affected mutations | Required for affected mutations | Build idempotency-key plumbing in Phase 8 apply engine from day one |
| Product ops async handling | Available | Available | Available | Use async operation polling for heavy `productSet` workloads |
| REST product/media relevance | Legacy | Legacy | Legacy | Keep GraphQL Admin as default path; REST fallback only where unavoidable |

## Mutation Selection Matrix (Phase 8 Apply Strategy)

| Change Type | Preferred Mutation Path | Notes |
|---|---|---|
| Product-level text/tags/options structural edits | `productSet` | Supports holistic updates and async mode for timeout-prone payloads |
| Variant field updates (price/metafields/options) | `productVariantsBulkUpdate` | Supports `allowPartialUpdates`; returns per-call `userErrors` |
| Creating missing variants | `productVariantsBulkCreate` | Use explicit strategy semantics for standalone/default variant behavior |
| File ingestion | `stagedUploadsCreate` + direct upload + `fileCreate` | Required for robust media handling; file lifecycle is async |
| Inventory authoritative set | `inventorySetQuantities` | Use CAS (`changeFromQuantity`) + idempotency key when required |
| Inventory delta adjustment | `inventoryAdjustQuantities` | Prefer when absolute source-of-truth set is not appropriate |

## Failure Taxonomy and Retry Policy (Execution-Ready)

| Failure Class | Example Signal | Retry Policy | Route |
|---|---|---|---|
| Rate-limit pressure | `429`, low throttle headroom | Dynamic backoff from throttle metadata/headers | Continue batch with pacing |
| Transient network | timeout / transport errors | bounded exponential retry + idempotency key reuse | Continue |
| CAS conflict | inventory compare mismatch | refresh current state + re-evaluate rule; do not blind overwrite | conflict review |
| Stale target | product/variant missing at pre-flight | no mutation attempted | `Recovery Logs` |
| Policy exclusion | blocked by negative rule | no retry | dry-run/user decision |
| Media not ready | `fileStatus != READY` | poll-with-timeout before association | continue or item-level fail |
| Validation/business errors | GraphQL `userErrors` | no blind retry | item-level fail + lineage |

## Scheduling and Pre-Flight Control Plane

Minimum safe sequence for scheduled apply:
1. Load approved batch + immutable approval snapshot.
2. Run pre-flight existence check for every target product/variant ID.
3. Split set into `eligible` and `conflicted`.
4. Route conflicted rows to `Recovery Logs` with actionable reason payload.
5. Execute eligible rows under adaptive concurrency.
6. Write per-item and per-field audit lineage.

This sequence enforces your locked requirement that stale/deleted targets are preserved, not silently dropped or force-applied.

## SLO / Guardrail Targets (for Comprehensive Plans)

Recommended initial operational targets:
- Resolution candidate response (single SKU): p95 <= 2.0s (matches roadmap expectation).
- Dry-run materialization (<=500 products): p95 <= 30s.
- Pre-flight verification for scheduled batches (<=500 products): p95 <= 20s.
- Recovery routing latency on stale targets: p95 <= 5s after detection.
- Apply idempotency safety: duplicate-submit mutation side effects == 0.

These are implementation targets to validate in Phase 8 execution and tune via UAT/runtime evidence.

## Standard Stack

### Core
| Library | Version/Status | Purpose | Why Standard Here |
|---------|----------------|---------|-------------------|
| Flask blueprints (`src/api/v1/*`) | Existing | API surface for resolution endpoints | Matches existing auth/error/versioning patterns |
| SQLAlchemy + Alembic migrations | Existing | Durable resolution state, snapshots, rules, logs | Already used for all durable business contracts |
| Celery task routing (`src/tasks`, `src/jobs`) | Existing | Async apply execution and recovery-safe queueing | Already supports tiered queues and cancellation semantics |
| Next.js App Router + React Query | Existing | Dry-run review UX and approval flows | Already in place from Phase 7 foundation |

### Supporting
| Capability | Existing Pattern | Use in Phase 8 |
|-----------|------------------|----------------|
| RFC 7807 error shaping | `src/api/core/errors.py` | Field-level and business conflict responses |
| Job progress/status model | `src/models/job.py`, `src/api/v1/jobs` | Apply lifecycle visibility (`Currently Happening`) |
| Vendor catalog persistence | `src/models/vendor.py` | Supplier-side candidate source |

## Architecture Patterns

### Recommended Resolution Flow

1. `resolve request` -> normalize input keys (SKU/barcode/title/options).
2. Query source adapters in strict order:
   - Shopify local/state data
   - Vendor catalog data
   - Web adapter (only when supplier verified + policy allows)
3. Score candidates + detect structural conflicts (variant/options/schema).
4. Build persisted dry-run batch with field-level proposed changes and reasons.
5. Review/approve at field granularity (with bulk operations).
6. Apply engine performs pre-flight validation, then execute with adaptive throttling.
7. Failures and stale targets route to `Recovery Logs`.

### Persistence-First Governance

Before any Shopify mutation:
- Persist batch manifest snapshot.
- Persist per-product pre-change snapshot for all targeted products.
- Persist explicit approval state (including acting `user_id`).

### Locking Model

Use checkout lock with lease + heartbeat:
- Owner can edit/approve.
- Others read-only.
- Lock expiry allows safe reclaim for abandoned sessions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unstructured approval memory | In-memory approval objects | SQL-backed batch/item/change tables | Prevents data loss, supports audit lineage |
| Ad-hoc conflict handling | Implicit heuristics | Explicit conflict classes (`structural`, `policy`, `stale_target`) | Keeps decisions explainable and testable |
| URL-only image usage | Pass-through vendor URLs | Download + hash + store + trace metadata | Meets asset sovereignty and rollback safety |

## Common Pitfalls

### Pitfall 1: Product-Level Match Without Variant Semantics
- What goes wrong: wrong variant gets updated or missing variant silently ignored.
- Avoidance: variant-aware resolution keys + `Structural Conflict` state when options diverge.

### Pitfall 2: Approved Batch Applied Against Stale Shopify State
- What goes wrong: failed writes, ghost behavior, inconsistent user trust.
- Avoidance: pre-flight existence check immediately before mutation; conflict items diverted to `Recovery Logs`.

### Pitfall 3: Concurrent Review Corrupts Intended Change Set
- What goes wrong: one reviewer overwrites another or approves stale client state.
- Avoidance: single checkout lock + optimistic concurrency tokens for write actions.

### Pitfall 4: Rule Learning Without Negative Constraints
- What goes wrong: auto-rule overreach (e.g., protected pricing domains changed).
- Avoidance: explicit exclusion rules with higher precedence than positive rules.

## Code Examples

### Resolution Adapter Contract (shape)

```python
class ResolutionAdapter(Protocol):
    source: str
    def search(self, query: NormalizedQuery, ctx: ResolutionContext) -> list[Candidate]: ...
```

### Pre-Flight Guard Contract (shape)

```python
def preflight_validate(batch_id: int) -> PreflightReport:
    # Validate Shopify product/variant existence for every target row.
    # Return conflicts; do not mutate on conflict rows.
    ...
```

## Open Questions (To Set in Execution Defaults, Not Blocking Planning)

1. Default critical-error threshold `N` for auto-pause.
   - Recommendation: start with `N=3` and make configurable per store.
2. Lock lease duration and heartbeat interval.
   - Recommendation: 5 min lease, 30 sec heartbeat, 2 misses before reclaim.
3. GraphQL-first mutation set selection for each conflict class.
   - Recommendation: prefer `productSet` for holistic structural updates; use bulk variant mutations for targeted variant waves.
4. API version pin for initial Phase 8 rollout.
   - Recommendation: pin to a single GraphQL Admin version at rollout and encode compatibility shims explicitly in adapter layer.

## Sources

### Primary (HIGH confidence, local authoritative context)
- `.planning/phases/08-product-resolution-engine/08-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `src/models/product.py`
- `src/models/vendor.py`
- `src/api/v1/jobs/routes.py`
- `src/tasks/scrape_jobs.py`
- `frontend/src/features/onboarding/components/OnboardingWizard.tsx`

### Primary (HIGH confidence, external official)
- Shopify API limits: https://shopify.dev/docs/api/usage/limits
- REST Admin API rate limits + legacy notice: https://shopify.dev/docs/api/admin-rest/usage/rate-limits
- Product variants bulk create: https://shopify.dev/docs/api/admin-graphql/2025-01/mutations/productVariantsBulkCreate
- Product variants bulk update: https://shopify.dev/docs/api/admin-graphql/2024-04/mutations/productvariantsbulkupdate
- Product set (sync/async): https://shopify.dev/docs/api/admin-graphql/latest/mutations/productSet
- Product operation polling: https://shopify.dev/docs/api/admin-graphql/2024-07/queries/productOperation
- Media management (fileCreate/stagedUploadsCreate workflow): https://shopify.dev/apps/build/product-merchandising/products-and-collections/manage-media
- Staged uploads payload details: https://shopify.dev/docs/api/admin-graphql/2023-07/payloads/StagedUploadsCreatePayload
- Inventory CAS mutation: https://shopify.dev/docs/api/admin-graphql/2024-10/mutations/inventorySetQuantities
- Inventory concurrency changelog (2026-01 / 2026-04): https://shopify.dev/changelog/concurrency-protection-features
- Inventory CAS syntax change detail: https://shopify.dev/changelog/finalizing-compare-and-swap-redesign-for-inventory-set-quantities
- Current explicit lock behavior (`FOR UPDATE`, `NOWAIT`, `SKIP LOCKED`): https://www.postgresql.org/docs/current/explicit-locking.html

## Metadata

- Standard stack confidence: HIGH (consistent with existing architecture).
- Architecture confidence: HIGH (locked context + external API behavior align).
- Throughput tuning confidence: MEDIUM (policy is correct; concrete per-store budgets should be calibrated in execution/UAT).

**Valid until:** 2026-03-12 (or until Phase 8 execution reveals conflicting runtime constraints).
