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

</decisions>

<specifics>
## Specific Ideas

- Precision workspace should preserve spreadsheet speed patterns while adding PIM-grade safety and auditability.
- Kimi-style ASCII preview patterns can be used in specs/prototypes for operator-facing flow validation.
- The control surface should feel "operations-grade": clear blast-radius display, explicit selection scope, and deterministic preflight/dry-run gates before apply.

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

</discussion_evidence>

<deferred>
## Deferred Ideas

- Real-time multi-user cell-locking collaboration (v2 candidate).
- AI-autonomous optimization loops and broader self-learning beyond scoped policy execution (Phase 14 alignment).

</deferred>

---
*Phase: 11-product-search-discovery*
*Context gathered: 2026-02-15*
