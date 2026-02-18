# Phase 9: Real-Time Progress Tracking - Context

**Gathered:** 2026-02-13  
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver live job progress with clear visual feedback, reliable fallback transport, ETA guidance, and operator-safe retry/error handling.
This phase improves observability and control for existing job workflows; it does not introduce new job types.

</domain>

<decisions>
## Implementation Decisions

### Transport and Delivery
- Primary transport is SSE.
- Fallback ladder is deterministic: `sse -> polling -> degraded`.
- Progress payload contract must be consistent across stream and polling.
- Client must subscribe to named SSE events (`job_{id}`) and not rely on default `message` only.

### Progress Contract
- Every progress payload includes:
  - counters (`processed_items`, `total_items`, `successful_items`, `failed_items`)
  - percent (`percent_complete`)
  - step semantics (`current_step`, `current_step_label`, `step_index`, `step_total`)
  - ETA (`eta_seconds`) when meaningful
  - retry metadata (`can_retry`, `retry_url`)
  - result deep link (`results_url`)
- Backend job list and job detail endpoints expose the same progress fields used by SSE and status polling.

### Step Semantics and UX
- Step transitions are explicit and user-readable.
- Visual states must differentiate `in_progress`, `completed`, `failed`, `cancelled`.
- Dashboard and job detail views should provide consistent status language.

### Error and Retry Semantics
- Retry is allowed only for terminal failed/cancelled states (`failed`, `failed_terminal`, `cancelled`).
- Retry creates a new job and preserves linkage to original (`retry_of_job_id`).
- If an active ingest already exists for the store, retry is blocked with deterministic `409`.

### Notifications and Trust
- Terminal notifications must include outcome details and a navigable job/results link.
- Bursty terminal updates are collapsed for readability, but failures remain sticky.
- Onboarding progress view must reflect live backend state after job creation.

</decisions>

<specifics>
## Specific Ideas

- Reuse existing Phase 5 SSE infrastructure and Phase 6 job state machine; do not create parallel tracking systems.
- Keep progress derivation centralized in a shared backend helper so API routes, stream events, and workers cannot drift.
- Keep ETA conservative and nullable when confidence is low (for example processed count is zero).
- Keep route and component upgrades additive to minimize regression risk.

</specifics>

<deferred>
## Deferred Ideas

- Multi-job timeline analytics, predictive duration modeling, and per-step machine-learning estimates are deferred.
- Full collaborative live editing semantics remain out of scope for this phase.

</deferred>

---

*Phase: 09-real-time-progress-tracking*  
*Context gathered: 2026-02-13*
