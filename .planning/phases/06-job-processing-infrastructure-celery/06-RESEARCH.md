# Phase 6: Job Processing Infrastructure (Celery) - Research

**Researched:** 2026-02-10
**Domain:** Async job orchestration with Celery + Redis + PostgreSQL in Flask
**Confidence:** HIGH

## Summary

Phase 6 requires moving from placeholder/background capability to production-safe orchestration where Celery executes work, but PostgreSQL remains the authoritative state machine for progress, checkpoints, and cancellation. The existing codebase already has a Celery app (`src/celery_app.py`) and a Redis-backed worker container, but job execution is still mostly synchronous-style in app code paths, and the current `jobs` model lacks chunk/outbox primitives required by `06-CONTEXT.md`.

The standard expert approach for this workload is at-least-once task delivery with idempotent task handlers and transaction-guarded DB transitions. Celery settings `task_acks_late=True` and `worker_prefetch_multiplier=1` are correct for fairness and crash retry behavior, but they must be paired with strict idempotency boundaries (`UNIQUE` constraints, claim tokens, guarded updates) so duplicate execution is safe.

For milestone auditing and broker-failure tolerance, implement a DB outbox (`audit_checkpoints`) and dispatch with row-claiming (`FOR UPDATE SKIP LOCKED`) rather than relying on in-memory or Celery result state. For cancellation, use cooperative cancellation (`cancel_requested`) as the primary flow, with `revoke(..., terminate=True)` reserved for stuck emergency cases only.

**Primary recommendation:** Implement a DB-authoritative chunk/outbox state machine (per `06-CONTEXT.md`) with queue isolation by tier (`interactive.t1..t3`, `batch.t1..t3`, `control`), Celery executing idempotent tasks only, and Flower + metrics for operational visibility.

## Standard Stack

The established stack for Phase 6 requirements:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Celery | 5.6.x (stable docs 5.6.2) | Distributed task execution | Mature Python queue runtime, first-class routing/retry/revocation semantics |
| Redis | 7.x | Broker/result backend | Already in stack, low overhead for Celery queueing |
| SQLAlchemy | 2.0.x | Transactional DB state machine | Supports `with_for_update(skip_locked=True)` and Postgres upsert patterns |
| PostgreSQL | 16.x | Source of truth | Strong constraints, row locking, conflict handling for idempotency |
| Flower | 2.x | Celery monitoring UI | Standard Celery monitor with worker/task visibility and Prometheus support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Kombu | bundled with Celery | Queue/exchange definitions | Explicit queue routing and isolation |
| Alembic / Flask-Migrate | existing | Schema migrations | Add `ingest_chunks`, `audit_checkpoints`, and DB guards |
| Prometheus (optional now, recommended) | current | Metrics scraping | Alerting on queue depth, lag, stuck chunks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Celery + Redis | Celery + RabbitMQ | RabbitMQ gives stronger broker semantics, but more ops overhead; current stack and phase scope favor Redis |
| Celery | RQ / Dramatiq | Simpler APIs, but less aligned with existing code and advanced routing/cancellation needs in this phase |
| DB outbox | Direct publish only | Simpler implementation, but loses durable dispatch semantics on broker/intermittent failure |

**Installation (project-specific baseline):**
```bash
pip install celery redis flower
```

## Architecture Patterns

### Recommended Project Structure
```text
src/
  jobs/
    orchestrator.py        # start_ingest and job-level orchestration
    chunking.py            # frozen chunk membership + chunk row creation
    claims.py              # claim/reclaim logic with stale detection
    checkpoints.py         # milestone crossing + outbox upsert
    dispatcher.py          # pending audit dispatcher (SKIP LOCKED)
    finalizer.py           # terminal transition logic
    cancellation.py        # cooperative cancellation and revocation helper
  tasks/
    ingest.py              # Celery task: ingest_chunk
    audits.py              # Celery tasks: dispatch_pending_audits, audit_run
    control.py             # cancel/finalize/sweep control tasks
  models/
    ingest_chunk.py
    audit_checkpoint.py
    job.py                 # extend enums/guards for phase semantics
```

### Pattern 1: DB-Authoritative Orchestration
**What:** Persist all progress and emission state in PostgreSQL; Celery only executes commands.

**When to use:** Always for ingest chunks, milestones, cancellation, and finalization.

**Why:** Celery is explicitly at-least-once. Exactly-once outcomes require DB constraints + guarded transitions.

