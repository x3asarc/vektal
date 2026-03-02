# Knowledge Graph Availability Runbook

## Overview
The Shopify Multi-Supplier Platform uses a Neo4j-based knowledge graph for codebase analysis and assistant intelligence. This runbook describes how the system maintains availability through an autonomous three-tier fallback cascade.

## The Fallback Cascade
The system automatically resolves the best available graph backend:
1.  **Aura (Cloud)**: Primary, high-availability knowledge base.
2.  **Local Neo4j (Docker)**: Fallback for local development or cloud downtime.
3.  **Local Snapshot (Read-Only)**: File-based JSON fallback for total downtime.

## Prerequisites
*   **Aura Credentials**: `AURA_CLIENT_ID`, `AURA_CLIENT_SECRET`, `AURA_TENANT_ID`, `AURA_INSTANCE_ID` in `.env`.
*   **Local Neo4j**: Docker Desktop or Docker Engine installed and running.
*   **Python Dependencies**: `neo4j`, `graphiti-core`, `httpx` installed in venv.

## Manual Intervention Procedures

### 1. Forcing a Backend Reset
If the system is stuck on a stale backend manifest:
```bash
python scripts/graph/bootstrap_graph_backend.py
```
This forces a re-probe of the entire cascade and updates `.graph/runtime-backend.json`.

### 2. Manual Snapshot Rebuild
If the local snapshot is corrupt or missing:
```bash
# Via Registry
python -c "from src.graph.remediation_registry import registry; registry.get_tool('local_snapshot').diagnose_and_fix()"
```

### 3. Aura Resume
If your Aura instance is paused:
```bash
# Via Registry
python -c "from src.graph.remediation_registry import registry; registry.get_tool('aura').diagnose_and_fix({'action': 'resume'})"
```

## Troubleshooting Guide

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| `⚠️ [Backend: LOCAL_SNAPSHOT]` | Aura and Local Neo4j are down. | Start Docker or check Aura Console. |
| `❌ [Backend: UNKNOWN]` | Manifest missing. | Run `bootstrap_graph_backend.py`. |
| `Sync status: ❌` | Pipeline failure. | Run `scripts/graph/sync_to_neo4j.py --full`. |
| `UnicodeEncodeError` | Terminal charset mismatch. | Set `$env:PYTHONUTF8=1`. |

## Status Commands Reference
*   **General Status**: `python scripts/graph/graph_status.py`
*   **Machine-Readable**: `python scripts/graph/graph_status.py --json`
*   **Bootstrap**: `python scripts/graph/bootstrap_graph_backend.py`

## Automation Hooks
Agent hooks are configured to run `pretool_gate.py` before tool use in:
*   `.claude/settings.local.json`
*   `.gemini/preToolUseHook.sh`
*   `.codex/preToolUseHook.sh`

`pretool_gate.py` enforces:
1. Sentry worker gate (`scripts/observability/ensure_sentry_worker.py`)
2. Graph backend bootstrap (`scripts/graph/bootstrap_graph_backend.py`)

This means each session/tool cycle is autonomous:
- If Sentry puller daemon is active and healthy, gate is a no-op and execution continues.
- If inactive, gate launches daemon mode (`scripts/observability/sentry_issue_puller.py --daemon`) automatically.
