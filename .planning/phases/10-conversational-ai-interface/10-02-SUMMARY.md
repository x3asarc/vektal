---
phase: 10-conversational-ai-interface
plan: 02
subsystem: api
tags: [chat, dry-run, approvals, single-sku, safety-gates]
requires:
  - phase: 10-conversational-ai-interface
    provides: "10-01 chat session/message/action API foundation"
  - phase: 08-product-resolution-engine
    provides: "dry-run, preflight, apply, recovery-log contracts"
provides:
  - "Single-SKU mutating chat intents converted into dry-run action proposals"
  - "Product-scoped approve/apply endpoints with selective field overrides"
  - "Draft-first create semantics with explicit publish gate metadata"
  - "Variant expansion path contract routed to productVariantsBulkCreate when needed"
affects: [phase-10-03-bulk-chat-orchestration, phase-10-04-chat-ui]
tech-stack:
  added: [chat orchestrator module, chat approvals module, single-sku workflow tests]
  patterns: [dry-run-before-apply, product-scope-approval, preflight-conflict-hold, recovery-linkage]
key-files:
  created:
    - src/api/v1/chat/orchestrator.py
    - src/api/v1/chat/approvals.py
    - tests/api/test_chat_single_sku_workflow.py
    - frontend/src/shared/contracts/chat.ts
  modified:
    - src/api/v1/chat/routes.py
    - src/api/v1/chat/schemas.py
    - src/api/v1/resolution/routes.py
    - src/resolution/shopify_graphql.py
    - tests/api/test_chat_contract.py
    - frontend/src/shared/contracts/index.ts
key-decisions:
  - "Mutating chat intents are limited to add/update product and always emit a dry-run proposal first."
  - "Approval is server-enforced at product action scope, with optional field-level overrides."
  - "Apply is hard-gated by approval + preflight; conflicts are held and linked to Recovery Logs."
patterns-established:
  - "Chat orchestration reuses shared resolution route contracts instead of creating parallel write paths."
  - "Create semantics are explicit in payload (`draft_first`, `publish_allowed`) and never implicitly publish."
duration: 105min
completed: 2026-02-15
---

# Phase 10-02 Summary

Phase `10-02` delivered the single-SKU conversational write workflow with strict dry-run, approval, and apply safety gates.

## Accomplishments

- Added deterministic single-SKU orchestrator:
  - parses SKU/URL + intent + hints
  - builds dry-run proposal through shared resolution contract
  - emits structured `diff/action` blocks for UI
  - annotates create semantics (`draft_first`, explicit publish policy) and variant mutation path
- Added product-scoped approvals/apply controls:
  - `POST /api/v1/chat/sessions/{id}/actions/{action_id}/approve`
  - `POST /api/v1/chat/sessions/{id}/actions/{action_id}/apply`
  - supports selective `change_id` selection, field overrides, and comments
- Enforced dry-run-first + preflight gating:
  - apply without approval returns deterministic `409 approval-required`
  - preflight conflicts hold apply and mark action `conflicted`
  - recovery log references returned on conflicted flow
- Added/updated chat contracts for frontend integration:
  - API schemas for `action_hints`, approval/apply requests
  - frontend chat contract types in `frontend/src/shared/contracts/chat.ts`

## Verification Runs

- Command:
  - `python -m pytest -q tests/api/test_chat_contract.py tests/api/test_chat_stream.py tests/api/test_chat_single_sku_workflow.py tests/api/test_endpoints.py`
- Result:
  - `24 passed`, `0 failed`

## Issues Encountered

- SKU extraction edge-case on phrases like `update SKU-100` could yield malformed entity (`-100`) from upstream classifier pattern.
- Fixed by validating entity SKU and falling back to robust token extraction in orchestrator.

## Outcome Against Plan Gates

- Dry-run required for single-SKU mutating operations: **met**
- Product-scoped approvals with selective overrides: **met**
- Draft-first create + explicit publish gating semantics: **met**
- Conflict/low-confidence decision gating with recovery linkage: **met**

---
*Phase: 10-conversational-ai-interface*
*Completed: 2026-02-15*