### Pattern 2: Tiered Queue Isolation via Routing
**What:** Route tasks to tier/intent-specific queues (`interactive.t1..t3`, `batch.t1..t3`, `control`) with worker pools consuming targeted queues.

**When to use:** Any workload where interactive jobs must not be starved by bulk jobs.

**Why:** Queue isolation + worker allocation is more predictable than relying only on numeric message priority.

### Pattern 3: Outbox Dispatch with `SKIP LOCKED`
**What:** Store checkpoint dispatch intents in `audit_checkpoints`, claim pending rows with `FOR UPDATE SKIP LOCKED`, increment attempts while lock held, publish, then mark dispatched.

**When to use:** Any broker publication that must survive transient failures.

**Why:** Avoids duplicate claims across dispatcher workers and decouples durable intent from broker availability.

### Pattern 4: Cooperative Cancellation First
**What:** Transition job to `cancel_requested`, stop new claims, let in-progress chunks exit at safe boundaries, then finalize to `cancelled`.

**When to use:** All user-driven cancels.

**Why:** Hard termination can leave partial external side effects and inconsistent local state.

### Anti-Patterns to Avoid
- **Treating Celery result backend as truth:** Task state and DB state can diverge.
- **Incrementing progress outside completion transaction:** Creates phantom progress under retries.
- **Recomputing chunk membership on retry:** Breaks idempotency and progress semantics.
- **Single shared queue for all priorities:** Causes noisy-neighbor starvation.

## Decision Matrix (Holistic)

| Option | Strengths | Weaknesses | Operational Risk | Chosen? Why/Why Not |
|--------|-----------|------------|------------------|---------------------|
| A. DB-authoritative state machine + Celery execution + outbox dispatcher | Precise recovery semantics, idempotent retries, deterministic milestones | More schema and transaction logic | MEDIUM (implementation complexity) | **Chosen** - matches `06-CONTEXT.md` invariants and minimizes data correctness risk |
| B. Celery task state as primary progress source | Faster to build initially | Drift between broker/task state and DB; weak replay guarantees | HIGH (silent correctness failures) | Rejected - violates Phase 6 reliability principles |
| C. In-process threads/async jobs in API service | Minimal infra change | Poor durability, weak observability, restart loss, scale limits | HIGH (production fragility) | Rejected - does not satisfy phase goals or requirements |

**Decision rule applied:** Prefer lower migration/correctness risk over lower initial coding effort.

## Sequential Thinking Trace

1. **Problem framing:** Build production-safe async ingest/audit/cancellation where DB is authoritative and Celery is at-least-once executor.
2. **Evidence baseline:** Existing Celery config has correct core toggles (`acks_late`, prefetch=1), but tasks/domain orchestration are placeholders; current job cancel path is immediate state flip without cooperative semantics.
3. **Branches explored:** (A) DB-authoritative orchestration, (B) broker-state-centric orchestration, (C) in-process workers.
4. **Stress tests:** worker crash mid-chunk, duplicate deliveries, broker outage during checkpoint publish, cancel while chunks running, stale claims.
5. **Chosen approach:** Option A due to strongest data correctness and replay safety.
6. **Confidence:**
   - State machine design: HIGH
   - Queue routing model: HIGH
   - Cancellation behavior: HIGH
   - Capacity sizing defaults: MEDIUM (needs workload tuning)
7. **Unknowns:** initial worker split and strict-vs-lenient terminal failure policy remain open by design in `06-CONTEXT.md`.

## Incremental Implementation Strategy

### Phase Ordering
1. **Foundation (non-breaking):**
   - Add `ingest_chunks` and `audit_checkpoints` tables.
   - Add `jobs` constraints/guards and ingest-class active lock.
   - Add queue declarations/routing config without cutover.
2. **Integration (compatible):**
   - Implement `start_ingest`, `ingest_chunk`, dispatcher, finalizer, cancellation services.
   - Add Celery tasks that call service-layer transaction functions.
3. **Cutover (controlled):**
   - Route ingest API/job creation to new orchestrator.
   - Keep legacy job read/status endpoints compatible.
4. **Hardening:**
   - Flower auth/persistence, metrics, alerts, stale-job sweeps.
   - Retention/cleanup for old terminal jobs and stale rows.

### Compatibility Plan
- Preserve existing `/api/v1/jobs` response contracts while extending underlying state logic.
- Keep legacy statuses exposed, mapping internal transient states as needed during migration.
- Leave existing non-ingest job types untouched until explicitly migrated.

