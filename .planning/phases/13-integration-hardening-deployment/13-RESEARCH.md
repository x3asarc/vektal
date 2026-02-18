# Phase 13: Integration Hardening & Deployment - Research

**Researched:** 2026-02-16  
**Domain:** Production reliability, governance, observability, and deployment hardening for agentic execution  
**Confidence:** HIGH (contracts and architecture), MEDIUM-HIGH (operational tuning)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Policy-driven breakers and retry matrix with explicit thresholds and terminal semantics.
- Async-friendly idempotency behavior and replay handling.
- Oracle verification with deferred state when eventual consistency prevents immediate confirmation.
- RTO/RPO, canary rollback math, protected fields, and kill-switch controls are mandatory.
- Structured redaction, retention windows, deletion propagation, and instrumentation-only learning foundation are required.
- Tier 3 backlog protection must include queue message TTL + dead-letter + user-visible expiry status.

### Claude's Discretion
- Idempotency storage split and operational implementation details.
- Dashboard implementation details for SLI/error budget visibility.
- Worker pool sizing and queue partition strategy.

### Deferred Ideas (OUT OF SCOPE)
- Autonomous training loops and policy adaptation (Phase 14).
- Self-healing remediation loops and dynamic scripting promotion (Phase 15).
</user_constraints>

## Summary

Phase 13 should be delivered as a production hardening layer over existing phase foundations, not as a functional rewrite. Phase 8 already established dry-run/approval/apply safety semantics, Phase 11 established snapshot/recovery and retry-ready primitives, and Phase 12 established route/policy control surfaces. Phase 13 now turns those primitives into audited, deterministic production contracts.

Synthesis from core and deep research indicates four required waves:
1. Boundary hardening and execution reliability (`13-01`).
2. Governance and recovery semantics (`13-02`).
3. Deployment, observability, and security operations (`13-03`).
4. Instrumentation-only learning data capture (`13-04`).

Primary recommendation: keep wave order strict and gate each wave by contract tests. This reduces operational risk and avoids hidden coupling between runtime hardening and deployment controls.

## Locked Context Constants (Congruency Anchor)

The following locked constants from `13-CONTEXT.md` must be preserved during execution:

- Breaker policy lineage fields: `policy_version`, `effective_at`, `changed_by_id`.
- Retry classes and limits:
  - `429`: max 3 retries with exponential backoff + jitter.
  - `5xx`: max 2 retries with linear backoff.
  - `timeout`: max 1 retry with `1.5x` timeout budget.
  - `connectivity`: max 3 immediate retries.
  - `schema/validation`: max 1 reflexive fixer attempt.
- Idempotency terminal semantics: `PROCESSING`, `SUCCESS`, `FAILED`, `EXPIRED`.
- Tier 3 backlog protection:
  - `message_ttl_seconds` default `900`, policy cap `3600`.
  - expired tasks must be dead-lettered with user-visible `expired_not_run`.
- Verification oracle cadence: `5s`, `10s`, `15s` (max `30s`) with `DEFERRED_VERIFICATION` when unresolved.
- DR thresholds:
  - single-tenant state: `RTO < 2 min`, `RPO <= 5 min`.
  - full DB: `RTO < 1 hr`, `RPO <= 6 hr`.
- Canary constraints:
  - rollback trigger: availability drop `>5%` vs baseline.
  - sample floor: `N > 100` within same tenant/tier scope.
- Observability/SLO:
  - availability SLI formula: `successful_requests / (total_requests - user_errors)`.
  - availability target: `99.9%`.
  - error budget: `43m 12s` per 30-day window.
- Security/retention/deletion:
  - traces: `14 days`.
  - audit logs: `1 year`.
  - right-to-be-forgotten: live purge within `48h`, backup/snapshot delayed purge `<=14 days`.
- Instrumentation-only fields required in Tier 2/3 lineage:
  - `correlation_id`, `preference_signal`, `oracle_signal`, `reasoning_trace_tokens`, `cost_usd`.

## Standard Stack

