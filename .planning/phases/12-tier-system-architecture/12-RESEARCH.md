# Phase 12: Tier System Architecture - Research

**Researched:** 2026-02-15  
**Domain:** Capability-based routing and governed tool execution for Tier 1/2/3 assistant runtimes  
**Confidence:** HIGH (architecture and contracts), MEDIUM-HIGH (runtime tuning depends on production telemetry)

<phase_context>
## Locked Context Inputs

- Tier control is capability-based (permission-filtered toolbelt), not separate UX silos.
- Backend policy engine is routing authority.
- Low confidence defaults to safe Tier 1 response + explicit escalation prompt.
- Tier 2 semantic firewall: READ auto-exec, WRITE requires dry-run + approval.
- Tier 3 may delegate to bounded workers with strict limits and full audit.
- Explainability uses progressive disclosure; no chain-of-thought exposure.
- Capability visibility is tenant- and integration-aware.
- Fallback uses deterministic repair/retry before model escalation.
- Cross-chat memory uses typed facts + pgvector retrieval with RBAC.
- Additional lock-ins: vendor mapping versioning, dry-run TTL, retry policy, retention/export, protected columns, alt-text governance.
</phase_context>

## Executive Summary

Phase 12 should be implemented as a **policy + routing control plane** layered on top of existing dry-run/apply safety infrastructure (Phase 8/10/11), not as a rewrite.

Primary outcome:
- Every request gets a deterministic `route_decision` and an `effective_toolset`.
- The model only receives tools the policy engine allows.
- Write operations remain dry-run first, approval-gated, and auditable.

Best implementation sequence:
1. `12-01`: Policy resolver + tier router + explainability payload contract.
2. `12-02`: Tier 1/2 runtime wiring with semantic firewall and approval handoff.
3. `12-03`: Tier 3 manager-worker delegation with bounded recursion, budget, and traceability.

## Internal Baseline Findings (Current Repo)

### What already exists and should be reused

- User tier model exists: `src/models/user.py` (`tier_1`, `tier_2`, `tier_3`).
- Tier-aware API rate limiting exists: `src/api/core/rate_limit.py`.
- Dry-run/approval/apply safety chain exists:
  - `src/api/v1/chat/orchestrator.py`
  - `src/api/v1/chat/approvals.py`
  - `src/api/v1/resolution/routes.py`
  - `src/resolution/policy.py`
  - `src/resolution/preflight.py`
- Protected-column and alt-text policy gates already exist in staging:
  - `src/api/v1/products/staging.py`
  - `src/api/v1/products/schemas.py`

### Gaps that Phase 12 must close

- No canonical `effective_toolset` policy resolver yet.
- No explicit tier router contract (`route_decision`, confidence, fallback stage).
- No tenant/integration-aware tool registry projection.
- No Tier 3 delegation runtime contract (worker scope immutability, depth limits).
- No unified routing event telemetry schema.

## External Research Synthesis (Context7 + Local Precision Workspace)

### Context7 Evidence (Primary)

1. PostgreSQL 16 (`/websites/postgresql_16`)
- RLS requires explicit enablement and policy definitions.
- `USING` and `WITH CHECK` should be separated for read vs write guarantees.
- `BYPASSRLS` and owner semantics must be controlled.
- `FORCE ROW LEVEL SECURITY` should be used where owners must not bypass policy.

2. pgvector (`/pgvector/pgvector`)
- HNSW and IVFFlat are both viable; HNSW generally stronger recall, IVFFlat lower build/memory cost.
- Vector search should be combined with normal SQL filters and indexes for tenant/user scoping.
- Query-time controls (`ef_search`, `probes`) are required to balance latency vs recall.

3. Celery (`/websites/celeryq_dev_en_stable`)
- Official retry controls support `autoretry_for`, `retry_backoff`, `retry_jitter`, and `max_retries`.
- External API/tool failures should use bounded retries + jitter and idempotent execution semantics.
- For long-running external operations, `task_acks_late=True` and `worker_prefetch_multiplier=1` improve fairness and failure recovery (with idempotency requirement).

### Precision Workspace Crossovers Used

From `precisionworkspace.md`, the following directly strengthens Phase 12:
- Permission-filtered tool visibility (avoid “tool confusion”).
- Mandatory dry-run for all mutations.
- Per-product action approvals.
- Protected-column immutability patterns.
- Recovery-log-first operational transparency.

