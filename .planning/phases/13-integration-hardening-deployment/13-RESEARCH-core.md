# Phase 13: Integration Hardening & Deployment - Research (Core Pass)

**Researched:** 2026-02-16  
**Domain:** Production hardening for agentic execution, provider integrations, and deployment reliability  
**Confidence:** HIGH (policy contracts), MEDIUM-HIGH (runtime tuning depends on production telemetry)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Circuit breakers are policy-driven and versioned per skill/provider.
- Retry matrix and idempotency semantics are explicit and mandatory.
- Tier 3 workloads require bulkhead isolation and queue backlog protection.
- Verification oracle polling is mandatory; unresolved verification becomes deferred status.
- RTO/RPO, canary rollback gates, protected-field policies, and kill-switches are required.
- Observability, structured redaction, retention/deletion, and instrumentation are required.

### Claude's Discretion
- Storage split for idempotency keys.
- Dashboard UX for SLO/error-budget reporting.
- Worker pool sizing and queue partition count.

### Deferred Ideas (OUT OF SCOPE)
- Continuous learning/training loops (Phase 14).
- Self-healing autonomous remediation loops (Phase 15).
</user_constraints>

## Summary

Phase 13 should be executed as a hardening layer over existing Phase 8/10/11/12 foundations, not as a rewrite. The architecture already has dry-run/apply controls, routing policy controls, and snapshot/recovery primitives. The work now is to convert these into explicit production contracts with deterministic failure behavior.

Primary recommendation: implement in four waves:
1. Boundary hardening and execution reliability contract.
2. Governance and recovery contract.
3. Deployment/observability/security contract.
4. Instrumentation-only data contract for Phase 14/15 readiness.

## Standard Stack

### Core
| Library/Component | Version/State | Purpose | Why Standard |
|---|---|---|---|
| FastAPI + Pydantic contracts | existing | Typed API and validation contracts | Deterministic request/response enforcement |
| Celery + Redis queues | existing | Tier-aware background execution | Supports isolated queues and retry controls |
| PostgreSQL | existing | Policy, audit, and durability store | Strong transactional semantics for governance |
| Existing chat/resolution APIs | existing | Execution path integration | Avoids duplicating apply/approval logic |

### Supporting
| Component | Purpose | When to Use |
|---|---|---|
| Dead-letter queue handling | Backlog protection and expired task routing | Tier 3 and long-running workflows |
| Correlation-id propagation | Traceability across layers | Every request and tool chain |
| Structured audit export path | Compliance and operator debug | Every mutating execution |

## Architecture Patterns

### Pattern 1: Policy-first reliability gate
- Evaluate policy before execution.
- Apply idempotency key semantics.
- Run retry/backoff rules by error class.
- Apply breaker transitions and fallback decisions.

### Pattern 2: Verification-before-finality
- Tool success is provisional.
- Verification oracle determines final status.
- Deferred verification is explicit and user-visible.

### Pattern 3: Queue and blast-radius isolation
- Tier 1/2 remain responsive under Tier 3 stress.
- Tier 3 messages use TTL + dead-letter routing.
- No automatic replay of expired high-cost tasks.

## Do Not Hand-Roll

| Problem | Do not build | Use instead | Why |
|---|---|---|---|
| Per-request ad hoc retries | custom scattered retry code | centralized retry matrix | Consistent behavior and auditability |
| Manual breaker toggles in handlers | handler-level flags | versioned breaker policy registry | Avoid drift and hidden logic |
| Implicit task backlog recovery | blind queue replay | TTL + dead-letter + explicit status | Prevent budget shock and hidden side effects |

## Common Pitfalls

### Pitfall: Duplicate side effects on retries
- Cause: missing terminal idempotency states.
- Prevention: PROCESSING/SUCCESS/FAILED/EXPIRED semantics with stable key scope.

### Pitfall: False confidence from tool "success"
- Cause: external eventual consistency.
- Prevention: mandatory oracle polling with deferred verification state.

### Pitfall: Cascading outage from Tier 3 saturation
- Cause: shared pools and no backlog TTL.
- Prevention: queue bulkheads, TTL, dead-letter, and tenant/global kill-switches.

## Requirement Mapping (Core)

| Requirement | Core Mapping |
|---|---|
| INTEGRATE-01 | Policy boundaries and threat model enforced in execution path |
| INTEGRATE-02 | Typed contract + idempotency + terminal semantics |
| INTEGRATE-03 | RBAC/policy gates + HITL thresholds + protected fields |
| INTEGRATE-04 | Retry/backoff + breaker + graceful degradation |
| INTEGRATE-06 | correlation_id, SLI/SLO telemetry, audit events |
| INTEGRATE-08 | Retention, export controls, and deletion propagation |
| DEPLOY-03 | Backup/restore objectives tied to RTO/RPO |
| DEPLOY-05 | Alerting and operational signals |

## Context7 Evidence

Context7 was not re-run in this core pass because Phase 12 research already captured current references used by this phase:
- `/websites/postgresql_16` (RLS and policy behavior)
- `/pgvector/pgvector` (retrieval controls)
- `/websites/celeryq_dev_en_stable` (retry/backoff/jitter patterns)

Phase 13 planning reuses these verified upstream findings and extends with phase-specific production contracts.

## Open Questions

1. Exact initial threshold values per provider/skill beyond defaults.
2. Preferred idempotency storage split for highest throughput paths.
3. Initial queue partition sizing and autoscaling thresholds.

