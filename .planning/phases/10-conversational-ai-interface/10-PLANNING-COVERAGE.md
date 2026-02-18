# Phase 10 Planning Coverage

**Phase:** 10-conversational-ai-interface
**Generated:** 2026-02-15
**Source inputs:** `10-CONTEXT.md`, `10-RESEARCH.md`

## Requirement Trace

| Requirement | Covered In | Notes |
|---|---|---|
| CHAT-01 (ChatGPT-style UI) | `10-04` Task 1+2 | Full `/chat` workspace with message blocks + action cards |
| CHAT-02 (Streaming responses) | `10-01` Task 3, `10-04` Task 2 | SSE streaming contracts and frontend stream rendering |
| CHAT-03 (Context states) | `10-01` Task 1+2, `10-04` Task 1 | `at_door` vs `in_house` session state machine |
| CHAT-04 (Single SKU workflow) | `10-02` Task 1+2+3 | SKU/URL -> dry-run -> product-scoped approval -> apply |
| CHAT-05 (Bulk SKU processing) | `10-03` Task 1+2 | Up to 1000 SKUs with auto-chunking + queue |
| CHAT-06 (Parallel agent spawning) | `10-03` Task 1+2+3 | Adaptive concurrency and conflict-aware chunk orchestration |
| CHAT-07 (Natural language parsing) | `10-01` Task 2, `10-02` Task 1 | Intent/entity extraction expanded for SKU lists + URLs |
| CHAT-08 (Structured formatting) | `10-01` Task 2, `10-04` Task 1 | Typed response blocks and deterministic render contracts |

## Plan Waves

1. **Wave 1 (`10-01`)**: backend chat API/contracts, session state, and stream transport foundation.
2. **Wave 2 (`10-02`)**: single-SKU read/write orchestration with mandatory dry-run and product-scoped approvals.
3. **Wave 3 (`10-03`)**: bulk orchestration (up to 1000 SKUs), adaptive chunk concurrency, aggregated progress, and safety gates.
4. **Wave 4 (`10-04`)**: frontend chat workspace, streaming UX, approval controls, and integration hardening.

## Verification Contract (Mandatory)

- Backend (`10-01`, `10-02`, `10-03`):
  - `tests/api/test_chat_contract.py`
  - `tests/api/test_chat_stream.py`
  - `tests/api/test_chat_single_sku_workflow.py`
  - `tests/api/test_chat_bulk_workflow.py`
  - `tests/unit/test_chat_router.py`
- Frontend (`10-04`):
  - `frontend/src/app/(app)/chat/page.test.tsx`
  - `frontend/src/features/chat/components/ChatWorkspace.test.tsx`
  - `frontend/src/features/chat/hooks/useChatStream.test.ts`
  - `frontend/src/features/chat/components/ActionCard.test.tsx`
  - `frontend` typecheck

## Explicit Out-of-Scope (from context/research)

- Autonomous self-learning source expansion loops (Phase 14).
- Google-Docs-style concurrent live co-editing.
- Replacing Phase 8 apply engine or Phase 9 progress transport with parallel systems.

## Required Alignment Updates During Execution

- Update `.planning/REQUIREMENTS.md` wording for `CHAT-05` to match locked context (`up to 1000` with auto-chunking).
- Ensure snapshot policy language remains non-disableable in production documentation/contracts.
