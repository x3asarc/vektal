# Phase 10: Conversational AI Interface - Context

**Gathered:** 2026-02-15
**Status:** Context locked, ready for research and planning

<domain>
## Phase Boundary

Build the in-product conversational assistant at `/chat` as the primary operator surface for catalog work.
The assistant must support read + write operations through existing platform systems, always produce a dry-run before mutation, and enforce approval/safety controls before apply.

This phase defines conversational orchestration, approvals, and execution UX contracts; it does not replace Phase 8/9 engines or Phase 14 optimization scope.

</domain>

<decisions>
## Implementation Decisions

### Assistant Role and Operating Model
- Chat is the primary in-product control surface ("muscles of the machine") for store operations.
- The assistant can read from Shopify/platform state and initiate write workflows through existing backend contracts.
- The assistant should orchestrate existing logic/scripts/contracts rather than inventing parallel execution tracks.

### Source Priority and Trust
- Shopify remains source of truth for current store state.
- Priority remains `Shopify -> supplier data -> web`.
- Web discovery/scrape should only run against verified suppliers or user-provided trusted sources.
- When the user supplies new trusted sources during a task, capture them for future workflow policy/rule updates.

### Approval Semantics (Locked)
- Dry-run preview is mandatory before all mutating applies.
- Approval is action-scoped by product:
  - one product with multiple field changes can be approved once at product scope
  - multiple products require per-product decisions, with bulk affordances
- User can approve all, selectively approve/deny specific changes, and leave comments/manual edits before apply.
- Low-risk auto behavior is policy-gated and never bypasses mandatory dry-run visibility.

### Product Create / Update Behavior (Locked)
- Product creation from URL + SKU defaults to `draft` first.
- First create experience uses a structured preference wizard (strategy quiz) so user defines default behavior.
- Quiz decisions are editable later in Settings.

### Memory and Learning Scope (Locked)
- Memory is store/team-oriented by default to improve shared operational performance.
- Team memory must be RBAC-governed for who can view/edit/approve high-impact rules.
- Cross-chat memory persists and powers store-specific preferences (for example SEO writing style and preferred transformations).
- Learning depth/autonomous optimization beyond phase scope remains Phase 14 expansion, but Phase 10 must emit required telemetry/hooks.

### Bulk Throughput and UX (Locked)
- Bulk processing v1 target supports up to 1000 SKUs per request.
- Execution is auto-chunked with queue-based orchestration (user does not choose chunk size by default).
- Chunking/concurrency is adaptive to platform/rate-limit pressure.
- Live progress is mandatory (current stage + running status + queue visibility), including "currently happening" transparency.

### Conflict Handling and Safety (Locked)
- Low-confidence or structural-conflict operations require explicit user decision before apply.
- Snapshot/backups must exist before any mutation; pre-change state is mandatory.
- Recovery path must remain explicit for stale/deleted targets (Recovery Logs).
- Desired SLO direction is effectively 100% safe apply (no silent data loss, no untracked critical conflicts).

### Snapshot Policy (Locked)
- In production, snapshot safety is mandatory and non-disableable.
- No end-user production toggle for disabling snapshots.
- Optional bypass is only acceptable in controlled non-production environments.
- Snapshot strategy is tiered for scale: periodic full-store baseline + per-batch manifest + touched-product pre-change snapshot.
- Snapshot blobs are hash-deduped; unchanged pre-images reuse existing snapshot pointers.
- Recovery traversal must be deterministic: `batch manifest -> product pre-image -> baseline snapshot`.

### Variant Policy (Locked)
- Variant mismatch requires explicit strategy (`ask`, `auto`, `ignore`) captured by quiz/rules.
- First-run default is `ask every time` until supplier/store policy is established.
- If auto-create is enabled, created variants must remain non-selling-safe until explicitly made sellable by user policy/workflow.

### Collaboration and Visibility (Locked)
- Batch checkout/locking remains single-editor for mutation decisions; others are read-only.
- User attribution remains visible (who changed what).
- Activity surfaces should show `Currently Happening` and `Coming Up Next` for team clarity.

### Metrics (Locked for Phase 10)
- Primary success metrics:
  - Time-to-approved-change
  - First-pass dry-run approval rate (without manual edits)
  - Safe apply completion rate (no rollback/critical conflict/data loss)

### Claude's Discretion
- Exact chunk sizing algorithm and adaptive thresholds.
- Exact UI composition for progress timeline, provided contract semantics remain intact.
- Internal representation of chat message blocks if API contract remains deterministic and testable.

</decisions>

<specifics>
## Specific Ideas

- Chat should support prompts like:
  - "Get this product by SKU from this site and create it in my store"
  - "Check these 50/1000 SKUs, identify missing fields, and propose fixes"
- Missing-field completion examples include HS code, weight, and other required commerce fields with provenance.
- For unresolved identifiers/data gaps, system should:
  1. explain what could not be found
  2. accept user-provided source hints
  3. route unresolved gaps into internal feature/backlog visibility when automation is insufficient
- User preference wizard should be typeform-style and explicit (ask/auto/ignore and publish behavior controls).
- Dry-run must show before/after state clearly and keep comments/manual override affordances.

</specifics>

<discussion_evidence>
## Discussion Evidence

- areas_discussed:
  - assistant role and write authority
  - approval semantics and dry-run model
  - memory visibility and store learning scope
  - bulk scale and chunk orchestration
  - conflict/safety and snapshot policy
  - variant mismatch handling and strategy quiz
- questions_answered: 14
- user_answers_captured: yes
- key_user_answers:
  - "Chat is an in-product assistant that can read and write through project logic."
  - "Dry-run is always required before apply."
  - "Approval is per product action scope with selective edits/denies allowed."
  - "Bulk should scale to 1000 SKUs with queue + live progress; user should not tune chunk size."
  - "Creation should default to draft and user preferences are captured by quiz + editable settings."
  - "Team memory should be shared for store benefit."
  - "Low confidence/structural conflict requires user decision and backup safety."
  - "Production snapshot disable should not be allowed."
- captured_on: 2026-02-15

</discussion_evidence>

<deferred>
## Deferred Ideas

- Autonomous source-learning loops, adaptive discovery of new marketplaces, and deeper self-improving behavior are Phase 14 scope.
- Advanced collaborative live co-editing semantics (Google-Docs style) remain out of scope; batch checkout model is preferred.

</deferred>

---

*Phase: 10-conversational-ai-interface*
*Context gathered: 2026-02-15*
