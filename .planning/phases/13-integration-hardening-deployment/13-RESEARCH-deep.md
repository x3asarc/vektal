# Phase 13: Integration Hardening & Deployment - Research (Deep Pass)

**Researched:** 2026-02-16  
**Author:** AI research agent  
**Version:** v1  
**Confidence:** HIGH on contracts, MEDIUM on tuning constants pending live telemetry

## Executive Summary

Phase 13 is the point where existing feature correctness must be converted into production survivability. The existing system already has strong foundations: dry-run-first mutation safety, product-scoped approvals, snapshot/recovery workflows, route-aware capability control, and tiered runtime boundaries. The remaining risk is not missing features; it is inconsistent runtime behavior under pressure. This phase addresses that by enforcing explicit reliability contracts, deterministic fallback logic, and operational observability that can be trusted during incidents.

The primary architectural shape should be a policy-driven control plane around all mutating and high-cost operations. Every execution request should carry policy context (tier, tenant, tool class, approval state), correlation identifiers, idempotency keys, and bounded retry/breaker behavior. Every post-execution path should include verification and terminal state assignment, including deferred states where external eventual consistency prevents immediate confirmation. This prevents hidden partial failures and makes operator behavior predictable.

A second requirement is blast-radius containment. Tier 3 workloads are the highest-risk and highest-cost paths. They must be isolated from Tier 1/2 runtime capacity, and queue backlog recovery must not replay stale expensive work after restarts. Message TTL plus dead-letter routing plus user-visible expiry states are required to stop cost spikes and untraceable side effects.

The third requirement is deployment governance. Canary gates, rollback math, SLI formulas, error budgets, and retention/deletion contracts must be explicit and machine-checkable. A deployment that "looks healthy" but has no reproducible thresholds is operational debt. The Phase 13 contract should therefore define not only what to build, but how to detect drift and when to fail closed.

Recommendations:
1. Execute in four waves exactly aligned to `13-01..13-04`.
2. Keep policy values tenant-configurable with versioned audit lineage.
3. Treat verification-oracle outcomes as first-class operational signals.
4. Require test contracts for every policy decision path.
5. Keep all learning scope instrumentation-only in this phase.

## Methodology