### Core
| Component | Purpose | Why Standard |
|---|---|---|
| FastAPI/Pydantic contract boundaries | typed IO + server-side validation | deterministic policy enforcement |
| Celery + Redis queues | background execution by tier | supports bulkhead and retry controls |
| PostgreSQL policy/audit stores | durable state and governance trail | transactional reliability and auditability |
| Existing chat/resolution APIs | reuse safety chain | avoids duplicate mutation logic |

### Supporting
| Component | Purpose |
|---|---|
| Dead-letter queues | contain expired/failed high-cost tasks |
| correlation_id propagation | end-to-end traceability |
| audit export pathways | compliance and operator forensics |

## Architecture Patterns

### Pattern 1: Policy-first execution contract
- Route + policy snapshot evaluated first.
- Idempotency checked before mutation.
- Retry/breaker path selected by error class.
- Final state requires oracle verification status assignment.

### Pattern 2: Verification-before-finality
- Tool success is provisional until verified.
- Deferred verification is explicit and user-visible.

### Pattern 3: Blast-radius isolation
- Tier 3 workloads isolated from Tier 1/2 capacity.
- Tier 3 TTL/dead-letter guardrail prevents restart budget shocks.

### Pattern 4: Auditable rollout governance
- Canary baseline is explicit (N-1).
- Rollback threshold and sample floor are machine-checkable.

## Do Not Hand-Roll

| Problem | Do not build | Use instead | Why |
|---|---|---|---|
| Retry behavior by endpoint | ad hoc retry code | central retry matrix | avoids inconsistent failure handling |
| Breaker transitions in handlers | inline flags | versioned breaker policy object | prevents drift and hidden behavior |
| Backlog restart behavior | blind queue replay | TTL + dead-letter + explicit status | protects cost and correctness |

## Common Pitfalls

### Pitfall 1: Duplicate side effects
- Cause: retry without terminal idempotency semantics.
- Prevention: PROCESSING/SUCCESS/FAILED/EXPIRED contracts.

### Pitfall 2: False completion state
- Cause: treating provider success as immediately durable.
- Prevention: mandatory verification oracle path and deferred state.

### Pitfall 3: Interactive degradation from research queue load
- Cause: shared pools and no bulkheads.
- Prevention: tier-isolated queue routing, TTL, dead-letter.

### Pitfall 4: Flapping canary rollback
- Cause: rollback without sample floor/scope match.
- Prevention: baseline and sample floor constraints.

## Requirement Mapping

| Requirement | Coverage in Research Contract |
|---|---|
| INTEGRATE-01 | boundary + threat model in execution policy surfaces |
| INTEGRATE-02 | strict contracts, validation, idempotency terminal semantics |
| INTEGRATE-03 | secure execution: RBAC/policy/HITL/protected fields |
| INTEGRATE-04 | retry/backoff, breakers, graceful degradation |
| INTEGRATE-05 | provider fallback governance and cost-aware routing hooks |
| INTEGRATE-06 | traces/metrics/logs/cost telemetry requirements |
| INTEGRATE-07 | canary/evaluation gates and regression safety gates |
| INTEGRATE-08 | retention/export/deletion and compliance controls |
| DEPLOY-01..08 | compose/env/backups/cicd/monitoring/log/APM/security hardening pathway |

## Context7 Evidence

This phase reuses verified upstream Context7 references from recent phase research:
- `/websites/postgresql_16` (policy and RLS semantics)
- `/pgvector/pgvector` (retrieval tuning and filtering patterns)
- `/websites/celeryq_dev_en_stable` (retry/backoff/jitter semantics)

No conflicting evidence was introduced in this synthesis pass.

## Open Questions

1. Final per-provider timeout budgets by operation class.
2. Initial queue partition and concurrency defaults for production launch.
3. Tenant-level policy defaults for protected-field HITL thresholds.

## Metadata

**Confidence breakdown**
- Reliability contract: HIGH
- Governance/recovery semantics: HIGH
- Deployment/observability contract: HIGH
- Runtime tuning constants: MEDIUM-HIGH

**Valid until:** 30 days for contract assumptions; tune constants against live telemetry during execution.
