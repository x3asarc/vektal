# Phase 14.3: Graph Availability + Sync Reliability - README

## Overview
This phase implements a robust infrastructure layer that guarantees graph context availability through a three-tier fallback strategy (Aura → local Neo4j → snapshot) with autonomous failure resolution.

## Plan Index
- [x] **14.3-01: Backend Resolver Contract + Runtime Manifest** (Wave 1)
- [x] **14.3-02: Shared Bootstrap Command + Local Neo4j Auto-start** (Wave 1)
- [x] **14.3-03: Sync Status Contract + Metadata Updates** (Wave 2)
- [x] **14.3-04: PreTool/Session Integration** (Wave 2)
- [x] **14.3-05: MCP Response Metadata + Degraded-mode Guardrails** (Wave 3)
- [x] **14.3-06: Governance Availability Gate + Integration Tests** (Wave 3)
- [x] **14.3-07: Sentry Issue Ingestion + Autonomous Triage Normalization** (Wave 4)

## Success Criteria
- [x] Graph reads succeed via Aura, Local, or Snapshot.
- [x] Aura outage triggers automatic local Neo4j startup.
- [x] MCP responses include `backend_source` and freshness metadata.
- [x] Mutations blocked in Snapshot mode.
- [x] Sentry issues ingested and mapped to failure taxonomy.
