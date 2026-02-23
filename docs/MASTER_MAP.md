# MASTER_MAP

Last batch update: 2026-02-23
Owner: ContextCurator

## TOC
1. Project Map (depth 3)
2. Module Index
3. Data and Logic Flow
4. Active Plans
5. Governance Links
6. Journey Synthesis Links

## Project Map (Depth 3)
```text
.
|-- AGENTS.md
|-- STANDARDS.md
|-- .rules
|-- FAILURE_JOURNEY.md
|-- solutionsos/
|   `-- compound-engineering-os-policy.md
|-- .planning/
|   |-- ROADMAP.md
|   |-- STATE.md
|   |-- PROJECT.md
|   |-- REQUIREMENTS.md
|   |-- phases/
|   |   |-- 07-frontend-framework-setup/
|   |   `-- ...
|   `-- archive/
|-- reports/
|   |-- 07/
|   |   |-- 07.1-governance-baseline-dry-run/
|   |   `-- 07.2-governance-operational-defaults/
|   |-- meta/
|   `-- templates/
|-- ops/
|   |-- STRUCTURE_SPEC.md
|   `-- governance/
|       `-- roles/
|-- docs/
|   |-- MASTER_MAP.md
|   `-- INDEX.md
|-- src/
|   `-- ...
|-- tests/
|   `-- ...
|-- frontend/
|   `-- ...
|-- scripts/
|   `-- ...
`-- config/
    `-- ...
```

## Module Index
1. Governance:
   - `AGENTS.md`: governance constitution and role boundaries.
   - `STANDARDS.md`: review severity model and two-pass review protocol.
   - `.rules`: machine-checkable policy lines.
   - `ops/governance/roles/README.md`: canonical role definitions and links.
2. Planning:
   - `.planning/ROADMAP.md`: canonical phase state and phase details.
   - `.planning/STATE.md`: live state, blockers, gate snapshots.
   - `.planning/phases/`: phase-level plans, context, and research artifacts.
3. Evidence:
   - `reports/<phase>/<task>/`: four required closure reports.
   - `reports/meta/`: cross-phase synthesis reports.
   - `scripts/governance/validate_governance.py`: task gate validator.
4. Structure and context:
   - `ops/STRUCTURE_SPEC.md`: placement and protected path contract.
   - `docs/MASTER_MAP.md`: this project map and links.
5. Product code:
   - `src/`: backend/core implementation.
   - `frontend/`: Next.js UI implementation.
   - `tests/`: automated verification.

## Data and Logic Flow
1. Requirements and decisions are captured in `.planning`.
2. A task plan is created under `.planning/phases/<phase>/<task>/PLAN.md`.
3. Builder executes and publishes task evidence in `reports/<phase>/<task>/`.
4. Reviewer performs blind-first then context-fit two-pass audit.
5. StructureGuardian and IntegrityWarden publish final compliance reports.
6. PhaseManager updates `.planning/STATE.md` and `.planning/ROADMAP.md`.
7. ContextCurator updates this map at daily batch and phase close.

## Active Plans
1. Phase 14.1 execution artifacts:
   - `.planning/phases/14.1-rag-enhancement/14.1-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-CROSS-REFERENCE.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-RESEARCH.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-01-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-02-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-03-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-04-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-05-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-06-PLAN.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-01-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-02-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-03-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-04-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-05-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-06-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-SUMMARY.md`
   - `.planning/phases/14.1-rag-enhancement/14.1-EXECUTION-VALIDATION.md`
2. Phase 13 canonical artifacts:
   - `.planning/phases/13-integration-hardening-deployment/13-PRE-CONTEXT-SCOPE.md`
   - `.planning/phases/13-integration-hardening-deployment/13-CONTEXT.md`
   - `.planning/phases/13-integration-hardening-deployment/13-RESEARCH.md`
   - `.planning/phases/13-integration-hardening-deployment/13-PLANNING-COVERAGE.md`
   - `.planning/phases/13-integration-hardening-deployment/13-01-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-02-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-03-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-04-PLAN.md`
   - `.planning/phases/13-integration-hardening-deployment/13-01-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-02-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-03-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-04-SUMMARY.md`
   - `.planning/phases/13-integration-hardening-deployment/13-VERIFICATION.md`
3. Phase 13 governance evidence:
   - `reports/13/13-01/self-check.md`
   - `reports/13/13-01/review.md`
   - `reports/13/13-01/structure-audit.md`
   - `reports/13/13-01/integrity-audit.md`
   - `reports/13/13-02/self-check.md`
   - `reports/13/13-02/review.md`
   - `reports/13/13-02/structure-audit.md`
   - `reports/13/13-02/integrity-audit.md`
   - `reports/13/13-03/self-check.md`
   - `reports/13/13-03/review.md`
   - `reports/13/13-03/structure-audit.md`
   - `reports/13/13-03/integrity-audit.md`
   - `reports/13/13-04/self-check.md`
   - `reports/13/13-04/review.md`
   - `reports/13/13-04/structure-audit.md`
   - `reports/13/13-04/integrity-audit.md`
