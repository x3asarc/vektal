# Phase 11: Product Search & Discovery - Context

**Gathered:** 2026-02-15
**Status:** Ready for research/planning

<domain>
## Phase Boundary

Build the precision workspace for product discovery and bulk catalog operations: multi-field search, advanced filtering, product detail with history/diff, bulk selection/edit, and efficient snapshot lifecycle controls for safe apply.

This phase defines the non-chat operational control surface and safe mutation preparation contracts. It does not replace Phase 8 apply engine or Phase 10 conversational orchestration.

</domain>

<decisions>
## Implementation Decisions (Locked)

### Core UX and Interaction Model
- Workspace model is dual-mode:
  - Grid Edit mode for fast spreadsheet-like operations.
  - Bulk Action Builder mode for semantic operations and policy-safe execution.
- Selection behavior:
  - Selection persists during editing/filtering.
  - Selection becomes immutable snapshot at dry-run generation.
- Fill behavior:
  - Vertical fill is default.
  - Horizontal fill is available as advanced toggle.
- Mobile scope (v1):
  - Mobile/tablet supports read/monitor/approve flows.
  - Full precision grid editing remains desktop-first.

### Approval and Collaboration Semantics
- Approval scope is action-block, with per-product exclude/override within each action block.
- Collaboration model (v1) uses single-editor checkout lock for mutation decisions; non-editors are read-only.
- Real-time multi-user co-edit/cell-locking is deferred to v2.

### Execution and Throughput
- Apply engine uses adaptive chunk size (50-250) and adaptive concurrency (2-5 workers).
- System may switch to Shopify bulk-operation mode above threshold when more efficient.
- Retry policy (transient errors only):
  - Retry classes: 429, 5xx, network timeout.
  - Strategy: exponential backoff + jitter.
  - Max attempts: 5 at chunk level.
  - On exhaustion: move to Recovery Logs for targeted replay.

### Snapshot Lifecycle Policy (Efficient + Safe)
- Full-store snapshot is periodic baseline, not per-apply.
- Every apply batch requires:
  - immutable batch manifest, and
  - touched-product pre-change snapshot.
- Snapshot storage uses hash dedupe with pointer reuse for identical payloads.
- Deterministic recovery chain is mandatory:
  - batch manifest -> product pre-image -> baseline snapshot.
- Dry-run TTL is 60 minutes by default.
- Preflight revalidation is mandatory immediately before apply.

### Data Model Governance
- Protected columns are tiered:
  - System locked: IDs, lineage keys, snapshot references.
  - Guarded edit: sensitive fields requiring elevated confirmation.
  - Regular editable: standard business fields.
- Vendor mapping architecture is versioned per store+supplier+field-group.
  - Flow: supplier raw -> normalized canonical model -> Shopify payload.
  - Unmapped required fields block in dry-run with explicit fix path.
- Alt-text preservation:
  - Preserve existing Shopify alt text by default.
  - Store source alt and generated alt candidates.
  - Overwrite only with explicit user rule/approval.

### Rollback, Audit, and Retention
- Rollback model is 3-layer:
  - in-session undo,
  - post-commit batch rollback,
  - recovery-log replay.
- Audit retention is immutable for 24 months.
- Audit export formats: CSV and JSON.
- Audit payload minimum:
  - batch manifest,
  - per-product diff,
  - actor,
  - timestamps,
  - rule version.

### Non-negotiable Crossovers from External Research Set
- Shopify remains canonical source of truth.
- No mutation without dry-run diff preview.
- Explicit selection scopes (visible/page/filtered/all).
- Semantic bulk operations required (set/add/remove/replace/increase/decrease).
- Protected columns cannot be bulk-overwritten.
- Pre-apply validation and conflict visibility are mandatory.
- Background apply with live progress is mandatory.
- Auto-chunking + adaptive throughput for v1 cap (1000 SKUs).
- Partial failures must route to Recovery Logs.
- Product history + diff + actor audit trail are mandatory.
- Images must be downloaded, hashed, and internally stored.

### Precision Workspace UX Contracts (Locked for Planning)
- Search-and-selection must expose scope explicitly at all times:
  - visible page,
  - all filtered results,
  - explicit checked rows,
  - frozen selection snapshot at dry-run.
- Selection toolbar contract must always show:
  - selected count,
  - total matching set,
  - active scope mode,
  - clear/reset action.
- Bulk action panel must support operation-first edits:
  - set, replace, add, remove, clear,
  - increase/decrease (percent and fixed),
  - conditional set (if blank),
  - find-and-replace (text fields),
  - map-from-column.
- Diff preview contract must be side-by-side per product:
  - before,
  - after,
  - risk/conflict badge,
  - policy/rule reason,
  - per-product exclude override.
- Apply contract must provide deterministic terminal summary:
  - success count,
  - failed count,
  - deferred count,
  - retryable subset,
  - exported recovery payload.

</decisions>

<specifics>
## Specific Ideas

