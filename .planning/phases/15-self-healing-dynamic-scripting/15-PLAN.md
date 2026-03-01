# Phase 15: Self-Healing & Runtime Optimization - Plan

**Status**: PLANNED
**Depends on**: Phase 14 (Codebase Knowledge Graph)
**Branch**: `feat/phase-15-self-healing`
**Tagged**: `[developer-facing]` `[autonomous]` `[optimization]`

---

## Goal

Implement autonomous self-healing and runtime optimization loops that leverage the codebase knowledge graph to remediate failures and optimize performance without human intervention.

---

## Operational Prerequisites (Sentry Feedback Loop)

1. `.env` contains `SENTRY_AUTH_TOKEN` for issue status read access.
2. `.env` contains `SENTRY_ORG_SLUG` and `SENTRY_PROJECT_SLUG` for deterministic closure checks.
3. Sentry token handling follows least-privilege and never hardcodes tokens in code or committed docs.
4. If Sentry credentials are missing, Phase 15 loop runs in degraded mode with autonomous promotion disabled.

---

## Implementation Sequence

### Wave 1: Autonomous Remediation Loop
- **15-01**: Sandbox execution environment with 6-gate verification
- **15-02**: Failure detection and root-cause classifier (LLM + Graph)
- **15-03**: Autonomous fix generation and implementation
- **15-03b**: Sentry issue triage orchestrator (issue ingest -> normalize -> classify -> remediation candidate)

### Wave 2: Runtime Optimization
- **15-04**: Performance profiling and bottleneck identification
- **15-05**: Autonomous cost and latency optimization (Cache TTL, connection pools)

### Wave 3: Persistent Learning & Infra Agent
- **15-06**: **Autonomous Infrastructure & Bash Agent**:
    - Probes and remediates infrastructure failures (Redis, Neo4j, PostgreSQL)
    - Has bash access for logs, service status, and restarts
    - Implements automated "remediation recipes" for common environment blocks
- **15-07**: **Learnings Loop**:
    - Turns repeated failures into high-confidence reusable fix recipes
    - Injects validated remedies into next-prompt context automatically
    - Updates `FAILURE_JOURNEY.md` and knowledge graph with remediation outcomes

### Wave 4: Closed-Loop Observability Integration
- **15-08**: **Sentry Feedback Closure**:
    - Reads Sentry issue status transitions after remediation attempts
    - Correlates remediation run ids with issue fingerprints
    - Marks remedies as validated only after issue regression window passes
- **15-09**: **Autonomous Prompt-Memory Promotion**:
    - Promotes only validated remedies into next-prompt memory context
    - Expires stale/low-confidence remedies automatically
    - Emits audit artifacts for every promotion/demotion decision

---

## Success Criteria

1. Autonomous remediation passes all 6 verification gates before applying to production.
2. System fixes 95% of transient issues (infra downtime, timeouts) without human intervention.
3. Performance hot paths are optimized automatically based on real-world telemetry.
4. Learnings from solved problems are persisted and prevent recurrence.
5. All autonomous actions are auditable through reasoning traces in Neo4j.
6. Sentry-driven issues are triaged into machine-readable categories with remediation routing in under 5 minutes.
7. Only remedies with verified post-fix stability are promoted into autonomous prompt memory.
