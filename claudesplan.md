# Phase 13.2 -> 14 -> 15 Unified Architecture Plan

## Status
- Document type: execution blueprint (planning only)
- Strategy: Brain-First (build temporal graph substrate before further frontend work)
- Current gate verdict: `RED` (not ready to execute until prerequisites and preflight checks below are completed)
- This pass performed: plan review and hardening only, no implementation execution

## Intent
Build one reusable Oracle framework in Phase 13.2 that provides shared verification signals for:
- execution verification
- content verification
- visual verification
- policy verification

Then make that framework the required substrate for Phase 14 optimization loops and Phase 15 self-healing loops.

## Scope and Non-Goals
### In Scope (Phase 13.2)
- Neo4j service integration and runtime wiring
- `graphiti-core` client integration
- shared graph ingestion pipeline (episodes)
- graph-backed Oracle adapter with fail-open behavior
- memory retrieval relevance upgrade (vector + lexical fallback)
- governance gate script and contract tests
- roadmap/state/docs updates and phase closure artifacts

### Out of Scope (Phase 13.2)
- autonomous remediation behavior (Phase 15)
- optimization policy tuning loops (Phase 14)
- frontend contract redesign
- PostgreSQL schema changes for graph persistence

## Governance Baseline Alignment
- Canonical lifecycle/state files remain `.planning/ROADMAP.md` and `.planning/STATE.md`.
- Every execution task closure requires exactly 4 reports:
  - `self-check.md`
  - `review.md`
  - `structure-audit.md`
  - `integrity-audit.md`
- Merge blocks:
  - all `Critical`
  - all `High`
  - `Medium` in `Security` or `Dependency`
- Review protocol must preserve pass-order timestamps in `review.md`:
  - `pass_1_timestamp`
  - `plan_context_opened_at`
  - `pass_2_timestamp`

## Step 0: Architect Pause (Pre-Execution)
Complete in order before editing implementation files.

### 0a) Git Checkpoint
Planned command sequence:
```bash
git add -A
git commit -m "chore: pre-graph frontend-backend contract checkpoint"
git tag frontend-api-contract-pre-graph-20260218
git push -u origin claude/agentic-rag-knowledge-graph-7gW6p --tags
```

### 0b) Frontend Soft Freeze
During Phase 13.2 execution, keep these interfaces stable:

| Surface | Owner | Status |
|---|---|---|
| `GET /api/v1/products` | `src/api/v1/products/routes.py` | FROZEN |
| `POST /api/v1/chat/sessions/{id}/actions/{action_id}/apply` | `src/api/v1/chat/approvals.py` | FROZEN (emission hook only) |
| `POST /api/v1/products/enrichment/runs/{run_id}/apply` | enrichment routes | FROZEN (emission hook only) |
| `GET /api/v1/chat/sessions/{id}/stream` | chat routes | FROZEN |
| `frontend/src/features/*` | frontend domain | FROZEN |

Rules:
- no response schema changes
- no request contract changes
- no frontend component behavior changes in 13.2
- additive background emission hooks are allowed

### 0c) State Update
Append to `.planning/STATE.md`:
- current phase set to 13.2
- Architect Pause active
- checkpoint tag recorded
- frontend freeze active
- Neo4j + Graphiti integration in progress

## Why Graphiti-Core (vs Custom)
| Concern | Custom Build | Graphiti-Core |
|---|---|---|
| Temporal validity model | manual implementation | built-in bitemporal semantics |
| Contradiction handling | custom logic needed | built-in resolution path |
| Entity deduplication | custom pipeline needed | multi-stage matching model |
| Episode ingestion API | per-source custom adapters | unified ingestion contract |
| Async model | custom bridge required | async-native |
| Integration velocity | slower | faster |

Decision: use `graphiti-core`, bridge async calls via Celery task boundaries.