### Source Inputs
- `.planning/phases/13-integration-hardening-deployment/13-CONTEXT.md`
- `.planning/phases/13-integration-hardening-deployment/13-PRE-CONTEXT-SCOPE.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- Existing phase artifacts from Phase 8, 11, and 12

### Multi-pass approach
1. Pass 1: scope/theme scan (reliability, governance/recovery, deployment, instrumentation).
2. Pass 2: detailed extraction (thresholds, semantics, formulas, retention, queue controls).
3. Pass 3: gap audit (terminal states, canary baseline math, deletion propagation, policy versioning).

### Limitations
- No fresh external Context7 pull in this pass; inherits verified upstream references from recent phase research.
- Operational tuning values beyond defaults require production telemetry after rollout.

## Domain Overview

Production hardening for agentic systems has five overlapping concerns:
1. Correctness under retry/failure.
2. Safety under privilege and mutation boundaries.
3. Resilience under provider/service instability.
4. Operability under live incident conditions.
5. Auditability for compliance and postmortems.

### Glossary
- **Breaker Open/Half-Open/Closed:** failure-state transitions controlling call admission.
- **Idempotency terminal states:** PROCESSING/SUCCESS/FAILED/EXPIRED replay semantics.
- **Deferred verification:** accepted execution with delayed confirmation window.
- **Bulkhead isolation:** queue/resource partitioning to constrain failure impact.
- **Error budget:** permitted unreliability over fixed window before release freeze.

## Core Theme 1: Boundary Hardening

### Purpose
Ensure each execution step remains deterministic under retries, delays, and partial provider failures.

### Design Pattern
- Policy registry defines breaker thresholds and retry matrix.
- Idempotency middleware owns replay behavior.
- Queue isolation protects interactive paths.

### Benefits
- Predictable behavior under transient failures.
- Lower duplicate-write risk.
- Better incident triage with explicit terminal states.

### Tradeoffs
- More policy/config complexity.
- Requires strong integration tests to avoid policy drift.

### Implementation details
- Breaker defaults:
  - error_rate >25% (5m window)
  - p95 >15s (Tier 1/2), >45s (Tier 3)
  - min sample 10, cooldown 60s, close after 3 good probes
- Retry matrix by class:
  - 429: 3 exp retries + jitter, honor Retry-After
  - 5xx: 2 linear retries
  - timeout: 1 retry at 1.5x budget
  - connectivity: 3 immediate retries
  - schema: 1 reflexive fix attempt
- Queue TTL:
  - Tier 3 message_ttl_seconds default 900, cap 3600
  - expired -> dead-letter -> user-visible `expired_not_run`

## Core Theme 2: Governance and Recovery

### Purpose
Guarantee safe recoverability and auditable control in pre-apply, apply, and post-apply states.

### Design Pattern
- Mandatory verification oracle after tool success.
- Deferred verification state instead of silent failure.
- Kill-switches at global and tenant scope.
- RTO/RPO backed by backup/snapshot strategy.

### Benefits
- Prevents silent data drift.
- Supports incident response without global shutdown.
- Makes rollback decisions measurable.

### Tradeoffs
- Slightly higher latency on final status.
- Additional state transitions for operators to understand.

### Implementation details
- Verification polling: 5s, 10s, 15s (30s max)
- Unverified after window -> `DEFERRED_VERIFICATION`
- RTO/RPO:
  - tenant state: RTO <2m, RPO <=5m
  - full DB: RTO <1h, RPO <=6h
- Canary gate:
  - baseline = N-1 release
  - rollback if canary availability drops >5% with N>100 in matching scope

## Core Theme 3: Deployment, Observability, Security

### Purpose
Make production behavior explainable and enforceable for developers and operators.

### Design Pattern
- correlation_id propagated across all execution layers.
- SLI/SLO/error budget math used as release gate.
- Structured redaction primary, regex fallback secondary.
- Retention and deletion propagation are explicit.

### Benefits
- Faster root cause analysis.
- Better compliance posture.
- Lower risk of secret/PII leakage in logs.

### Tradeoffs
- Additional instrumentation overhead.
- Governance/reporting surface area increases.

### Implementation details
- Availability SLI:
  - successful_requests / (total_requests - user_errors)
  - target 99.9%
- Error budget:
  - 43m 12s / 30-day window
- Retention:
  - traces 14 days
  - audit logs 1 year
- Right-to-be-forgotten:
  - live purge <=48h
  - backup/snapshot purge <=14 days with audit trail

## Core Theme 4: Instrumentation Foundation

### Purpose
Capture high-quality data needed for future optimization and self-healing phases without enabling those loops now.

### Design Pattern
- Instrumentation only.
- Pair each Tier 2/3 execution with preference and oracle signals.

### Benefits
- Future DPO/RLVR readiness with lower rework.
- Better debugging of model and tool behavior.

### Tradeoffs
- Storage growth and data governance requirements.

### Required telemetry fields
- correlation_id, tier, preference_signal, oracle_signal, reasoning_trace_tokens, cost_usd.

## Comparison Table

| Option | Description | Strengths | Weaknesses | When to choose |
|---|---|---|---|---|
| A (minimal hardening) | 13-01 focused with partial 13-03 | Fastest | weak cost/fallback governance | emergency stabilization |
| B (balanced) | full 13-01..13-04 | best reliability/operability balance | moderate scope | current selected path |
| C (aggressive) | includes future-scope behavior | strongest resilience ceiling | highest schedule risk | only with extra capacity |

Preferred: **B**, as locked in context.

## Best Practices

### Setup
- Version all policy objects and include changed_by/effective_at.
- Predefine queue classes per tier.

### Implementation
- Enforce server-side policy for all tool calls.
- Keep idempotency terminal state checks centralized.
- Never finalize apply without oracle path assignment.

### Testing
- Contract-test each retry class and breaker transition.
- Test queue expiration/dead-letter/user status propagation.
- Test canary rollback trigger logic with baseline/scope constraints.

### Maintenance
- Review policy drift weekly from route/audit telemetry.
- Rotate secrets via deployment pipeline, not manual ad hoc steps.

### Scaling
- Tune queue concurrency and retry budgets by tier.
- Separate expensive Tier 3 workers from interactive pools.

## Edge Cases and Failure Modes

1. Provider recovery after prolonged outage with stale queue backlog.
- Detect: spike in expired tasks after restart.
- Prevent: TTL + dead-letter + no auto replay.

2. Duplicate side effects after partial timeout.
- Detect: repeated idempotency key hits with mixed terminal states.
- Prevent: strict PROCESSING/SUCCESS/FAILED/EXPIRED semantics.

3. Verification oracle false negatives under latency spikes.
- Detect: high deferred-verification rate with later success.
- Prevent: tuned polling windows and categorized deferred alerts.

4. Canary flapping from low sample size.
- Detect: rollback oscillation in low traffic segments.
- Prevent: enforce sample floor and scoped baseline matching.

## Implementation Playbooks

### Playbook: Reliability policy enforcement
- Preconditions: policy tables/migrations available.
- Steps:
  1. Evaluate route + policy snapshot.
  2. Compute idempotency key and terminal-state behavior.
  3. Execute with retry matrix.
  4. Update breaker state and telemetry.
  5. Return deterministic status payload.
- Validation: contract tests for each error class.

### Playbook: Post-execution verification
- Preconditions: oracle adapters available.
- Steps:
  1. tool returns provisional success.
  2. run polling 5/10/15s.
  3. set verified or deferred terminal state.
  4. notify user and audit.
- Validation: deferred and confirmed paths both test-covered.

## Open Questions and Gaps

1. Final provider-specific timeout budgets by operation class.
2. Initial canary scope partition strategy by tenant size.
3. Data retention overrides for enterprise/compliance tiers.

## Appendix: Checklist

- [ ] Versioned policy config schema exists.
- [ ] Retry matrix implemented and tested.
- [ ] Breaker transitions are deterministic and audited.
- [ ] Idempotency terminal states enforced.
- [ ] Queue TTL and dead-letter policies active for Tier 3.
- [ ] Verification oracle path covers deferred outcomes.
- [ ] SLI/SLO/error budget dashboard contract published.
- [ ] Retention/deletion propagation contract implemented.

