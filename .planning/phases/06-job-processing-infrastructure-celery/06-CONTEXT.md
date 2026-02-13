# Phase 6 Context: Job Processing Infrastructure (Celery)

## Objective
Implement a production-safe async job foundation using Celery + Redis where database state is authoritative and task execution is at-least-once tolerant.

## Scope
- In-scope: ingest orchestration, chunk processing, milestone audit dispatch, cancellation, prioritization, observability.
- Out-of-scope: Phase 12 capability routing, Phase 14 ML execution infrastructure, advanced multi-tenant fairness beyond tier/store lock.

## Locked Product Decisions
1. Phase 6 starts with Shopify catalog ingest (`A`).
2. Audit (`B`) trigger policy:
   - If store has <1000 products: run at 25,35,45,55,65,75,85,95,100 percent.
   - If store has >=1000 products: run once at 100 percent.
3. Auto-create enrichment jobs (`C`) is excluded unless manually approved.

## Reliability Principles
- Database is source of truth for progress and emission state.
- Celery is execution engine and may duplicate/retry work.
- Exactly-once outcomes are achieved by idempotency keys + unique constraints + transactional state transitions.
- Cooperative cancellation preferred; hard termination is last resort.

## Queueing Model (Phase 6)
Functional + tiered routing, explicit capacity allocation:
- `interactive.t1`, `interactive.t2`, `interactive.t3`
- `batch.t1`, `batch.t2`, `batch.t3`
- `control`

Notes:
- Prioritization is primarily enforced by worker allocation and queue isolation.
- Redis priority integers may be used as secondary signal only.

## Data Model Contract

### 1) `ingest_chunks`
Purpose: chunk idempotency, claim/reclaim, completion gating.

Required fields:
- `job_id` (fk jobs)
- `store_id`
- `chunk_idx`
- `status` (`pending|in_progress|completed|failed_terminal`)
- `claim_token` (optional but recommended)
- `claimed_at`
- `attempts`
- `processed_expected`
- `processed_actual`
- `product_ids_json` (frozen chunk membership for MVP)
- `completed_at`
- `last_error`

Constraints/invariants:
- `UNIQUE(job_id, chunk_idx)`
- `processed_actual <= processed_expected`
- if `status = completed` then `completed_at is not null`

### 2) `audit_checkpoints` (Outbox)
Purpose: durable checkpoint emission and broker-failure tolerance.

Required fields:
- `job_id` (fk jobs)
- `store_id`
- `checkpoint` (int: 25,35,...,100)
- `dispatch_status` (`pending_dispatch|dispatched`)
- `dispatch_attempts`
- `next_dispatch_at`
- `dispatched_at`
- `last_error`

Constraints:
- `UNIQUE(job_id, checkpoint)`

### 3) `jobs` additions/guards
- `CHECK(processed_count >= 0 AND processed_count <= total_products)`
- Active ingest lock scoped to ingest-class jobs only:
  - unique active ingest per store where `job_type='INGEST_CATALOG'` and status in `queued|running|cancel_requested`.

## State Machines

### Chunk state
`pending -> in_progress -> completed` (or `failed_terminal`)

Claim/reclaim rule:
- Claim when `status='pending'`, or reclaim only when `status='in_progress'` and stale (`claimed_at` older than `STALE_AFTER`).
- Never reclaim `completed` or `failed_terminal` rows.
- `attempts` increments only on a successful claim/reclaim transition (recommended semantics for Phase 6).
- On claim: set `in_progress`, assign `claim_token`, increment attempts.

Completion rule (single transaction):
1. Transition chunk `in_progress -> completed` guarded by status and claim token.
2. If rowcount=1:
   - increment `jobs.processed_count += processed_actual`
   - read authoritative post-increment `jobs.processed_count` from DB
   - compute crossed milestones from DB state + locked policy:
     - `<1000`: 25,35,45,55,65,75,85,95,100
     - `>=1000`: 100 only
   - upsert `audit_checkpoints` as `pending_dispatch`
3. If rowcount=0: no-op retry (already completed/not owned).

### Checkpoint outbox state
`pending_dispatch -> dispatched`