## Deepening Pass (Added Before Planning)

### A) Tenant Isolation Pattern (PostgreSQL RLS)

Recommended production pattern for Phase 12 groundwork:
1. Enable RLS on tenant-scoped tables.
2. Use explicit `USING` (read) and `WITH CHECK` (write) policies.
3. Apply `FORCE ROW LEVEL SECURITY` where owner-bypass is unacceptable.
4. Set tenant context per request/transaction (`SET LOCAL`) and reference via `current_setting(...)` in policies.

Illustrative policy shape:
- `tenant_id = current_setting('app.tenant_id', true)::int`

Research implication:
- Even if full hardening is Phase 13, Phase 12 contracts should be authored to be RLS-ready (no API shape that assumes cross-tenant unrestricted reads).

### B) Queueing and Retry Reliability (Celery)

Phase 12 planning should assume queue specialization:
- `tier1_read`, `tier2_exec`, `tier3_orchestrator` queues.
- Router uses task routes to map workload class to queue/priority.

Reliability baseline:
- `task_acks_late=True`
- `worker_prefetch_multiplier=1`
- bounded retries with exponential backoff + jitter
- idempotency keys on all mutating apply pathways

Research implication:
- Tier routing is not only model/tool selection; it must include queue/QoS selection in the routing decision payload.

### C) Memory Retrieval Quality (pgvector)

Recommended query strategy:
1. Filter first by tenant/store/RBAC metadata.
2. Vector rank within filtered candidate set.
3. Use tuned ANN parameters (`hnsw.ef_search` or `ivfflat.probes`) per query class.
4. For mixed recall needs, use hybrid rank fusion (text + vector) for higher precision.

Research implication:
- Phase 12 should include a retrieval policy object in routing (`memory_mode`, `top_k`, `filters`, `quality_profile`) rather than a single hardcoded retrieval path.

### D) Explainability Contract Hardening

Add explicit event fields for consistent traceability:
- `route_decision_id`
- `policy_snapshot_hash`
- `effective_toolset_hash`
- `fallback_stage`
- `delegation_parent_request_id`

Research implication:
- These fields should be locked as required in Phase 12 plan contracts to avoid later migration churn.

## Recommended Architecture

### 1) Policy Resolver (authoritative)

Introduce a resolver service:
- Input: `user_id`, `tenant_id`, `user_tier`, `intent`, `requested_capability`, `active_integrations`, `rbac_context`.
- Output:
  - `route_decision`: `tier_1|tier_2|tier_3|blocked`
  - `effective_toolset`: filtered list of tool IDs
  - `approval_mode`: `none|product_scope|required_before_apply`
  - `explainability_payload`: short reason + trace references
  - `fallback_plan`: deterministic fallback ladder

Hard rule:
- Resolver output is signed/immutable for the request lifecycle. The model cannot self-upgrade tools.

### 2) Tool Registry and Capability Projection

Maintain a canonical registry:
- `tool_id`, `risk_class`, `requires_integration`, `required_role`, `allowed_tiers`, `mutates_data`, `domain`.

Effective capability for each request:
- `allowed = tier_allowlist ∩ rbac_allowlist ∩ tenant_policy ∩ integration_health`.

### 3) Tier Runtime Contracts

Tier 1:
- Read-safe responses, no privileged mutations.
- Can propose escalation card when confidence/intent requires.

Tier 2:
- Skills/workflows execution.
- READ tools may auto-run.
- WRITE tools require dry-run token + product-scope approval before apply.

Tier 3:
- Manager-worker orchestration.
- Worker spawn constraints:
  - max depth `2`
  - bounded fan-out
  - strict budget/time cap
  - immutable worker tool scope
- Every spawn/complete/fail event must be persisted.

### 4) Fallback and Reliability Path

Execution fallback order:
1. Tool-call normalization + schema repair
2. bounded same-model retry
3. stronger model/provider escalation (policy + cost constrained)
4. safe halt with required user action

All stages emit structured `fallback_stage` events for audit and tuning.

### 5) Memory Architecture

Use a hybrid memory approach:
- Typed memory tables for authoritative rules/preferences.
- pgvector for semantic recall of relevant prior context.

Retrieval contract:
- top-k (`3-5`) scoped by tenant and RBAC.
- freshness threshold + trust score + provenance in prompt metadata.
- never include untrusted or expired memory without explicit marker.

