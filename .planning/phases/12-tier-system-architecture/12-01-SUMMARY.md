---
phase: 12-tier-system-architecture
plan: 01
subsystem: routing-foundation
tags: [tier-routing, policy, tool-projection, memory, contracts]
requires:
  - phase: 10-conversational-ai-interface
    provides: "chat session/action contracts and dry-run-first apply semantics"
  - phase: 11-product-search-discovery
    provides: "snapshot/recovery consistency patterns and contract-test posture"
provides:
  - "Deterministic route decision endpoint with explainability and runtime payload"
  - "Policy-filtered effective tool projection by tier/profile/tenant/integration/RBAC"
  - "Tenant-scoped memory retrieval endpoint with provenance metadata"
  - "Assistant routing/profile/memory/delegation persistence schema"
key-files:
  created:
    - src/models/assistant_tool_registry.py
    - src/models/assistant_tenant_tool_policy.py
    - src/models/assistant_profile.py
    - src/models/assistant_memory_fact.py
    - src/models/assistant_memory_embedding.py
    - src/models/assistant_route_event.py
    - src/models/assistant_delegation_event.py
    - migrations/versions/d4e5f6a7b8c9_phase12_tier_routing_and_profiles.py
    - src/assistant/policy_resolver.py
    - src/assistant/tool_projection.py
    - src/assistant/memory_retrieval.py
    - tests/api/test_chat_routing_contract.py
    - tests/api/test_tool_projection_contract.py
    - tests/api/test_assistant_profile_contract.py
    - tests/api/test_chat_memory_retrieval_contract.py
    - tests/api/test_tenant_rls_readiness_contract.py
  modified:
    - src/api/v1/chat/routes.py
    - src/api/v1/chat/schemas.py
    - src/models/__init__.py
completed: 2026-02-15
---

# Phase 12-01 Summary

Implemented the Tier System wave-1 routing foundation with backend-authoritative decisioning and deterministic capability projection.

## Delivered

- Added assistant governance persistence models:
  - canonical tool registry,
  - tenant tool policy overlays,
  - user/team assistant profiles with enabled-skill sets,
  - memory fact + embedding linkage,
  - auditable route events and delegation events.
- Added deterministic route API contracts:
  - `POST /api/v1/chat/route`,
  - `POST /api/v1/chat/tools/resolve`,
  - `POST /api/v1/chat/memory/retrieve`.
- Implemented policy projection order:
  - tier entitlement -> profile enabled skills -> integration readiness -> RBAC -> tenant overlay (deny precedence).
- Added wave-1 contract coverage:
  - routing determinism and hash stability,
  - profile enforcement (`TIER-07`),
  - tenant-scope/RLS-readiness contracts,
  - scoped memory retrieval provenance.

## Verification

- `python -m pytest -q tests/api/test_chat_routing_contract.py tests/api/test_tool_projection_contract.py tests/api/test_assistant_profile_contract.py tests/api/test_chat_memory_retrieval_contract.py tests/api/test_tenant_rls_readiness_contract.py`
- Result: `15 passed`, `0 failed`.

## Binary Gates

- `TIER-01`: `GREEN`
- `TIER-02`: `GREEN`
- `TIER-06`: `GREEN`
- `TIER-07`: `GREEN`

## Notes

- Migration `d4e5f6a7b8c9` is shared for wave-1 plus delegation schema primitives to avoid duplicate migrations and keep lineage centralized.