- Precision workspace should preserve spreadsheet speed patterns while adding PIM-grade safety and auditability.
- Kimi-style ASCII preview patterns can be used in specs/prototypes for operator-facing flow validation.
- The control surface should feel "operations-grade": clear blast-radius display, explicit selection scope, and deterministic preflight/dry-run gates before apply.

### External Benchmark Synthesis (Expanded)
- Shopify native bulk editor patterns to reuse:
  - fast table edits and column switching.
  - familiar checkbox-driven selection model.
  - low learning curve for merchants already in Shopify admin.
- Shopify-native gaps to close:
  - no first-class dry-run diff gate before commit.
  - weak rollback/recovery semantics after save.
  - limited pre-apply conflict taxonomy for concurrent catalog changes.
- Marketplace connector patterns to reuse:
  - mapping-centric operation model,
  - channel-aware field transforms,
  - status/tag/SKU filtering at scale.
- PIM patterns (Akeneo/Plytix class) to reuse:
  - operation semantics (add/remove/replace vs raw overwrite),
  - approval workflow hooks,
  - asynchronous job-style execution and logs.
- Spreadsheet patterns to preserve:
  - fill-handle speed,
  - keyboard-first interaction,
  - range edits and bulk apply gestures.
- Spreadsheet risks to explicitly mitigate:
  - silent data corruption from accidental fills,
  - protected field overwrite,
  - weak source-of-truth guarantees.

### End-to-End Precision Workflow (Planning Contract)
1. Discovery and scoping:
   - user builds working set via query + filters.
   - workspace displays products/variants affected and scope mode.
2. Staging in precision grid:
   - user edits via operations or direct cells where allowed.
   - inline schema and policy checks run continuously.
3. Dry-run compilation:
   - latest Shopify state fetched,
   - per-product diffs computed,
   - structural and policy conflicts classified.
4. Approval routing:
   - action-block approval,
   - per-product include/exclude and override where allowed.
5. Safe apply:
   - adaptive chunk/concurrency execution,
   - transient retries,
   - preflight revalidation at execution edge.
6. Post-apply audit:
   - deterministic result summary,
   - downloadable evidence,
   - actor/rule traceability.
7. Recovery loop:
   - failures move into Recovery Logs,
   - retryable failures get one-click replay path,
   - non-retryable failures route to fix queue.

### Error and Conflict Taxonomy (Planning Input)
- Validation errors:
  - type mismatch, required field missing, invalid value domain.
  - handled inline before dry-run complete state.
- Conflict errors:
  - stale data, concurrent update, structural mismatch.
  - handled in dry-run conflict panel with resolve/hold path.
- API/transient failures:
  - 429, timeout, 5xx transport/service failures.
  - handled via bounded retry policy and deferred recovery queue.
- Deferred dependency failures:
  - image ingest failures, mapping gaps, variant dependency issues.
  - handled as partial-batch deferrals with explicit replay or edit actions.

### Minimal Data and API Implications (Planning Input)
- Data structures required:
  - mutable staging set for proposed edits,
  - immutable batch manifest records,
  - per-product pre-image snapshot references,
  - recovery-log entries with replay metadata.
- API behavior required:
  - support both synchronous and background apply modes,
  - provide chunk-progress stream and final aggregate summary,
  - return conflict-classified responses for dry-run and preflight.

### Success Metrics to Carry into Plan/Verification
- Adoption:
  - precision workspace usage share vs legacy paths.
- Speed:
  - time from scoped selection to approved apply.
- Safety:
  - dry-run coverage rate (target 100% for mutating operations),
  - percentage of applies with zero critical conflicts.
- Correction rate:
  - frequency of post-apply fixes,
  - recovery replay success rate.

### V1 vs V2 Boundary (Context Lock)
- V1 must include:
  - precision search/filter/scope workspace,
  - side-by-side dry-run diff gate,
  - action-block approval + per-product overrides,
  - adaptive apply with recovery logs,
  - snapshot lifecycle efficiency model.
- V2 candidates:
  - real-time co-edit/cell locks,
  - predictive AI fill/autocomplete for field suggestions,
  - anomaly detection for suspicious bulk edits.

</specifics>

<discussion_evidence>
## Discussion Evidence

- areas_discussed:
  - precision workspace ux
  - approval semantics
  - execution throughput
  - snapshot lifecycle efficiency
  - retry/recovery policies
  - audit/retention/export
  - protected columns and alt-text data rules
- questions_answered: 13
- user_answers_captured: yes
- external_research_inputs:
  - precisionworkspace.md (Kimi agent mode, Gemini deep research, Grok instant, ChatGPT instant)
  - synthesis_method: consensus lock + outlier adjudication by user decisions

</discussion_evidence>

<deferred>
## Deferred Ideas

- Real-time multi-user cell-locking collaboration (v2 candidate).
- AI-autonomous optimization loops and broader self-learning beyond scoped policy execution (Phase 14 alignment).

</deferred>

---
*Phase: 11-product-search-discovery*
*Context gathered: 2026-02-15*
