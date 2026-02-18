# Phase 10: Conversational AI Interface - Research

**Researched:** 2026-02-15  
**Domain:** Production-grade in-product conversational orchestration for read/write catalog operations with mandatory dry-run safety  
**Confidence:** HIGH (architecture fit), MEDIUM-HIGH (throughput tuning depends on live store/API profiles)

<user_constraints>
## User Constraints (from 10-CONTEXT.md)

### Locked decisions
- Chat is the primary in-product operator surface for store work.
- Assistant is read/write, but writes are always mediated by dry-run + approval.
- Shopify is source of truth; source order remains `Shopify -> supplier -> web`.
- Bulk target is up to 1000 SKUs per request.
- Bulk execution is auto-chunked with queue + live progress.
- Approval semantics are product-action scoped, with selective override/deny possible.
- Low-confidence and structural conflicts require user decision.
- Snapshot safety is mandatory and non-disableable in production.
- Team memory is shared and must be RBAC-governed.

### Deferred / out of scope
- Fully autonomous self-learning source expansion loops (Phase 14+).
- Google-Docs style live co-editing.
</user_constraints>

## Executive Summary

Phase 10 should be built as a **control plane** over already-working execution engines:
- Chat interprets intent and composes actions.
- Resolution (Phase 8) remains the write safety engine.
- Jobs/progress (Phase 9) remain the runtime execution/progress engine.

Deep research outcome: the fastest safe architecture is to add deterministic `/api/v1/chat/*` contracts, persist chat/action lineage, and route all mutating work through existing dry-run/preflight/apply endpoints.

**Critical hard limits from primary sources affect implementation directly:**
- Shopify GraphQL mutation/query cost + throttle status must drive adaptive concurrency.
- GraphQL input arrays are capped at 250, constraining chunk payload construction.
- `productCreate` creates only initial variant and defaults unpublished, which aligns with your draft-first rule.
- SSE has browser connection limits in non-HTTP/2 contexts; chat stream design must avoid opening many parallel streams per tab.

## External Primary-Source Constraints (What changes design)

### Shopify Admin API constraints
1. **GraphQL cost throttle model** (not simple request count) with throttle metadata in `extensions.cost.throttleStatus`.
2. **Single query cost limit** of 1000 points.
3. **Input arrays max size 250**.
4. For stores with large variant counts, Shopify enforces **resource-based throttles** on variant-creating mutations.
5. `productCreate` only creates the initial variant; more variants should use `productVariantsBulkCreate` / related mutations.
6. `productCreate` creates products unpublished by default (publish is separate), which matches draft-first behavior.
7. Bulk operations can reduce client-side pagination/throttle complexity for large read/import workflows and can be monitored via webhook or polling.

### SSE/web transport constraints (MDN)
1. Named events must be consumed with `addEventListener(<eventName>)`; `onmessage` only receives default messages.
2. Reconnect behavior is built-in; explicit error handling is still required.
3. Non-HTTP/2 contexts may hit low per-origin connection limits across tabs (commonly 6), so stream usage must be conservative.

### Celery worker/runtime constraints
1. Worker concurrency and prefetch materially impact fairness/latency under long-running tasks.
2. Retry backoff/jitter options are available and should be explicit for external API calls.
3. Prefetch settings should be tuned for long tasks to avoid starvation and unfair queue reservation.

### Authorization and API error standards
1. OWASP authorization guidance supports deny-by-default, least privilege, per-request checks, and authz test coverage.
2. RFC 9457 obsoletes RFC 7807; your existing ProblemDetails shape is directionally correct but should be aligned to 9457 terminology over time.

## Internal Baseline (what already exists and should be reused)

- Intent classification and handler routing: `src/core/chat/router.py`, `src/core/chat/handlers/*`.
- Resolution safety stack (dry-run/preflight/apply/locks/recovery): `src/api/v1/resolution/routes.py`.
- Job progress + retry + SSE ladder semantics: `src/api/v1/jobs/routes.py`, `src/api/jobs/events.py`, `src/jobs/progress.py`.
- Frontend API error normalization and transport patterns: `frontend/src/lib/api/client.ts`, `frontend/src/features/jobs/hooks/useJobDetailObserver.ts`.
- Chat UI route exists but is currently placeholder: `frontend/src/app/(app)/chat/page.tsx`.

Inference: the project is already 70-80% of the required infrastructure if Phase 10 is implemented as orchestration, not reinvention.