## Data Model and Persistence Contracts

Phase 12 additions (minimum):
1. `assistant_tool_registry`
2. `assistant_tenant_tool_policy`
3. `assistant_route_event`
4. `assistant_delegation_event`
5. `assistant_memory_fact` (typed)
6. `assistant_memory_embedding` (vector rows linked to typed facts)

Phase 12 extensions to existing tables:
- Add `route_decision_id` / `policy_snapshot` refs to chat action/session records.
- Preserve dry-run id linkage for every mutating action (already mostly present).

## API Contract Targets (Phase 12)

1. `POST /api/v1/chat/route`
- Returns `route_decision`, `effective_toolset`, `confidence`, `reasons`, `fallback_plan`.

2. `POST /api/v1/chat/tools/resolve`
- Returns capability projection for current user/tenant/session state.

3. `POST /api/v1/chat/actions/{id}/delegate`
- Tier 3 manager-only endpoint for worker spawn under policy constraints.

4. `GET /api/v1/chat/actions/{id}/trace`
- Returns progressive disclosure payload:
  - summary
  - tool events
  - approvals
  - fallback stages
- Must not expose chain-of-thought.

5. `POST /api/v1/chat/memory/retrieve`
- Returns scoped top-k memory snippets + provenance for this request.

## Security, Governance, and Compliance Notes

- Enforce deny-by-default on tool access.
- Use server-side policy checks for all tool calls (never trust client tier claims).
- Use RLS for tenant-bound memory and routing event data where applicable.
- Keep immutable audit events for:
  - route decisions
  - tool projections
  - approvals
  - delegation and fallback transitions

## Requirement Mapping

| Requirement | Research-Derived Contract |
|---|---|
| TIER-01 | Policy resolver + capability matrix with deterministic tool filtering. |
| TIER-02 | Route decision contract with confidence, reasons, and fallback metadata. |
| TIER-03 | Tier 1 read-safe path with escalation prompts only. |
| TIER-04 | Tier 2 semantic firewall; write actions require dry-run + approval. |
| TIER-05 | Tier 3 manager-worker delegation with depth/fan-out/budget limits. |
| TIER-06 | Tier-aware capability disclosure from server-side effective toolset projection. |
| TIER-07 | Tenant/user profile + RBAC + integration-health-based tool visibility. |
| TIER-08 | Clear downgrade/escalation UX continuity path and safe fallback behavior. |

## Open Decisions (Research-validated, not blockers)

1. Exact protected-column matrix by entity type and role.
2. Numeric cost thresholds for model escalation by tier.
3. Memory conflict resolution priority (`human override` vs `latest` vs `confidence`).
4. Whether RLS is enforced in DB now (Phase 12) or fully hardened in Phase 13.

## Key Risks and Mitigations

1. Policy bypass via direct tool invocation
- Mitigation: all tool calls must pass server-side resolver and signed policy snapshot.

2. Delegation explosion in Tier 3
- Mitigation: hard depth/fan-out limits + budget caps + cancellation controls.

3. Memory poisoning or stale retrieval
- Mitigation: trust/freshness/provenance gates + scoped top-k retrieval.

4. Retry storms and repeated side effects
- Mitigation: bounded retries + jitter + idempotency keys + terminal reason codes.

5. Operator confusion on why route/tool was chosen
- Mitigation: progressive explainability with short reason + trace viewer.

## Next Step Output Targets

For planning (`12-01`/`12-02`/`12-03`), this research should produce:
- Resolver interface spec and policy snapshot schema.
- Tool registry schema and seed policy matrix.
- Tier runtime state diagrams.
- Delegation guardrail constants and failure handling contract.
- Test matrix:
  - authorization bypass tests
  - fallback ladder tests
  - dry-run write-gate tests
  - delegation limit tests
- memory scope/RBAC leakage tests

Deepening add-ons:
- RLS-readiness tests for tenant-scoped queries and writes.
- queue routing tests (tier -> queue/QoS) under concurrent load.
- fallback-stage telemetry completeness tests.

## Context7 Traceability

- `/websites/postgresql_16`: RLS enablement, policy semantics, `FORCE RLS`, `BYPASSRLS`.
- `/pgvector/pgvector`: index strategy (HNSW/IVFFlat), filtered retrieval patterns, tuning knobs.
- `/websites/celeryq_dev_en_stable`: retry/backoff/jitter semantics and bounded retry configuration.