## Architecture Contract (13.2 -> 14 -> 15)
### Phase 13.2: Build the shared graph substrate
- deploy graph runtime and client
- define domain entity/edge contracts
- emit episodes from critical governance + apply paths
- expose graph-backed Oracle evidence adapter
- unify reliability behavior (timeout, retry, fail-open)

### Phase 14: Feed and exploit the graph
- optimization loops query graph before proposing changes
- learning loop outputs are emitted as episodes
- trend and drift signals come from temporal graph state

### Phase 15: Graph-aware self-healing
- remediation planning checks graph evidence first
- critical warnings force escalation
- remediation outcomes become episodes
- time-aware history informs future remediations

## Dependency and Compatibility Policy
- Python dependencies must be exact pins in `requirements.txt` (no `>=`).
- Proposed pins for 13.2:
  - `graphiti-core==0.26.0`
  - `neo4j==5.26.0`
- Existing requirements remain unchanged unless required by compatibility checks.
- Any dependency changes require integrity audit:
  - license validation
  - security posture checks
  - transitive risk review

## Integration Sources
### Required Direct Source
1. Graphiti (primary integration source)
   - Repo: `https://github.com/getzep/graphiti`
   - Include `mcp_server` path as same-repo reference when applicable:
     - `https://github.com/getzep/graphiti/tree/main/mcp_server`

### Optional Direct Sources (only if implementation uses internals directly)
1. Neo4j Python driver
   - Repo: `https://github.com/neo4j/neo4j-python-driver`
2. Neo4j server
   - Repo: `https://github.com/neo4j/neo4j`
3. Sentence Transformers
   - Repo: `https://github.com/UKPLab/sentence-transformers`
4. OpenAI Python SDK
   - Repo: `https://github.com/openai/openai-python`
5. Celery
   - Repo: `https://github.com/celery/celery`

Source-linking rule:
- Keep plan noise low. Link only repos that are directly integrated or whose internals are used in implementation decisions.

## Infrastructure Delta (Planned)
### `docker-compose.yml`
Add `neo4j` service, named volumes, and environment wiring for `backend` and `celery_worker`.

Reference service shape:
```yaml
neo4j:
  image: neo4j:5.26
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    NEO4J_server_memory_heap_max__size: 1G
    NEO4J_server_memory_pagecache_size: 512M
  ports:
    - "7474:7474"
    - "7687:7687"
  volumes:
    - neo4j_data:/data
    - neo4j_logs:/logs
  healthcheck:
    test: ["CMD", "curl", "-sf", "http://localhost:7474"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
  restart: unless-stopped
```

### `.env.example`
```env
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeit
GRAPH_ORACLE_ENABLED=true
```

Security note:
- production credentials must come from secret management (not default literals)
- avoid committing real credentials

## Episode Taxonomy Contract
All episode payloads must include at minimum:
- `episode_type`
- `store_id`
- `created_at` (UTC)
- `correlation_id` (when available)

Episode classes for 13.2:
1. `oracle_decision`
2. `failure_pattern` (from `FAILURE_JOURNEY.md`)
3. `enrichment_outcome`
4. `user_approval`
5. `vendor_catalog_change`

Payload quality rules:
- immutable event identity
- explicit reason codes where applicable
- no PII fields unless required and approved

## Entity and Edge Contract
Planned file: `src/core/synthex_entities.py`

Entity families:
- `OracleDecisionEntity`
- `FailurePatternEntity`
- `ModuleEntity`
- `EnrichmentOutcomeEntity`
- `UserApprovalEntity`

Edge families:
- `WasVerifiedByEdge`
- `HasFailureWarningEdge`
- `YieldedOutcomeEdge`
- `ApprovedByUserEdge`

Contract rule:
- keep entity/edge fields stable and versioned
- any breaking schema change requires roadmap/state annotation

## Async Bridge Rules
- no `asyncio.run()` in Flask request handlers
- no blocking graph write calls in request path
- ingestion is always fire-and-forget via Celery
- graph reads from request path must be timeout-guarded (2s default) and fail-open