4. Phase 13.1 closure artifacts:
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-PRE-CONTEXT-SCOPE.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-CONTEXT.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-RESEARCH.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-PLANNING-COVERAGE.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-01-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-02-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-03-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-04-PLAN.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-01-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-02-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-03-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-04-SUMMARY.md`
   - `.planning/phases/13.1-product-data-enrichment-protocol-v2-integration/13.1-VERIFICATION.md`
5. Canonical trackers:
   - `.planning/ROADMAP.md` (Phase 14.1 marked complete `6/6`)
   - `.planning/STATE.md` (current atomic task: Phase 14.1 phase-close verification + Phase 15 readiness)
6. Governance closure evidence:
   - `reports/07/07.2-governance-operational-defaults/self-check.md`
   - `reports/07/07.2-governance-operational-defaults/review.md`
   - `reports/07/07.2-governance-operational-defaults/structure-audit.md`
   - `reports/07/07.2-governance-operational-defaults/integrity-audit.md`

## Phase 13.2 Graph Integration Modules

**Core:**
- `src/core/graphiti_client.py` - Graph client singleton with fail-open behavior
- `src/core/synthex_entities.py` - Entity and edge type contracts for temporal knowledge

**Tasks & Jobs:**
- `src/tasks/graphiti_sync.py` - Celery tasks for graph episode emission
- `src/jobs/graphiti_ingestor.py` - Episode ingestion with dedupe and timeout protection

**Assistant & Governance:**
- `src/assistant/governance/graph_oracle_adapter.py` - Graph-backed Oracle evidence adapter
- `src/assistant/memory_retrieval.py` - Enhanced memory retrieval with vector + lexical blend

**Scripts:**
- `scripts/governance/graph_gate.py` - Graph integration governance gate (GREEN/RED verdict)

**Tests:**
- `tests/core/test_graphiti_client_contract.py` - Client contract tests (10 tests)
- `tests/core/test_synthex_entities.py` - Entity/edge contract tests (16 tests)
- `tests/tasks/test_graphiti_sync_contract.py` - Emission task tests (10 tests)
- `tests/api/test_graph_oracle_adapter_contract.py` - Oracle adapter tests (13 tests)

**Documentation:**
- `.planning/KNOWLEDGE_GRAPH_ORACLE.md` - Integration guide for Phase 14/15

## Phase 14 Codebase Knowledge Graph Modules

**Core:**
- `src/core/codebase_entities.py` - Entity and edge models for codebase structure (File, Module, Class, Function, PlanningDoc)
- `src/core/codebase_schema.py` - Neo4j schema definitions (indexes, constraints, ensure_schema)
- `src/core/summary_generator.py` - Hierarchical summary extraction (file/function/class purpose without full content)
- `src/core/embeddings.py` - Vector embedding generation with sentence-transformers (384-dim, local, Neo4j vector index)

**Scripts:**
- `scripts/graph/init_codebase_schema.py` - CLI script to initialize codebase graph schema

**Tests:**
- `tests/unit/test_embeddings.py` - Embedding and summary generator tests (16 tests)

**Planning:**
- `.planning/phases/14-continuous-optimization-learning/14-CONTEXT.md` - Phase 14 context and decisions
- `.planning/phases/14-continuous-optimization-learning/14-01-PLAN.md` - Entity schema foundation plan
- `.planning/phases/14-continuous-optimization-learning/14-01-SUMMARY.md` - Plan 01 execution summary
- `.planning/phases/14-continuous-optimization-learning/14-02-PLAN.md` - Vector embedding pipeline plan
- `.planning/phases/14-continuous-optimization-learning/14-02-SUMMARY.md` - Plan 02 execution summary

## Phase 14.1 Hybrid-RAG Modules

**Graph Retrieval and Caching:**
- `src/graph/search_expand_bridge.py` - Two-phase search-then-expand retrieval with depth and token constraints
- `src/graph/semantic_cache.py` - Similarity-threshold query cache with TTL/eviction/invalidation
- `src/graph/query_interface.py` - Unified cache-first query pipeline with discrepancy + convention metadata
- `src/graph/query_templates.py` - Shared query templates including discrepancy, convention, and CALLS support

**Lifecycle + Guardrails:**
- `src/graph/mcp_server.py` - MCP stdio server with session context preload and convention-aware tools
- `src/graph/convention_checker.py` - Convention conflict scoring for architectural suggestions
- `src/graph/refactor_guard.py` - CALLS-topology refactor risk scoring

**Scripts:**
- `scripts/graph/seed_memory_nodes.py` - Memory entity seeding from project docs
- `scripts/graph/start_mcp_server.sh` - MCP startup wrapper

**Tests:**
- `tests/unit/test_search_expand_bridge.py`
- `tests/unit/test_semantic_cache.py`
- `tests/unit/test_query_interface.py`
- `tests/unit/test_mcp_server_contract.py`
- `tests/unit/test_convention_checker.py`
- `tests/unit/test_refactor_guard.py`

## Governance Links
1. Policy source: `solutionsos/compound-engineering-os-policy.md`
2. Governance baseline: `AGENTS.md`
3. Standards: `STANDARDS.md`
4. Structure spec: `ops/STRUCTURE_SPEC.md`
5. Canonical roadmap: `.planning/ROADMAP.md`
6. Canonical state: `.planning/STATE.md`
7. Canonical role definitions: `ops/governance/roles/README.md`

## Journey Synthesis Links
1. Template: `reports/meta/journey-synthesis-template.md`
2. Next required synthesis: end of current 3-phase window.