Dispatcher handles retries by updating `dispatch_attempts`, `next_dispatch_at`, `last_error`.
No terminal dispatch-failed state in Phase 6.
Dispatcher must claim rows before publish using `FOR UPDATE SKIP LOCKED` and increment `dispatch_attempts` while holding the lock, then publish, then mark `dispatched`.

### Cancellation state
`queued|running -> cancel_requested -> cancelled`

Rules:
- No new chunks claimed once cancel requested.
- In-progress chunks exit at safe points.
- Revoke queued-not-started tasks as best effort.
- Remaining `pending` chunks are transitioned to terminal `failed_terminal` with a cancellation-specific reason code (schema-minimal approach for Phase 6).

### Job finalizer state
`running -> completed|failed_terminal` and `cancel_requested -> cancelled`

Terminal chunk states for finalizer logic are `completed` and `failed_terminal`.

Finalization rules:
- `running -> completed` when:
  - all `ingest_chunks` are terminal, and
  - no due `audit_checkpoints` remain (due = `dispatch_status='pending_dispatch'` and (`next_dispatch_at IS NULL OR next_dispatch_at <= now()`)).
- Completion mode depends on policy:
  - strict mode: all chunks must be `completed`
  - lenient mode: allow some `failed_terminal` chunks
- `running -> failed_terminal` when terminal failure policy is met.
- `cancel_requested -> cancelled` when:
  - no chunks are `in_progress`, and
  - no pending chunks remain claimable (or are transitioned to `failed_terminal` with a cancellation-specific reason code).

Finalizer execution points:
- opportunistically after chunk completion,
- opportunistically after dispatcher cycles,
- optional periodic sweep can be added later.

## Task Contracts

### `start_ingest(job_id, store_id, user_id)`
- Validate active-ingest guard.
- Fetch total products and freeze ordered membership.
- Create chunk rows (`pending`) and enqueue chunk tasks.

### `ingest_chunk(job_id, store_id, chunk_idx)`
- Claim chunk (stale-aware).
- Read frozen membership from `ingest_chunks.product_ids_json` for that chunk.
- Never re-query Shopify to decide chunk membership on retries.
- Upsert products idempotently.
- Compute `processed_actual`.
- Commit chunk completion transaction.

### `dispatch_pending_audits()`
- Poll pending rows (`FOR UPDATE SKIP LOCKED`).
- Enqueue `audit_run(job_id, checkpoint)`.
- Mark dispatched or schedule retry via backoff.

### `audit_run(job_id, checkpoint)`
- Audit ingested subset so far only.
- Idempotent write keyed by `(job_id, checkpoint)`.

## Freeze Membership Rule
Chunk membership is frozen at ingest start and reused on retries.
MVP storage: persist frozen membership directly on each `ingest_chunks` row via `product_ids_json`.
Do not recompute chunk boundaries dynamically during retries.
If row payload size becomes a concern for very large stores, migrate membership storage to pointer-based object storage in a later phase.

## Worker/Runtime Defaults (Initial)
- `worker_prefetch_multiplier=1`
- `task_acks_late=True` (tasks must remain idempotent)
- Chunk default size: 100
- `STALE_AFTER`: 10 minutes (tune with observed chunk runtime)
- Dispatcher cadence: 10 seconds
- Dispatcher batch size: 50

## Failure Handling
- Product writes must be retry-safe (`ON CONFLICT DO UPDATE/DO NOTHING` as appropriate).
- Progress is derived only from committed chunk transitions.
- Outbox ensures checkpoint dispatch survives temporary broker failures.

## Observability
- Flower enabled with worker events.
- Track queue depth, task latency, chunk claim age, pending_dispatch backlog, and job staleness.

## Open Decisions Before Implementation
1. Initial worker concurrency split across `interactive` and `batch` pools.
2. Strict vs lenient terminal failure policy for ingest (any failed chunk vs threshold).

## Implementation Order (Recommended)
1. Schema changes (new tables + constraints + lock guard).
2. Celery routing and worker split.
3. `start_ingest` + chunk claim/complete path.
4. Checkpoint outbox + dispatcher.
5. Cooperative cancellation wiring.
6. Metrics and operational alerts.
