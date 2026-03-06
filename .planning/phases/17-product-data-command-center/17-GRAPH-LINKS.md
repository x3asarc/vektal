# Phase 17 Graph Links (Neo4j/Graphiti Evidence)

Date: 2026-03-05
Source: Graphiti query layer via local snapshot fallback.

## Runtime backend status

Command:

```powershell
python scripts/graph/graph_status.py --json
```

Observed:

```json
{
  "backend": {
    "type": "local_snapshot",
    "reason": "neo4j_unreachable",
    "is_degraded": true
  },
  "sync": {
    "last_sync_at": "2026-03-01T16:29:28.676151",
    "success": true
  }
}
```

Notes:
- Graphiti/Neo4j access was attempted through project graph tooling.
- Because Aura/local Neo4j was unreachable, evidence below comes from `.graph/local-snapshot.json` through `execute_template(...)` queries.

## Query methods used

- `execute_template("imports", {"file_path": ...})`
- `execute_template("imported_by", {"file_path": ...})`
- `execute_template("functions_in_file", {"file_path": ...})`

## Dependency map for Phase 17 scope

### Frontend dashboard + chat

1. `frontend/src/app/(app)/dashboard/page.tsx`
- imports:
  - `frontend/src/app/(app)/dashboard/sections.ts`
  - `frontend/src/lib/auth/session-flags.ts`

2. `frontend/src/features/chat/components/ChatWorkspace.tsx`
- imports:
  - `frontend/src/components/OperationalErrorCard.tsx`
  - `frontend/src/features/chat/components/ActionCard.tsx`
  - `frontend/src/features/chat/components/MessageBlockRenderer.tsx`
  - `frontend/src/features/chat/hooks/useChatSession.ts`
  - `frontend/src/lib/diagnostics.ts`
- imported_by:
  - `frontend/src/app/(app)/chat/page.tsx`
  - `frontend/src/features/chat/components/ChatWorkspace.test.tsx`

3. `frontend/src/features/chat/hooks/useChatSession.ts`
- imports:
  - `frontend/src/features/chat/api/chat-api.ts`
  - `frontend/src/features/chat/hooks/useChatStream.ts`
  - `frontend/src/lib/api/client.ts`
  - `frontend/src/shared/contracts/chat.ts`

### Product data + lifecycle backend

4. `src/api/v1/products/routes.py`
- imports include:
  - `src/api/v1/products/schemas.py`
  - `src/api/v1/products/search_query.py`
  - `src/api/v1/products/staging.py`
  - `src/core/enrichment/capability_audit.py`
  - `src/core/enrichment/write_plan.py`
  - `src/jobs/progress.py`
  - `src/jobs/queueing.py`
  - `src/models/__init__.py`
- key functions found:
  - `list_products`, `get_product`, `search_products`
  - `get_product_history`, `get_product_diff`
  - `enrichment_run_start`, `enrichment_run_review`, `enrichment_run_approve`, `enrichment_run_apply`

5. `src/api/v1/chat/routes.py`
- imports include:
  - `src/api/v1/chat/orchestrator.py`
  - `src/api/v1/chat/approvals.py`
  - `src/api/v1/chat/bulk.py`
  - `src/assistant/*` runtime/governance layers
- key functions found:
  - `create_session`, `create_message`, `create_bulk_action`
  - `approve_action`, `apply_action`, `delegate_action`
  - `stream_session`

### Versioning / rollback primitives

6. `src/models/product.py`
- imported_by:
  - `src/api/v1/products/search_query.py`
  - `src/resolution/adapters/shopify_adapter.py`
  - `src/resolution/preflight.py`

7. `src/models/product_change_event.py`
- append-only event model already present.

8. `src/models/resolution_snapshot.py`
- imported_by includes:
  - `src/resolution/snapshot_lifecycle.py`
  - `src/resolution/preflight.py`
  - `src/resolution/apply_engine.py`
  - `src/api/v1/resolution/routes.py`

9. `src/resolution/snapshot_lifecycle.py`
- imports:
  - `src/models/resolution_batch.py`
  - `src/models/resolution_snapshot.py`
- key functions found:
  - `capture_snapshot`
  - `ensure_store_baseline`
  - `resolve_snapshot_chain`
  - `is_batch_fresh`

### Ingest orchestration

10. `src/tasks/ingest.py`
- imports:
  - `src/jobs/orchestrator.py`
  - `src/jobs/finalizer.py`
  - `src/celery_app.py`

## Phase 17 planning implication

Graph evidence confirms strong reusable foundations in:
- chat orchestration + transport
- product APIs (including history/diff)
- snapshot lifecycle + rollback chain primitives
- ingest job framework (Celery/Redis)

Primary planned additions for Phase 17 are:
- product-field completeness intelligence layer
- Shopify product webhook + reconciliation listener path
- dashboard command-center metrics APIs and visualization surfaces
- tighter chat clarifier loop + dashboard-first orchestration entrypoints