## Recommended Architecture (Production-grade)

### 1) Split by planes
- **Control plane (new in Phase 10):** session/memory, intent, action proposal, approvals, execution requests.
- **Execution plane (existing):** resolution dry-run/apply, jobs, progress, recovery logs.

### 2) Chat state machine
- `at_door`: classify, clarify, propose actions, no mutation execution.
- `in_house`: approved action(s) active; execution and progress tracking allowed.

Transition rules:
- `at_door -> in_house` only when an action proposal is explicitly approved.
- `in_house -> at_door` on completion/cancel or explicit reset.

### 3) Action lifecycle (deterministic)
`drafted -> dry_run_ready -> awaiting_approval -> approved -> applying -> completed|failed|conflicted|partial`

### 4) Persistence model (minimum)
- `chat_session`
- `chat_message`
- `chat_action`
- `chat_action_approval`
- `chat_memory_rule` (RBAC metadata + provenance)

Each record should carry `store_id`, `user_id`, timestamps, and lineage references (`batch_id`, `job_id`, `recovery_log_ids`).

## API Contract Blueprint (recommended)

### Session/message endpoints
- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{id}`
- `GET /api/v1/chat/sessions/{id}/messages`
- `POST /api/v1/chat/sessions/{id}/messages`
- `GET /api/v1/chat/sessions/{id}/stream`

### Approval/execution endpoints
- `POST /api/v1/chat/sessions/{id}/actions/{action_id}/approve`
- `POST /api/v1/chat/sessions/{id}/actions/{action_id}/reject`
- `POST /api/v1/chat/sessions/{id}/actions/{action_id}/apply`

### Response block schema (deterministic rendering)
`blocks[]` types:
- `text`
- `table`
- `diff`
- `action`
- `progress`
- `alert`

Inference: block typing is mandatory to keep frontend predictable for complex bulk outputs.

## Throughput Design for 1000-SKU Requests

### Hard boundaries
- Request cap: 1000 SKUs (product requirement).
- Per mutation payload and list arguments must obey Shopify/GraphQL limits (notably 250 array cap).

### Chunk policy (recommended)
- Normalize/dedupe SKUs first.
- Dynamic chunk size target range: 25-100, hard ceiling 250.
- Start conservative for writes (for example 50) and adapt upward only with healthy throttle headroom.

### Adaptive concurrency policy
- Inputs:
  - `throttleStatus.currentlyAvailable`
  - `throttleStatus.restoreRate`
  - rolling average mutation cost
  - worker capacity and queue depth
- Policy:
  - compute safe parallel budget from available points and reserve floor buffer
  - clamp by admin cap and worker health
  - decrease aggressively on throttle/429; increase gradually on sustained headroom

Inference: adaptive-with-cap is better than fixed worker counts for heterogeneous stores.

## Single-SKU Write Workflow (authoritative path)

1. Parse message (SKU/URL/intent).
2. Resolve current state from Shopify + local context.
3. Build dry-run via Phase 8 endpoint.
4. Render before/after diff + confidence/reasons.
5. User approves at product scope (with optional selective overrides).
6. Preflight immediately before apply.
7. Apply via existing engine.
8. Stream progress + final outcome + recovery references (if any).

No shortcut path should exist around steps 3-6.

## Variant and Product-Create Semantics

- Keep first-run variant policy default at `ask`.
- If user enables auto-create, variants must remain non-selling-safe until policy says otherwise.
- For creation flows:
  - create product draft-first
  - create additional variants through bulk-variant mutations as needed
  - publish only through explicit policy/approval path

Inference from Shopify docs: this aligns with `productCreate` behavior and avoids accidental go-live.

## Memory/RBAC Model (team-shared by default)

### Recommended policy
- Team-shared store memory is default.
- RBAC gates for who can:
  - create/edit memory rules
  - approve high-impact actions (pricing/publish/inventory)
  - bypass warnings (if ever allowed)

### Governance controls
- Deny-by-default permissions.
- Full provenance in memory/rule changes.
- Expiry/versioning for learned rules.
- Audit surfaces for “why this memory was applied.”

## Reliability and Safety Invariants

1. No write without dry-run id.
2. No apply without pre-change snapshot.
3. No low-confidence/structural conflict auto-apply.
4. Every terminal failure yields machine-readable reason and recovery path.
5. Every user-visible error follows ProblemDetails conventions.

About your 100% safe-apply expectation:
- This is best implemented as **invariants + verification gates**, not optimistic metric claims.
- Target outcome is zero silent corruption/data loss and deterministic containment of failures.

## Failure-Mode Matrix (must be planned/tested)

1. Shopify 429 / throttle collapse
- Expected: adaptive backoff + reduced concurrency + progress notice

2. Scheduled apply stale targets
- Expected: preflight catch -> conflict hold -> Recovery Logs link

3. Partial chunk failures in 1000-SKU batch
- Expected: continue safe eligible work, isolate failed/conflicted subset, summarize counts and reasons

4. Stream interruption
- Expected: UI switches to polling/degraded mode without losing action state

5. Duplicate execution request
- Expected: idempotent action guard; same action id cannot apply twice concurrently

## Verification Strategy (deeper than current)

### Contract tests
- Chat API request/response schema invariants.
- Block rendering schema invariants.
- ProblemDetails shape for all expected error classes.

### Workflow tests
- Single-SKU: proposal -> dry-run -> approval -> apply.
- Bulk: 1000 SKUs -> chunking -> adaptive concurrency -> final aggregation.
- Conflict: structural mismatch + low confidence -> forced decision.

### Safety tests
- Snapshot existence before apply enforced.
- Recovery-log creation on stale/deleted targets.
- No mutation when approval absent.

### Load/soak tests
- 1000 SKU mixed workload with realistic API cost behavior.
- Verify queue fairness and bounded memory usage under sustained load.

### Authz tests
- RBAC role matrix for memory edit/approve/apply actions.
- Negative tests for cross-store/session access attempts.

## Plan Impact (required refinements)

1. `10-03` must explicitly encode Shopify constraints:
- chunk payload bounded by API argument limits.
- adaptive concurrency tied to throttle metadata.

2. `10-02` must explicitly encode creation path:
- draft-first create + separate publish semantics.

3. Requirements consistency:
- `CHAT-05` wording must stay aligned to “up to 1000 with auto-chunking.”

4. ProblemDetails reference modernization:
- keep current implementation, but note RFC 9457 supersedes 7807 for future docs cleanup.

## Open Questions (still unresolved)

1. API version target for Shopify integration during Phase 10 execution (`2025-10` vs `2026-01`) impacts bulk-operation concurrency capabilities.
2. Final RBAC role matrix definitions (who can approve publish/pricing at scale).
3. Idempotency key policy for chat apply actions (store-level uniqueness window, replay behavior).
4. Whether bulk read-heavy paths should move to Shopify bulk operations now or in a follow-up optimization sub-plan.

## Sources

### External primary sources
- Shopify API limits: https://shopify.dev/docs/api/usage/limits
- Shopify GraphQL `productCreate`: https://shopify.dev/docs/api/admin-graphql/latest/mutations/productcreate
- Shopify GraphQL `productVariantsBulkCreate`: https://shopify.dev/docs/api/admin-graphql/2025-01/mutations/productVariantsBulkCreate
- Shopify bulk operations (queries): https://shopify.dev/api/usage/bulk-operations/queries
- Shopify bulk operations (imports): https://shopify.dev/api/usage/bulk-operations/imports
- MDN SSE usage: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- MDN EventSource: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- Celery configuration: https://docs.celeryq.dev/en/main/userguide/configuration.html
- Celery optimizing/prefetch: https://docs.celeryq.dev/en/v5.3.4/userguide/optimizing.html
- OWASP Authorization Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- RFC 9457 (Problem Details): https://www.rfc-editor.org/rfc/rfc9457

### Internal sources
- `.planning/phases/10-conversational-ai-interface/10-CONTEXT.md`
- `.planning/phases/08-product-resolution-engine/08-04-SUMMARY.md`
- `.planning/phases/09-real-time-progress-tracking/09-02-SUMMARY.md`
- `src/core/chat/router.py`
- `src/api/v1/resolution/routes.py`
- `src/api/v1/jobs/routes.py`
- `src/api/jobs/events.py`
- `src/jobs/progress.py`
- `frontend/src/app/(app)/chat/page.tsx`
- `frontend/src/lib/api/client.ts`

## Metadata

- Research depth: expanded architecture + protocol + safety + throughput + failure semantics.
- Recommendation: keep Phase 10 as 4-wave delivery, but add strict gate criteria before Wave 3 bulk go-live.
- Valid until: material change in Shopify API constraints or internal Phase 8/9 contract breaks.

## Context7 Deep-Dive Addendum (2026-02-15)

### Why this addendum exists
This section deepens Phase 10 with direct Context7 evidence and translates it into implementation/verification gates.

### Context7 findings translated into engineering rules

#### A) Shopify Admin GraphQL operational rules
1. Bulk operation control endpoints are first-class:
- `currentBulkOperation`
- `bulkOperationRunQuery`
- `bulkOperationRunMutation`
- `bulkOperationCancel`

2. Variant scale behavior:
- For multi-variant creation on existing products, use dedicated variant bulk mutations (`productVariantsBulkCreate`) instead of overloading initial product create paths.

3. Publish semantics:
- Publication is separate from creation flow; keep chat orchestration draft-first by default and publish as explicit follow-up action/policy.

4. Payload safety rule:
- Enforce per-operation list/input bounds in orchestrator before issuing API calls.
- Keep chunk planner hard-cap <= 250 input items per mutation call.

#### B) Celery fairness and reliability rules
1. Long-running chunked workloads should use fairness settings by default:
```python
# Queue profile: chat_bulk
task_acks_late = True
worker_prefetch_multiplier = 1
```

2. Optional fair scheduling mode:
- run worker with `-Ofair` for mixed-duration tasks.

3. Idempotency consequence:
- late ack means tasks may replay after worker loss; every chunk/apply handler must be idempotent and dedupe by action/chunk key.

4. Starvation prevention rule:
- do not use high prefetch settings on chat-bulk workers where chunk duration variance is large.

#### C) Flask streaming rules for chat SSE
1. If stream generator accesses `request`/`session`, wrap with `stream_with_context`.
2. Keep stream responses wrapped in `Response(...)` and enforce anti-buffering/no-cache proxy headers at API edge.
3. Keep one chat-session stream per tab/session to avoid connection pressure.

### Deeper throughput model (practical)

#### 1000-SKU run decomposition
- Input normalize + dedupe first.
- Build chunk plan with dynamic target (25-100) and hard cap 250.
- Execute with adaptive concurrency controller bounded by:
  - API throttle headroom
  - queue depth
  - worker health
  - admin cap

#### Adaptive controller guardrails
- On throttle/429 burst: immediate concurrency reduction + retry backoff.
- On sustained healthy window: gradual step-up only.
- Never increase concurrency and chunk size at the same control interval.

### Go-live acceptance gates (Wave 3 must pass)

1. Safety gates
- 0 untracked writes without dry-run id.
- 0 applies without snapshot reference.
- 100% conflicted/low-confidence items remain approval-gated.

2. Reliability gates
- In a 1000-SKU mixed-duration load test, no worker starvation pattern observed with fairness profile.
- Duplicate/replayed chunk attempts are idempotently handled (no duplicate mutation side effects).

3. Observability gates
- Aggregate and per-chunk progress remain coherent end-to-end.
- Terminal summary reports applied/skipped/conflicted/failed with recovery references.

4. Stream resilience gates
- Simulated stream drop recovers to polling/degraded state without losing action lifecycle state.

### Mandatory plan updates derived from this addendum

- `10-03-PLAN.md`
  - explicitly enforce <=250 mutation payload bound in chunk planner
  - explicitly test throttle-driven concurrency decisions
  - explicitly test fairness/no-starvation under mixed chunk durations

- `10-02-PLAN.md`
  - explicitly test draft-first create and explicit publish gating
  - explicitly route multi-variant expansion through variant bulk mutation path

### Context7 source pointers used in this addendum
- Shopify Admin GraphQL full index (bulk operations):
  https://shopify.dev/docs/api/admin-graphql/2025-07/full-index
- Shopify product variant bulk references:
  https://shopify.dev/docs/api/admin-graphql/2025-07/objects/productvariant
- Shopify publishable interface references:
  https://shopify.dev/docs/api/admin-graphql/2025-07/interfaces/publishable
- Celery optimization and prefetch guidance:
  https://docs.celeryq.dev/en/stable/userguide/optimizing
- Celery configuration reference:
  https://docs.celeryq.dev/en/stable/userguide/configuration.html
- Flask streaming patterns:
  https://flask.palletsprojects.com/en/stable/patterns/streaming/
- Flask `stream_with_context` API:
  https://flask.palletsprojects.com/en/stable/api/