### Rollback Plan
- **Rollback triggers:** duplicate milestone emissions, stuck `in_progress` growth, queue starvation, cancel flows not converging.
- **Fast rollback path:** disable new orchestrator entrypoint (feature flag), stop dispatcher workers, revert to previous synchronous/legacy job path, keep new tables intact for postmortem.

## Don't Hand-Roll

| Problem | Do Not Build | Use Instead | Why |
|---------|--------------|-------------|-----|
| Async execution engine | Custom thread/process queue | Celery workers and routing | Celery already solves retries, queueing, visibility, and worker lifecycle |
| Durable publish retry | Ad-hoc in-memory retry loops | DB outbox + dispatcher task | Survives process crash and broker outage |
| Claim concurrency control | App-level mutexes | Postgres row locks + `SKIP LOCKED` | Correct cross-worker behavior under contention |
| Monitoring UI | Custom dashboard first | Flower (+ Prometheus scrape) | Faster operational value and lower build risk |
| Cancel semantics | Immediate hard kill by default | Cooperative cancel + optional emergency terminate | Safer for data consistency and partial side effects |

**Key insight:** In this phase, correctness under retries and failures is more important than raw throughput.

## Common Pitfalls

### Pitfall 1: Progress Drift from Non-Transactional Updates
**What goes wrong:** `jobs.processed_count` increments even when chunk completion did not commit.
**Why it happens:** Progress mutation is separate from guarded chunk transition.
**How to avoid:** Perform chunk completion, progress increment, milestone calculation in one transaction.
**Warning signs:** `processed_count` exceeds total chunk expected totals.

### Pitfall 2: Duplicate Milestone Emission
**What goes wrong:** Same checkpoint publishes multiple audits.
**Why it happens:** No unique key or non-idempotent dispatch transition.
**How to avoid:** `UNIQUE(job_id, checkpoint)` plus outbox `dispatch_status` claim/publish/mark flow.
**Warning signs:** Duplicate `(job_id, checkpoint)` audit artifacts.

### Pitfall 3: Stuck In-Progress Chunks
**What goes wrong:** Worker crash leaves chunks permanently non-terminal.
**Why it happens:** No stale reclaim policy.
**How to avoid:** Reclaim only stale `in_progress` rows by `claimed_at < now - STALE_AFTER`.
**Warning signs:** Old `in_progress` rows with no worker activity.

### Pitfall 4: Starvation of Interactive Jobs
**What goes wrong:** Tier 1 batch floods block high-priority work.
**Why it happens:** Single queue or poor worker allocation.
**How to avoid:** Queue isolation plus dedicated worker pools and explicit `-Q` consumption.
**Warning signs:** High latency for tier-3 interactive jobs during batch spikes.

### Pitfall 5: Unsafe Hard Cancellation
**What goes wrong:** Partial writes and inconsistent state after force termination.
**Why it happens:** Using terminate-first cancellation strategy.
**How to avoid:** Cooperative cancellation checkpoints; terminate only for non-responsive tasks.
**Warning signs:** Frequent manual reconcile after cancel actions.

### Pitfall 6: Overreliance on Broker State
**What goes wrong:** UI/API reports completed while DB work is incomplete (or opposite).
**Why it happens:** Treating Celery event/result state as authoritative.
**How to avoid:** Read status from DB state machine only.
**Warning signs:** Flower state and API job state frequently disagree.

### Pitfall 7: Dispatcher Thundering Herd
**What goes wrong:** Many dispatcher instances hammer same rows.
**Why it happens:** Poll loop without lock-aware claim semantics.
**How to avoid:** `FOR UPDATE SKIP LOCKED`, bounded batch size, retry backoff.
**Warning signs:** High DB lock waits on outbox table.

## Code Examples

Verified patterns from official sources and phase constraints:

### 1) Celery Reliability Defaults
```python
# Source: Celery optimizing guide
app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
```

### 2) Queue Routing by Intent/Tier
```python
# Source: Celery routing guide
from kombu import Queue

app.conf.task_queues = (
    Queue("interactive.t1"), Queue("interactive.t2"), Queue("interactive.t3"),
    Queue("batch.t1"), Queue("batch.t2"), Queue("batch.t3"),
    Queue("control"),
)

app.conf.task_routes = {
    "src.tasks.ingest.start_ingest": {"queue": "control"},
    "src.tasks.ingest.ingest_chunk_t1": {"queue": "batch.t1"},
    "src.tasks.ingest.ingest_chunk_t2": {"queue": "batch.t2"},
    "src.tasks.ingest.ingest_chunk_t3": {"queue": "batch.t3"},
    "src.tasks.audits.dispatch_pending_audits": {"queue": "control"},
}
```