Fail-open contract:
- graph unavailability must not block mutation flows
- fallback Oracle signal:
  - `decision="pass"`
  - `confidence=0.5`
  - empty `reason_codes`
  - empty `evidence_refs`

## Phase 13.2 Execution Plan Breakdown
## 13.2-01 Infrastructure + Client + Entity Types
### Goal
Neo4j runtime and Graphiti client substrate are available with contract tests.

### Planned file changes
- `docker-compose.yml`
- `.env.example`
- `requirements.txt`
- `src/core/graphiti_client.py` (new)
- `src/core/synthex_entities.py` (new)

### Acceptance criteria
- graph client singleton behavior is deterministic
- graph availability check is bounded and fail-open safe
- entity and edge contracts are defined and importable

### Required reports
- `reports/13.2/13.2-01/self-check.md`
- `reports/13.2/13.2-01/review.md`
- `reports/13.2/13.2-01/structure-audit.md`
- `reports/13.2/13.2-01/integrity-audit.md`

## 13.2-02 Episode Ingestion Pipeline
### Goal
Emit episodes from governance and apply paths without API contract changes.

### Planned file changes
- `src/tasks/graphiti_sync.py` (new)
- `src/jobs/graphiti_ingestor.py` (new)
- `src/tasks/__init__.py`
- `src/assistant/governance/verification_oracle.py`
- `src/api/v1/chat/approvals.py`
- `src/tasks/enrichment.py`
- `src/tasks/ingest.py`

### Acceptance criteria
- emission hooks are additive and non-blocking
- failure journey sync task parses and emits structured episodes
- retries and silent-fail boundaries are explicit

### Required reports
- `reports/13.2/13.2-02/self-check.md`
- `reports/13.2/13.2-02/review.md`
- `reports/13.2/13.2-02/structure-audit.md`
- `reports/13.2/13.2-02/integrity-audit.md`

## 13.2-03 Graph Oracle Adapter + Memory Retrieval Upgrade
### Goal
Add graph-backed evidence path and improve memory relevance scoring while preserving safe fallback.

### Planned file changes
- `src/assistant/governance/graph_oracle_adapter.py` (new)
- `src/assistant/memory_retrieval.py`
- `.planning/KNOWLEDGE_GRAPH_ORACLE.md` (new)

### Acceptance criteria
- adapter returns Oracle signal payload contract
- adapter is bounded by timeout and fail-open behavior
- memory retrieval supports vector + lexical blend with lexical fallback

### Required reports
- `reports/13.2/13.2-03/self-check.md`
- `reports/13.2/13.2-03/review.md`
- `reports/13.2/13.2-03/structure-audit.md`
- `reports/13.2/13.2-03/integrity-audit.md`

## 13.2-04 CI Governance Gate + Contract Tests
### Goal
Introduce deterministic graph-governance gate and test suite coverage.

### Planned file changes
- `scripts/governance/graph_gate.py` (new)
- `tests/core/test_graphiti_client_contract.py` (new)
- `tests/tasks/test_graphiti_sync_contract.py` (new)
- `tests/api/test_graph_oracle_adapter_contract.py` (new)

### Acceptance criteria
- gate provides binary output (`GREEN`/`RED`)
- static hook checks validate required emission points
- tests do not require live Neo4j for unit/contract coverage

### Required reports
- `reports/13.2/13.2-04/self-check.md`
- `reports/13.2/13.2-04/review.md`
- `reports/13.2/13.2-04/structure-audit.md`
- `reports/13.2/13.2-04/integrity-audit.md`

## 13.2-05 Phase Closure + Forward Integration Spec
### Goal
Close phase artifacts and update canonical planning/state maps with Phase 14/15 integration hooks.

