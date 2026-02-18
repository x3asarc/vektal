# Phase 9: Real-Time Progress Tracking - Research

**Researched:** 2026-02-13
**Domain:** SSE-first job progress delivery, fallback resilience, ETA/retry semantics, and operator-facing UI trust
**Confidence:** HIGH (internal architecture fit), MEDIUM (ETA precision tuning requires runtime calibration)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
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

### Claude's Discretion
No `Claude's Discretion` section was provided in `09-CONTEXT.md`.

### Deferred Ideas (OUT OF SCOPE)
## Deferred Ideas

- Multi-job timeline analytics, predictive duration modeling, and per-step machine-learning estimates are deferred.
- Full collaborative live editing semantics remain out of scope for this phase.
</user_constraints>

## Summary

Phase 9 should be implemented as a contract-hardening phase, not a transport rewrite. The codebase already has SSE endpoints, polling fallback, and lifecycle state machinery from Phases 5-7; the critical gap is that payload semantics (step, ETA, retryability) are inconsistent across endpoints and UI consumers.

The best implementation path is additive and low-risk:
1. Introduce a shared backend progress payload builder.
2. Emit that payload from stream, polling, list/detail APIs, and lifecycle transition points.
3. Upgrade frontend observer to named-event SSE handling with the existing fallback ladder preserved.
4. Add guarded retry endpoint semantics and surface retry UI only for retryable states.

**Primary recommendation:** Standardize a single progress contract in backend and make every producer/consumer use it; do not let SSE, polling, and list/detail drift.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask `Response` streaming | Existing app stack | SSE stream endpoint | Native streaming support, no broker required |
| Browser `EventSource` | Web standard | Real-time client updates | Built-in reconnect behavior, simple one-way progress channel |
| SQLAlchemy models (`Job`) | Existing app stack | Authoritative counters and state | Already canonical source for job lifecycle |
| Celery tasks/workers | Existing app stack | State transitions and background processing | Existing orchestration/finalizer pipeline already in place |
| Next.js App Router + React | Existing app stack | UI surfaces (jobs, onboarding, dashboard) | Existing feature modules can be upgraded in-place |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TanStack Query | existing (`^5.90.5`) | Polling/fetch cache integration where needed | Polling fallback and rehydrate paths |
| Zustand | existing (`^5.0.8`) | Cross-page local pending/notification state | Global tracker and terminal toast state |
| Problem Details normalization | existing internal utility | Retryability and severity hints in UI | Error UX and deterministic action gating |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SSE-first | WebSockets-first | Higher complexity and stateful infra without clear one-way progress benefit |
| Derived ETA from job model | External metrics pipeline ETA | Better long-run prediction but overkill for current phase scope |
| Retry by mutating same job row | Retry as new job row | In-place mutation obscures audit lineage and terminal history |

**Installation:**
```bash
# No new dependencies required for Phase 9 scope.
```

## Architecture Patterns

### Recommended Project Structure
```text
src/
|-- jobs/
|   |-- progress.py        # canonical payload builder + broadcast helper
|   |-- orchestrator.py    # emits progress at queue/chunk milestones
|   |-- finalizer.py       # emits terminal transitions
|   `-- cancellation.py    # emits cancel-request transition
|-- api/
|   |-- jobs/events.py     # SSE + polling endpoints consuming shared payload
|   `-- v1/jobs/routes.py  # list/detail/retry endpoints consuming shared payload
frontend/src/
|-- features/jobs/hooks/useJobDetailObserver.ts
|-- app/(app)/jobs/[id]/page.tsx
`-- features/onboarding/components/OnboardingWizard.tsx
```

### Pattern 1: Canonical Progress Payload Builder
**What:** A single backend function computes all progress fields (`percent`, step, ETA, retryability, links).  
**When to use:** Every endpoint/event that returns job progress semantics.  
**Example:**
```python
def build_progress_payload(job: Job) -> dict[str, Any]:
    # counters, percent, current step, eta_seconds, can_retry, links
    ...
