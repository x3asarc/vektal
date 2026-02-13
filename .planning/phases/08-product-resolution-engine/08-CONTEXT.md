# Phase 8: Product Resolution Engine - Context

**Gathered:** 2026-02-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement intelligent product lookup across Shopify, supplier data, and web, then produce dry-run previews before apply.
This phase defines resolution behavior and user-governed change rules; it does not expand scope into unrelated capabilities.

</domain>

<decisions>
## Implementation Decisions (Locked So Far)

### Source Priority and Trust
- Shopify is source of truth.
- Default source priority is: Shopify -> supplier data -> web.
- Web source is only eligible when supplier sources are verified by user.

### Conflict Handling Policy
- If Shopify and external sources differ: apply user-consented profile rules automatically where defined; otherwise require explicit approval.
- True tie between top candidates must never auto-pick; require user selection.

### Auto-Resolve Strictness
- Auto-resolve is allowed for exact and high-confidence normalized matches, with policy checks.
- Medium-confidence auto-resolve is not allowed by default.

### User Rule Profiles
- User can define profile-level field behavior for supplier-to-store differences (for example: images, barcode, SKU, description, audience).
- User must explicitly consent to auto-apply these rules.
- These rules are applied in dry-run for future CSV imports.
- Rule management is available in Settings and can be changed later.
- Initial rule setup is offered during onboarding but is not required to use the platform.

### Supplier and Policy Onboarding (Locked)
- Unknown suppliers are detected at CSV upload and trigger verification before processing.
- Verification proof level is confirmation plus a 1-3 field sample mapping check.
- Auto-apply consent scope is per supplier plus per field group (`images`, `text`, `pricing`, `ids`).
- If no consented rules exist, every changed field requires explicit approval.
- Manual overrides during dry-run are tracked to generate rule suggestions.

### Dry-Run UX and Approval Semantics (Locked)
- Default dry-run grouping is by product (Shopify catalog-centered review).
- Approval granularity is per field with bulk actions available.
- Rule suggestion prompts are batched at end of dry-run, and also available in Settings inbox.
- User can choose suggestion behavior/defaults on first batch; preference is saved for future batches.
- Apply mode supports both immediate and scheduled execution per batch.
- For scheduled mode, timing should support off-peak execution for large updates.

### Safety, Rollback, and Audit Controls (Locked)
- Pre-change snapshot scope is both:
  - batch manifest snapshot
  - per-product pre-change snapshot
- Rollback default is auto-rollback on critical apply failures.
- Non-critical item-level failures should be isolated/flagged, not force full-batch rollback.
- Audit logs must be user-visible at per-product and per-field granularity.
- Audit entries must include rule attribution and reason trace for trust/debugging.
- Image storage behavior is persistent with:
  - hash-based deduplication
  - original source trace metadata

### Execution and Throughput Policy (Locked)
- Batch apply concurrency is adaptive to available rate-limit budget (including `X-Shopify-Shop-Api-Call-Limit` signals).
- Rate-limit handling uses dynamic backoff based on response headers/signals.
- Long-batch auto-pause triggers when critical errors exceed a configured threshold `N` (default policy band, not first error).
- For scheduled apply conflicts where catalog changed since dry-run:
  - re-run dry-run for conflicted items only
  - avoid full-batch re-run unless conflict scope expands materially.
- Pre-flight validation runs immediately before apply (target within 60 seconds of first mutation call).
- Pre-flight validation performs 1:1 existence checks for target Shopify product/variant IDs.
- Targets missing/deleted since approval are not pushed and are preserved in `Recovery Logs` with actionable restore metadata.
- Active dry-run review sessions are checked out to one user at a time (batch locking).

