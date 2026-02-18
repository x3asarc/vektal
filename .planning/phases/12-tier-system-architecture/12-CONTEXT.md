# Phase 12: Tier System Architecture - Context (DRAFT LOCK)

Gathered: 2026-02-15
Status: Context locked for research kickoff

## Discussion Evidence

- questions_answered: 8
- areas_discussed:
  - Tier routing authority and permission model
  - Low-confidence routing fallback behavior
  - Tier 2 execution approvals and dry-run gates
  - Tier 3 delegation model and sub-agent constraints
  - Explainability model for standard and power users
  - Tenant-aware catalog/tool visibility
  - Failure fallback and model escalation policy
  - Cross-chat memory model and retrieval boundaries
  - Candidate future scope for self-healing dynamic scripting
- source: user decisions in active Phase 12 context discussion

<domain>

Phase boundary:
Implement routing-first capability control where effective capability is determined by policy-filtered tools, not separate product experiences.

Primary objective:
Each request is routed to Tier 1/2/3 with explainable policy decisions, safe execution boundaries, and approval-aware write semantics.

</domain>

<decisions>

## 1) Routing authority: permission-filtered toolbelt (approved)

- Backend policy engine is the authority.
- For each request, system computes effective_toolset = tier entitlements + tenant policy + active integrations + RBAC + runtime safety gates.
- LLM receives only effective tools. Unauthorized/unavailable tools are never exposed.

## 2) Low-confidence routing default: safe response + explicit escalation (approved)

- If intent confidence is low, default to Tier 1 read-safe path.
- UI shows a suggested escalation card (Tier 2/3) requiring explicit user confirmation.
- No silent escalation to mutating paths.

## 3) Tier 2 execution policy: semantic firewall (approved)

- READ operations: auto-execute.
- WRITE operations: require dry-run preview and explicit approval before apply.
- Approval unit for product mutations: per-product batch (not per-field click spam).

## 4) Tier 3 delegation: manager-worker with hard limits (approved with guardrails)

- Tier 3 may spawn bounded workers with minimal scoped tools.
- Required limits:
  - max delegation depth: 2
  - max worker fan-out per request: policy-defined
  - per-request budget/time caps
- Every delegation event must be auditable.

## 5) Explainability: progressive disclosure (adjusted)

- Default view: concise human-readable execution status and reason.
- Power view: structured execution log (tool calls, inputs/outputs metadata, decisions, timings, approvals).
- Do not expose raw chain-of-thought/internal reasoning.

## 6) Tenant catalog model: dynamic discovery (approved)

- Capability visibility = tier permission + tenant policy + active connection health.
- Example: Tier 3 user without Shopify connection does not see Shopify mutation skills.

## 7) Failure fallback and model escalation (adjusted)

Fallback chain:
1. deterministic tool-call repair + schema validation retry
2. bounded retry on same model
3. escalate to stronger model/provider behind abstraction
4. if still failing, return safe halt with actionable user prompt

- Escalation is policy-governed, cost-aware, and fully logged.

## 8) Cross-chat memory: PostgreSQL + pgvector with scoped retrieval (approved with safeguards)

- Use hybrid memory:
  - typed facts/preferences store (authoritative)
  - vector retrieval for semantic recall
- Retrieve top-k relevant memory snippets only.
- Default visibility: team-shared store memory, with RBAC boundaries.
- Prevent context poisoning using freshness, trust-score, and source tagging.

## 9) Additional architectural decisions locked from outliers

- Vendor field mapping:
  - Versioned supplier mapping profiles with typed transforms and required field validators.
  - Mapping change history is auditable and reversible.
- Dry-run TTL:
  - Default TTL 24h; pre-flight freshness check required before apply.
  - If stale, re-dry-run conflicted scope before execution.
- Retry logic (transient failures):
  - Exponential backoff + jitter, bounded attempts, idempotency keys, and terminal reason codes.
- Audit retention/export:
  - Immutable audit trail with retention policy (default 365d) and export endpoints (JSON/CSV).
- Protected columns:
  - System-critical fields are non-editable in bulk workflows by default; explicit elevated override required.
- Alt-text preservation:
  - Preserve existing alt text unless policy permits overwrite.
  - New assets require alt-text rule path (retain, generate, or manual review).

## 10) Snapshot and recovery baseline (locked)

- Snapshot before apply remains always-on in production.
- Product-targeted deltas are captured per apply scope; baseline snapshots are deduplicated.
- Deleted-target outcomes route to Recovery Logs with restore/re-create path.

## 11) Phase placement decision: self-healing dynamic scripting

- Recommendation: keep as separate Phase 15 (not Phase 14 core), due security and governance risk.
- Phase 14 remains governed optimization/learning.
- Phase 15 can add autonomous repair with mandatory sandbox, policy checks, and verification gates.

</decisions>

<specifics>

Implementation anchors for planning:

1. Policy resolver contract
- Inputs: user_id, tenant_id, tier, request_intent, active_integrations, rbac_context
- Outputs: route_decision, effective_toolset, approval_mode, explainability_payload

2. Approval contract
- For writes, dry-run payload must include before/after + conflicts + risk markers.
- Apply endpoint accepts only approved dry-run tokens.

3. Delegation contract
- manager_request_id links all worker tasks.
- Worker tool scopes are immutable after spawn.

4. Observability hooks
- route_decision event
- approval_requested/approved/rejected events
- delegation_spawned/completed events
- fallback_stage events

5. Explicit non-goals for Phase 12
- No autonomous code/script generation in production path.
- No deployment hardening implementation (Phase 13).
- No self-optimizing loops (Phase 14).

</specifics>

## Open questions to validate during research (not blockers)

1. Exact protected-column list by entity type.
2. Cost thresholds for model escalation.
3. Team memory conflict resolution policy (latest-wins vs confidence-wins vs human-resolved).
4. Recovery Logs UX placement and retention tiering.