```

### Pattern 2: SSE Named-Event Subscription + Fallback Ladder
**What:** Subscribe to `job_{id}` event channel and keep deterministic fallback (`sse -> polling -> degraded`).  
**When to use:** Job detail and onboarding progress views.  
**Example:**
```ts
const source = new EventSource(streamUrl, { withCredentials: true });
source.addEventListener(`job_${jobId}`, (event) => {
  const payload = JSON.parse((event as MessageEvent).data);
  setJob(payload);
});
```

### Pattern 3: Retry as New Job (Linked Lineage)
**What:** Retry creates a new job row with `retry_of_job_id`, keeps old terminal job immutable.  
**When to use:** Failed/cancelled terminal states.  
**Example:**
```python
retry_job = Job(..., parameters={"retry_of_job_id": original.id, ...})
```

### Anti-Patterns to Avoid
- **Per-endpoint payload shaping:** Causes frontend drift and inconsistent UX.
- **ETA hardcoding:** Produces false precision and trust loss.
- **Retrying active/completed jobs:** Violates lifecycle semantics and can duplicate work.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| One-way progress streaming | Custom websocket hub | SSE with Flask streaming + EventSource | Lower operational complexity, native browser support |
| Retry eligibility | Frontend-only guess logic | Backend-enforced retryability + `409` contracts | Prevents race/integrity bugs |
| Step labels in multiple places | Manual UI maps per page | Backend `current_step_label` in payload | Avoids semantic drift and localization mismatch |
| Notification queue semantics | New event bus | Existing global job tracker + policy collapse | Reuses tested behavior and minimizes regressions |

**Key insight:** The main risk is contract fragmentation, not transport capability.

## Common Pitfalls

### Pitfall 1: Listening only to `onmessage` for named SSE events
**What goes wrong:** UI never updates even though server emits `event: job_123`.  
**Why it happens:** `EventSource.onmessage` handles only default message events; named events require `addEventListener`.  
**How to avoid:** Subscribe to `job_{id}` explicit event name and keep polling fallback.  
**Warning signs:** Stream connection is open but no job state changes in UI.

### Pitfall 2: ETA oscillation and trust erosion
**What goes wrong:** ETA jumps wildly or shows nonsense values.  
**Why it happens:** Computing ETA before stable throughput exists (e.g., processed count = 0).  
**How to avoid:** Emit nullable ETA until enough signal exists; show "calculating" state in UI.  
**Warning signs:** ETA moves from seconds to hours repeatedly.

### Pitfall 3: Retrying wrong lifecycle states
**What goes wrong:** Duplicate active jobs or invalid recovery actions.  
**Why it happens:** Retry gating is incomplete or only in frontend.  
**How to avoid:** Backend-enforced state gate + active-ingest uniqueness guard + deterministic `409`.  
**Warning signs:** Multiple active ingest jobs for same store.

### Pitfall 4: Producer drift across stream/polling/list/detail
**What goes wrong:** One page shows retry available, another does not.  
**Why it happens:** Different code paths shape progress payload separately.  
**How to avoid:** Centralize payload builder and call from all producers.  
**Warning signs:** Snapshot mismatch between `/stream`, `/status`, `/jobs`, `/jobs/{id}`.

## Code Examples

Verified patterns from official sources and aligned with repo architecture:

### SSE response shape in Flask
```python
return Response(
    generate(),
    mimetype="text/event-stream",
    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
)
```
Source: Flask streaming pattern + SSE event-stream content type docs.

### Named SSE event format
```text
event: job_123
data: {"status":"running","processed_items":42}

```
Source: MDN SSE event stream format.

### Client subscription for named events
```ts
const es = new EventSource("/api/v1/jobs/123/stream", { withCredentials: true });
es.addEventListener("job_123", (event) => {
  const payload = JSON.parse((event as MessageEvent).data);
  render(payload);
});
```
Source: MDN `EventSource` + named event listener usage.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Ad-hoc per-route status objects | Canonical progress contract across all producers | Phase 9 design decision | Eliminates UI semantic drift |
| Generic `onmessage` SSE parsing | Named-event subscription with fallback ladder | Current browser API best practice | Reliable updates for event-scoped streams |
| Retry as implicit "rerun" action | Retry as explicit new job with linkage | Modern audit-safe workflow pattern | Better traceability and safer operations |

**Deprecated/outdated:**
- Treating SSE and polling payloads as separate schemas is an anti-pattern for this phase.

## Open Questions

1. **Step inference source of truth**
   - What we know: Step semantics are required and user-facing.
   - What's unclear: Whether step transitions should be purely derived from progress percentage or explicitly set in orchestration transitions.
   - Recommendation: Start with explicit transition hints in orchestrator/finalizer and fallback inference in payload builder.

2. **ETA smoothing policy**
   - What we know: Raw instantaneous ETA can jitter.
   - What's unclear: Required smoothing aggressiveness for UX.
   - Recommendation: Keep ETA conservative/nullable in Phase 9; introduce EWMA smoothing only if UAT flags instability.

3. **Terminal notification retention window**
   - What we know: Bursty collapse + sticky failures are required.
   - What's unclear: Optimal TTL and list cap under heavy usage.
   - Recommendation: Keep current defaults, capture telemetry in Phase 10+ for tuning.

## Sources

### Primary (HIGH confidence)
- Phase and constraints:
  - `.planning/phases/09-real-time-progress-tracking/09-CONTEXT.md`
  - `.planning/ROADMAP.md` (Phase 9 section)
  - `.planning/REQUIREMENTS.md` (`PROGRESS-01..07`)
- Existing implementation anchor points:
  - `src/api/core/sse.py`
  - `src/api/jobs/events.py`
  - `src/jobs/orchestrator.py`
  - `src/jobs/finalizer.py`
  - `src/jobs/cancellation.py`
  - `frontend/src/features/jobs/hooks/useJobDetailObserver.ts`
- Official docs:
  - MDN EventSource API: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
  - MDN Server-sent events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
  - Flask streaming patterns: https://flask.palletsprojects.com/en/stable/patterns/streaming/
  - Celery task retry/backoff options: https://docs.celeryq.dev/en/stable/userguide/tasks.html#automatic-retry-for-known-exceptions

### Secondary (MEDIUM confidence)
- Celery configuration reference (cross-check for retry/backoff knobs): https://docs.celeryq.dev/en/stable/userguide/configuration.html

### Tertiary (LOW confidence)
- None. No unverified claims retained.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Fully aligned to already-adopted stack; no speculative tooling.
- Architecture: HIGH - Requires additive hardening only, not platform shifts.
- Pitfalls: HIGH - Verified against browser/flask/celery docs and current code paths.
- ETA strategy: MEDIUM - Final user-perceived quality depends on runtime throughput patterns.

**Research date:** 2026-02-13  
**Valid until:** 2026-03-15 (or until job lifecycle model changes materially)