### 3) SQLAlchemy Claim with `SKIP LOCKED`
```python
# Source: SQLAlchemy 2.x query guide (with_for_update)
stmt = (
    select(AuditCheckpoint)
    .where(AuditCheckpoint.dispatch_status == "pending_dispatch")
    .where(
        (AuditCheckpoint.next_dispatch_at.is_(None)) |
        (AuditCheckpoint.next_dispatch_at <= now_utc)
    )
    .order_by(AuditCheckpoint.id)
    .limit(50)
    .with_for_update(skip_locked=True)
)
rows = session.execute(stmt).scalars().all()
```

### 4) Postgres Upsert for Idempotent Outbox Writes
```python
# Source: SQLAlchemy PostgreSQL ON CONFLICT docs
from sqlalchemy.dialects.postgresql import insert

stmt = insert(AuditCheckpoint).values(
    job_id=job_id,
    store_id=store_id,
    checkpoint=checkpoint,
    dispatch_status="pending_dispatch",
    dispatch_attempts=0,
)

stmt = stmt.on_conflict_do_update(
    index_elements=[AuditCheckpoint.job_id, AuditCheckpoint.checkpoint],
    set_={
        "dispatch_status": "pending_dispatch",
        "next_dispatch_at": None,
        "last_error": None,
    },
)
session.execute(stmt)
```

### 5) Cooperative Cancellation Guard in Chunk Task
```python
def ingest_chunk(job_id: int, chunk_idx: int):
    job = session.get(Job, job_id)
    if job.status == "cancel_requested":
        return {"skipped": True, "reason": "cancel_requested"}

    claim = claim_chunk(session, job_id=job_id, chunk_idx=chunk_idx)
    if not claim:
        return {"skipped": True, "reason": "not_claimed"}

    # Process frozen membership for claimed chunk...
    complete_chunk_transaction(session, claim)
    return {"ok": True}
```

## Operational Readiness

### Testing Strategy
- **Unit tests:**
  - claim/reclaim transitions
  - milestone crossing computation
  - finalizer decision logic (completed/failed/cancelled)
- **Integration tests (DB + Celery eager/worker):**
  - duplicate task delivery idempotency
  - dispatcher crash/retry behavior
  - cancellation convergence (`cancel_requested -> cancelled`)
- **Contract/API tests:**
  - `/api/v1/jobs` status behavior unchanged for clients
  - cancel endpoint semantics remain compatible

### Observability and Diagnostics
- **Metrics to add:**
  - queue depth per queue
  - task runtime and wait latency by queue/tier
  - `ingest_chunks` claim age and stale reclaim count
  - `audit_checkpoints` pending backlog and retry age
  - terminal state counts by reason
- **Logs/events to add:**
  - `job_id`, `store_id`, `chunk_idx`, `claim_token`, `attempt`
  - checkpoint dispatch attempts and error class
  - cancellation signal and finalizer transitions
- **Alert thresholds (initial):**
  - any chunk `in_progress` older than `STALE_AFTER + 5m`
  - pending dispatch backlog older than 5 minutes
  - queue lag above SLO for interactive queues

### Production Guardrails
- Start with conservative concurrency and prefetch=1.
- Keep hard terminate disabled in normal cancel flows.
- Use feature flag for orchestrator cutover path.
- Enable Flower auth/basic auth before exposing dashboard beyond localhost.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Broker/task state treated as truth | DB-authoritative task orchestration | Matured as reliability best practice for at-least-once systems | Safer recovery and replay semantics |
| Single queue for all workloads | Queue isolation + worker allocation by tier/intent | Widely adopted in production Celery deployments | Reduces starvation and improves predictability |
| Ad-hoc publish retries | Transactional outbox + lock-safe dispatcher | Common reliability pattern in distributed systems | Survives broker and process failures |
| Force terminate for cancel by default | Cooperative cancellation first | Operational best practice for data-safe pipelines | Fewer partial side effects and reconcile events |
| Manual worker/task inspection | Flower + metrics endpoint scraping | Standardized operational monitoring | Faster diagnosis and safer scaling changes |