### Structural and Variant Policy (Locked)
- Resolution must evaluate product + variant structure (SKU/barcode/options), not title-only matching.
- If supplier data introduces variants not present in Shopify, mark as `Structural Conflict: New Variants Detected`.
- Product type/option-schema mismatches must enter a `Structural Review` state before apply.
- Default behavior is explicit approval required before creating missing variants.
- User can opt into auto-create missing variants per supplier/profile rule from Settings.
- For SKU variant mismatch (for example Shopify has `Red` only, supplier has `Red` + `Blue`), system must ask whether new variant(s) are desired.
- Safe default for newly created variants is non-live state (`draft` and/or zero inventory) until publish conditions are met.
- If supplier row maps to no Shopify product, route through `Draft New Product` flow rather than in-place update.

### Multi-User Collaboration Integrity (Locked)
- Manual overrides and approvals are always attributed to `user_id`.
- Non-lock owners can view a batch but cannot edit/approve while lock is active.
- UI should show clear lock ownership and active work indicators to avoid ambiguous ownership.

### Negative Constraints and Exclusion Rules (Locked)
- Preference store must support exclusion rules (for example: never auto-change price for selected collections/tags/vendors).
- Exclusion rules override positive auto-apply rules.
- Dry-run must explain when a proposed change was blocked by an exclusion rule.

### Explainability and Trust Controls (Locked)
- Dry-run row reasons are shown as human-readable sentences per change.
- Advanced/technical trace should remain available behind a power-user details toggle.
- Confidence display is numeric score + badge + reason factors.
- Rule-learning acceptance default is supplier-scoped with editable expiry/disable controls.
- "Why changed?" drill-down supports full historical lineage:
  - all batches
  - manual overrides
  - rule version history

</decisions>

<specifics>
## Specific Ideas

- Dry-run should clearly show diff + reason for each field decision.
- The system should learn/store each account's preferred transformation behavior for supplier deltas and reuse it when consented.
- Dry-run comparison table behavior:
  - auto-applied by rule marked as completed
  - proposed changes marked as awaiting approval
  - manual edits feed rule-learning suggestions
- Settings/onboarding includes a structured supplier strategy questionnaire (quiz/typeform style) to capture tight, machine-actionable preferences.
- Questionnaire examples include:
  - behavior for new variants on matched products (`create as draft`, `ignore`, `ask every time`)
  - behavior for scraping supplier variants (`all variants` vs `base product only`)
- Collaboration UX should prefer co-presence indicators + locking over Google-Docs-style live co-editing for lower complexity and clearer ownership.
- Add two visibility surfaces:
  - `Currently Happening` for active dry-runs and in-progress apply jobs
  - `Coming Up Next` for approved scheduled batches waiting to execute
- User-attributed visual cues (for example color-coded audit/history) should make ownership obvious without enabling concurrent write conflicts.
- Audit trace should make "Why changed?" explicit as lineage: `Batch -> Rule Version -> User ID/Color Attribution`.
- Confidence display should include numeric score + badge with reason factors (for example SKU match, title match).

## Non-Negotiable Requirements

- All files/data snapshots must be saved before any apply operation makes changes.
- The relevant product set being changed must always have current pre-change state persisted in PostgreSQL before mutation.
- System should maintain full-state availability, while guaranteeing strong snapshot fidelity for affected products in each batch.
- Images are special-case data:
  - image assets must be downloaded and stored/processed as files
  - URL-only image link persistence is not sufficient
  - final Shopify push must use controlled ingested asset source, not external vendor URL directly
- When approved work cannot be applied due to stale/deleted Shopify targets, preserve the payload and decision context in `Recovery Logs`.

## Data Lifecycle Note

- Enrichment/vectorization can run as a second-tier effect (post-live or async follow-up), and does not need to block first push from vendor scrape.
- Phase 8 should preserve/emit enough traceable state so later enrichment and embeddings can be layered safely.

</specifics>

<deferred>
## Deferred Ideas

- Full downstream embedding/vector enrichment policy tuning is deferred to later optimization/search-focused phases, while Phase 8 keeps compatibility hooks.

</deferred>

---

*Phase: 08-product-resolution-engine*
*Context gathered: 2026-02-12*
