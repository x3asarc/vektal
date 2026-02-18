# Phase 13: Integration Hardening & Deployment - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Harden production agent execution and external integrations, then prepare deployment infrastructure with enforceable reliability, governance, observability, and security controls. This phase focuses on production hardening and deployment readiness, not autonomous optimization/training loops.

</domain>

<decisions>
## Implementation Decisions

### Pre-Context Alignment
- Course selected: B
- High-level direction: Balanced Production Readiness
- Portfolio rationale: complete roadmap-defined hardening (`13-01` to `13-03`) and add instrumentation foundation (`13-04`) without pulling Phase 14/15 autonomy into this phase.

### Boundary Hardening Policy Matrix (`13-01`)
- Circuit breakers are policy-driven and versioned per skill/provider in config storage, not hardcoded in code paths.
- Default breaker thresholds:
  - error rate: `>25%` over rolling 5-minute window
  - p95 latency: `>15.0s` for Tier 1/2; `>45.0s` for Tier 3 tool calls
  - min sample: `10` requests before state transition
  - open cooldown: `60s`
  - half-open recovery: `3` consecutive successful probes to close
- Breaker policy changes must persist `policy_version`, `effective_at`, and `changed_by_id` audit lineage.
- Retry/network matrix:
  - `429`: max 3 retries, exponential backoff (`2^n`) + jitter, respect `Retry-After` exactly
  - `5xx`: max 2 retries, linear backoff (`5s`, `10s`), increment breaker error count
  - timeout: max 1 retry with `1.5x` timeout budget, trip breaker if retry fails
  - connectivity (socket/dns/tls): max 3 immediate retries, classify as infra failure class
  - schema/validation: max 1 reflexive fixer attempt (small model), no infinite retries
- Idempotency contract:
  - key scope: `sha256(tenant_id + action_type + resource_id + payload_hash)`
  - terminal semantics:
    - `PROCESSING`: return `202 Accepted` + `status_url`
    - `SUCCESS`: return cached response (`TTL=24h`)
    - `FAILED`: allow one explicit retry path after key-state reset, then return `422` on repeated failure
    - `EXPIRED`: treat as new request after key purge
- Bulkhead isolation is mandatory: Tier 3 workloads run on isolated queues so Tier 1/Tier 2 responsiveness is preserved under heavy or failing research execution.
- Tier 3 queue backlog protection is mandatory:
  - every Tier 3 queued message carries `message_ttl_seconds` (default `900`, policy-configurable cap `3600`)
  - expired messages are dead-lettered (not auto-resumed after downtime)
  - dead-letter/expiry events must emit audit telemetry and user-visible status (`expired_not_run`) to prevent silent budget burn on restart.

### Governance & Recovery (`13-02`)
- Post-execution verification oracle is mandatory before action is considered final.
- Verification polling: `5s`, `10s`, `15s` intervals (max `30s` total wait).
- If not verified by deadline, set `DEFERRED_VERIFICATION` and continue with explicit user-visible status update; do not silently drop state.
- DR objectives:
  - single-tenant state: `RTO < 2 min`, `RPO <= 5 min`
  - full system database: `RTO < 1 hr`, `RPO <= 6 hr`
- Canary rollback gate:
  - baseline: last stable production release (`N-1`)
  - trigger: rollback when canary availability drops `>5%` versus baseline
  - sample floor: `N > 100` requests within same tenant/tier scope
- Protected-field policy:
  - immutable: `store_currency`, `admin_email`, `tenant_id`
  - HITL thresholds are tenant-configurable policy values (for example inventory delta and price-change percent), evaluated per request.
- Kill-switch controls are required:
  - global kill-switch: fail closed to safe degraded mode
  - tenant kill-switch: disable high-risk execution for one tenant without global impact

### Deployment, Observability, and Security (`13-03`)
- Availability SLI formula:
  - `successful_requests / (total_requests - user_errors)`
  - target: `99.9%`
- Error budget:
  - `43m 12s` downtime allowed per 30-day window before feature-freeze gate.
- Every request must carry `correlation_id` across UI, router, tool execution, and provider call layers.
- Security/redaction policy:
  - primary: structured field-level masking in JSON logs
  - secondary: regex fallback for unstructured traces/reasoning text
- Retention policy:
  - traces: `14 days`
  - audit logs: `1 year`
- Right-to-be-forgotten policy:
  - live stores purge within `48h`
  - backup/snapshot purge follows delayed rotation SLA (`<=14 days`) with audit record.

### Instrumentation Foundation (`13-04`)
- Phase 13 is instrumentation-only for learning data; no autonomous training loops in this phase.
- Required telemetry per execution includes:
  - `correlation_id`
  - `tier`
  - `preference_signal` (human feedback/edit signal)
  - `oracle_signal` (binary verification result)
  - `reasoning_trace_tokens`
  - `cost_usd`
- All Tier 2/3 outputs must be joinable to verification outcomes to build downstream correctness datasets.

### Claude's Discretion
- Exact storage engine split for idempotency keys (Redis-only vs Redis+Postgres shadow) as long as terminal semantics and TTL guarantees are preserved.
- Exact dashboard UX for SLO/error-budget reporting as long as formulas and thresholds remain unchanged.
- Exact worker pool sizing and queue partition counts as long as bulkhead isolation behavior is preserved.

</decisions>

<specifics>
## Specific Ideas

- "Magic of AI meets the violence of production" translated into strict policy matrices and binary gates.
- Emphasis on preventing "cascading stupidity" through skill-level breakers, bulkheads, and kill-switch controls.
- "Every interaction is a governed transaction" adopted as implementation anchor.
- Phase 13 explicitly prepares DPO/RLVR-ready data capture without enabling training behavior yet.

</specifics>

<deferred>
## Deferred Ideas

- Preference-model training loops and automatic policy adaptation move to Phase 14.
- Full RLVR-driven self-healing/remediation orchestration moves to Phase 15.
- Any broader multi-provider autonomy beyond hardening and fallback policy remains out of Phase 13 scope.

</deferred>

<discussion_evidence>
## Discussion Evidence

- areas_discussed: reliability matrix, retries/idempotency, governance/recovery, observability/security, instrumentation scope
- questions_answered: 20+
- user_answers_captured: yes

</discussion_evidence>

---

*Phase: 13-integration-hardening-deployment*
*Context gathered: 2026-02-16*