### Planned file changes
- `.planning/phases/13.2-oracle-framework-reuse/13.2-01-PLAN.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-02-PLAN.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-03-PLAN.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-04-PLAN.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-05-PLAN.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-PLANNING-COVERAGE.md` (new)
- `.planning/phases/13.2-oracle-framework-reuse/13.2-VERIFICATION.md` (new)
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `docs/MASTER_MAP.md`

### Acceptance criteria
- roadmap and state are synchronized
- phase verification artifact maps evidence to requirements
- all plan-level governance reports exist

### Required reports
- `reports/13.2/13.2-05/self-check.md`
- `reports/13.2/13.2-05/review.md`
- `reports/13.2/13.2-05/structure-audit.md`
- `reports/13.2/13.2-05/integrity-audit.md`

## Risk Register
| Severity | Risk | Impact | Mitigation | Owner |
|---|---|---|---|---|
| High | Request-path latency regression from graph calls | API SLO impact | hard 2s timeout + fail-open + async bridge | Builder |
| High | Dependency/license drift from new packages | merge block | integrity audit with transitive review and replacement plan | IntegrityWarden |
| Medium(Security) | Neo4j credential leakage | secret exposure | env template only, runtime secrets management, no plaintext commits | Builder |
| Medium | Duplicate event ingestion | noisy graph state | idempotency keys in episode payload and dedupe strategy | Builder |
| Medium | Memory relevance behavior drift | retrieval quality drop | blended scoring fallback + contract tests | Reviewer |
| Low | Graphiti API surface mismatch by version | rework | exact pin + compatibility preflight in 13.2-01 | Builder |

## Rollback Plan
Rollback triggers:
- critical reliability regression in chat/apply flows
- graph-related worker instability affecting queue health
- contract test regressions without safe patch path

Rollback actions:
1. Disable graph adapter via `GRAPH_ORACLE_ENABLED=false`.
2. Keep emission hooks no-op safe (swallow exceptions).
3. Revert 13.2 file set to checkpoint tag.
4. Preserve governance report trail and record post-mortem in `.planning/STATE.md`.

Rollback owner:
- PhaseManager for lifecycle decision
- Builder for technical rollback execution

## Verification Matrix (Execution-Time)
Planned checks:
```bash
python -m pytest tests/core/test_graphiti_client_contract.py -q
python -m pytest tests/tasks/test_graphiti_sync_contract.py -q
python -m pytest tests/api/test_graph_oracle_adapter_contract.py -q
python -m pytest tests/ -q -k "memory"
python scripts/governance/graph_gate.py --check-emission-hooks
python scripts/governance/validate_governance.py --phase 13.2
```

Gate policy:
- Any failing mandatory check keeps status `RED`.
- `GREEN` requires passing checks plus complete governance artifacts.

## Phase 14 and 15 Integration Contract (Forward)
### Phase 14 mandatory pre-action reads
1. `query_graph_evidence(action_type="optimization", target_module=<module>)`
2. enrichment trend search by vendor/outcome
3. user approval pattern search by action type

### Phase 15 mandatory pre-action reads
1. `query_graph_evidence(action_type="remediation", target_module=<module>)`
2. critical warning -> escalate; do not auto-remediate
3. sandbox outcome must emit episode

Cross-phase invariant:
- agents add episodes only
- agents do not delete graph history

## Definition of Done for Phase 13.2
Phase 13.2 is `GREEN` only when all are true:
1. plans `13.2-01` to `13.2-05` are executed and evidence-linked
2. all mandatory reports exist for each task
3. graph gate returns `GREEN`
4. required contract tests pass
5. roadmap/state/master map are synchronized
6. no unresolved blocking findings (`Critical`, `High`, `Medium` in `Security`/`Dependency`)

Otherwise phase status remains `RED`.

## Branch Contract
- Working branch: `claude/agentic-rag-knowledge-graph-7gW6p`
- This document is a planning contract and must be updated when scope, risks, or gates change.