**New tools/patterns to consider later (not mandatory in Phase 6):**
- Dead-letter/retry queues per failure class
- Dedicated scheduler/beat for sweep jobs if opportunistic finalization is insufficient

**Deprecated/outdated for this phase:**
- In-memory progress tracking for long-running distributed jobs
- Non-idempotent task handlers with `acks_late=True`

## Open Questions

1. **Initial worker concurrency split by tier/queue**
   - What we know: queue isolation is required; routing model is fixed in context.
   - What is unclear: exact concurrency per queue for expected traffic profile.
   - Recommendation: start with conservative split (e.g., `control` small dedicated pool, balanced batch pools), measure queue lag, tune weekly.

2. **Strict vs lenient terminal failure policy**
   - What we know: context allows policy choice.
   - What is unclear: business tolerance for partial ingest success.
   - Recommendation: default strict for first rollout; introduce lenient mode only with explicit product sign-off.

3. **Retention policy for chunk/checkpoint/job history**
   - What we know: JOBS-08 requires cleanup.
   - What is unclear: regulatory/business retention duration.
   - Recommendation: define default retention (e.g., 30-90 days) with archive option before hard delete.

4. **Outbox dispatcher cadence vs DB load**
   - What we know: context default is 10s cadence, batch size 50.
   - What is unclear: actual lock/contention profile under production load.
   - Recommendation: ship defaults, then tune cadence/batch based on lock wait and backlog metrics.

## Sources

### Primary (HIGH confidence)
- `./.planning/phases/06-job-processing-infrastructure-celery/06-CONTEXT.md` - locked decisions, invariants, state machines
- `./src/celery_app.py` - current Celery baseline in this codebase
- `./src/models/job.py` - current job schema and status model
- `./src/api/v1/jobs/routes.py` - current job API and cancel behavior
- Celery docs (stable 5.6.2):
  - Optimizing: https://docs.celeryq.dev/en/stable/userguide/optimizing.html
  - Routing: https://docs.celeryq.dev/en/stable/userguide/routing.html
  - Workers / revoke semantics: https://docs.celeryq.dev/en/stable/userguide/workers.html
- SQLAlchemy docs:
  - `with_for_update` / locking options: https://docs.sqlalchemy.org/en/20/orm/queryguide/query.html
  - PostgreSQL ON CONFLICT upsert: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#insert-on-conflict-upsert
- PostgreSQL docs:
  - `SKIP LOCKED`: https://www.postgresql.org/docs/current/sql-select.html
- Flower docs:
  - CLI/man options: https://github.com/mher/flower/blob/master/docs/man.rst

### Secondary (MEDIUM confidence)
- Existing project roadmap and requirements alignment:
  - `./.planning/ROADMAP.md`
  - `./.planning/REQUIREMENTS.md`
  - `./.planning/STATE.md`

### Tertiary (LOW confidence)
- None.

## Metadata

**Research scope:**
- Core technology: Celery + Redis + PostgreSQL orchestration
- Ecosystem: Flower monitoring, SQLAlchemy 2.x transactional patterns
- Patterns: chunk state machine, outbox dispatch, cooperative cancellation, tiered queue routing
- Pitfalls: duplicate delivery, progress drift, starvation, stale claims, unsafe termination

**Confidence breakdown:**
- Standard stack: HIGH - aligned with official docs and existing platform stack
- Architecture patterns: HIGH - directly constrained by `06-CONTEXT.md` and authoritative queue/DB locking patterns
- Pitfalls: HIGH - derived from known failure modes in at-least-once processing
- Code examples: HIGH - based on official Celery/SQLAlchemy/PostgreSQL references and current project model

**Risk class (holistic planning):** HIGH
- Reason: touches queueing, persistence invariants, cancellation semantics, and shared job contracts.

**Research date:** 2026-02-10
**Valid until:** 2026-03-12 (30 days - infrastructure settings may need quick retuning based on observed production behavior)

**Research constraints from 06-CONTEXT.md:**
- LOCKED: Shopify ingest first, checkpoint policy (<1000: 25..100, >=1000: 100 only), no auto-create enrichment jobs
- LOCKED: DB as source of truth, Celery at-least-once tolerance, cooperative cancellation default
- LOCKED: queue topology (`interactive.t1..t3`, `batch.t1..t3`, `control`)
- LOCKED: frozen chunk membership for retries
- OPEN: worker split and strict-vs-lenient terminal policy
