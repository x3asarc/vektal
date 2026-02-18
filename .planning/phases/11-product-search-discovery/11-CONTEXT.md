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

### Precision Runtime Contracts (Expanded)
- Admission controller is mandatory between staging edits and apply:
  - schema validation,
  - policy validation,
  - conflict classification,
  - commit eligibility gate.
- Mutation execution mode switches by scope and complexity:
  - smaller sets may run synchronous mutation path,
  - large sets use staged uploads + background bulk mutation workflow,
  - selection scope and complexity drive mode choice.
- Throughput control follows adaptive AIMD behavior:
  - additive increase while healthy,
  - multiplicative decrease on throttle (429),
  - bounded worker and chunk guardrails to avoid API lockout.
- Progress contract is explicit and operator-visible:
  - processed/total,
  - ETA,
  - current item/chunk,
  - live log stream,
  - cancel remaining action.
- Conflict resolution contract includes four explicit user actions:
  - skip,
  - force apply,
  - merge non-conflicting fields,
  - review in side-by-side diff.
- Recovery contract is actionable, not archival-only:
  - deferred/failed rows become a replayable work queue,
  - retry-eligible rows support one-click re-apply after fix,
  - non-retryable rows require targeted remediation with reason codes.

### Deep Architecture Recommendations (Locked)
- Vendor field mapping architecture:
  - versioned per `store + supplier + field_group`,
  - deterministic transform pipeline from supplier raw -> canonical -> Shopify payload,
  - required-field mapping gaps block dry-run completion.
- Dry-run TTL architecture:
  - default TTL is 60 minutes,
  - stale previews require revalidation before apply,
  - stale state must be surfaced with explicit UI badge and blocked blind apply.
- Retry logic architecture (transient only):
  - retry classes: 429, timeout, 5xx,
  - exponential backoff + jitter,
  - bounded attempts and deferred handoff to Recovery Logs.
- Audit retention/export architecture:
  - immutable 24-month retention,
  - export formats CSV + JSON,
  - payload includes actor, reason, rule version, per-product diff, timestamps.
- Protected column architecture:
  - enforced at UI, API, and persistence layers,
  - protected/system columns cannot be filled, bulk-overwritten, or formula-propagated.
- Alt-text preservation architecture:
  - existing Shopify alt text preserved by default,
  - generated/source candidates tracked with provenance,
  - overwrite requires explicit rule or action-level approval.

### Error Taxonomy Contract (Planning Seed)
- Validation class:
  - invalid domains (negative price, type mismatch, required missing),
  - blocks preview completion until fixed or excluded.
- Conflict class:
  - stale snapshot/concurrent mutation/structural mismatch,
  - routes to merge/force/skip/review actions.
- Platform/transient class:
  - throttle/timeouts/service failures,
  - auto-retry under bounded policy.
- Deferred dependency class:
  - image ingest failure, mapping dependency, variant dependency constraints,
  - moved to Recovery Logs with replay metadata.
- Unexpected/system class:
  - operation paused safely,
  - failure reason preserved and operator notified with next action.

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

### Precision Interaction Blueprint (Expanded)
- Workspace layout baseline:
  - search bar + filter builder,
  - scope-aware selection toolbar,
  - editable grid with locked/protected columns,
  - bulk action panel,
  - dry-run preview modal/page,
  - apply monitor and results/recovery view.
- Selection semantics:
  - explicit scopes: page, filtered result set, explicit checked rows,
  - persistent selection under filter changes,
  - immutable selection snapshot when dry-run is generated.
- Bulk operations grammar:
  - set,
  - add,
  - remove,
  - replace,
  - clear,
  - increase/decrease (percent/fixed),
  - conditional set (if blank),
  - find/replace,
  - map-from-column.
- Grid ergonomics (desktop-first precision mode):
  - keyboard-first navigation,
  - fill handle (vertical default, horizontal optional),
  - pattern-aware fill with confirmation on ambiguous patterns,
  - protected fields visually distinct and non-fillable.
- Dry-run preview ergonomics:
  - side-by-side before/after,
  - risk/conflict badges,
  - per-product include/exclude,
  - export preview for offline review.
- Apply monitor ergonomics:
  - live progress and ETA,
  - active chunk/item indicator,
  - background continuation option,
  - deterministic terminal summary and recovery handoff.

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

### Minimal Entity Contract (Expanded for Planning)
- `bulk_operation`:
  - operation state machine (drafting -> previewing -> preview_ready -> applying -> completed/deferred/failed/cancelled),
  - selection scope snapshot,
  - operation config and risk metadata.
- `product_snapshot`:
  - product pre-image at scope freeze,
  - snapshot timestamp and lineage reference.
- `preview_result`:
  - per-product before/after,
  - conflict and warning classification,
  - preview generation timestamp and TTL marker.
- `apply_result`:
  - chunk-level outcomes,
  - processed/success/deferred/failed counters,
  - started/completed timestamps.
- `recovery_log`:
  - deferred/failed action record,
  - retry eligibility,
  - reason code/message,
  - replay payload pointer.
- `stored_image_asset`:
  - source URL provenance,
  - content hash and dedupe key,
  - internal storage reference and media metadata.

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
  - synthesis_method: consensus lock + outlier adjudication by user decisions + architecture uplift from multi-model overlap
- canonical_contract_definitions:
  - `.planning/phases/11-product-search-discovery/GOV_REL_GLOSSARY.md`

</discussion_evidence>

<deferred>
## Deferred Ideas

- Real-time multi-user cell-locking collaboration (v2 candidate).
- AI-autonomous optimization loops and broader self-learning beyond scoped policy execution (Phase 14 alignment).

</deferred>

---
*Phase: 11-product-search-discovery*
*Context gathered: 2026-02-15*
