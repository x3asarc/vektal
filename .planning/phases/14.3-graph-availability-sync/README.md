# Phase 14.3: Graph Availability + Sync Reliability

**Status**: PLANNED
**Depends on**: Phase 14.2 (Tool Calling 2.0 Integration)
**Created**: 2026-02-26
**Tagged**: `[developer-facing]` `[knowledge-graph]` `[reliability]`

---

## What This Phase Does

Makes Neo4j-backed graph access resilient across session environments (Codex, Claude, Gemini) by enforcing:
1. Aura-first connection policy with health checks.
2. Automatic local Neo4j fallback when Aura is unavailable.
3. Guaranteed queryability through a local snapshot backend when no live graph is reachable.
4. Explicit sync status so "auto vs manual" is always visible.
5. Sentry issue ingestion bridge for external failure signals into remediation routing.

---

## Why This Exists

Phase 14.2 optimizes tool-calling behavior. It does not guarantee runtime graph availability or auto-sync reliability.

Phase 14.3 closes that gap so MCP tool flows remain operational even during Aura outage, local Docker downtime, or credential drift.

---

## Core Outcome

`query_graph` and graph-adjacent MCP workflows must remain available in this priority chain:
1. `aura`
2. `local_neo4j` (auto-started if needed)
3. `local_snapshot` (read-only fallback)

Every query response must declare `backend_source` and `sync_freshness` metadata.

Sentry-derived failures are normalized into the same taxonomy before remediation dispatch, so production incidents can feed the autonomous loop without bypassing governance.

---

## Plan

See `14.3-PLAN.md` for implementation waves, acceptance criteria, and verification evidence.
