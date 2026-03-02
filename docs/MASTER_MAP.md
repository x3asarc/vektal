# MASTER_MAP

Last batch update: 2026-03-02
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
|   `-- phases/
|       |-- 14.3-graph-availability-sync/
|       `-- 15-self-healing-dynamic-scripting/
|-- reports/
|   |-- 14.3/
|   |-- 15/
|   |-- meta/
|   `-- templates/
|-- ops/
|   |-- STRUCTURE_SPEC.md
|   `-- governance/roles/
|-- docs/
|   |-- MASTER_MAP.md
|   `-- INDEX.md
|-- src/
|   `-- ...
|-- tests/
|   `-- ...
|-- frontend/
|   `-- ...
`-- scripts/
    `-- ...
```

## Module Index
1. Governance:
   - `AGENTS.md`: governance constitution and role boundaries.
   - `STANDARDS.md`: severity model and review policy.
   - `.rules`: machine-checkable policy lines.
   - `ops/governance/roles/README.md`: canonical role definitions.
2. Planning and lifecycle:
   - `.planning/ROADMAP.md`: canonical lifecycle state (phases and plans).
   - `.planning/STATE.md`: current execution state and gate snapshot.
   - `.planning/phases/14.3-graph-availability-sync/`: availability and sync reliability artifacts.
   - `.planning/phases/15-self-healing-dynamic-scripting/`: self-healing and optimization artifacts.
3. Evidence and validation:
   - `reports/<phase>/<task>/`: required four-report governance bundles.
   - `reports/meta/`: cross-phase synthesis artifacts.
   - `scripts/governance/validate_governance.py`: governance gate validator.
4. Product code:
   - `src/graph/`: graph infrastructure, remediation, optimization, and sandbox systems.
   - `src/api/v1/approvals.py`: approval queue API.
   - `src/cli/approvals.py`: CLI controls for human-in-the-loop approvals.
   - `frontend/src/features/approvals/`: web approval queue UI.

## Data and Logic Flow
1. Requirements and decisions are captured in `.planning`.
2. Plan execution outputs summaries under `.planning/phases/<phase>/`.
3. Each task closure writes `self-check.md`, `review.md`, `structure-audit.md`, and `integrity-audit.md`.
4. Reviewer applies blocking policy (`Critical`, `High`, and `Medium` for `Security`/`Dependency`).
5. PhaseManager syncs `.planning/ROADMAP.md` and `.planning/STATE.md`.
6. ContextCurator updates `docs/MASTER_MAP.md` and journey synthesis links.

## Active Plans
1. Current lifecycle status:
   - v1.0 phases `1` through `15` are complete (`GREEN`) per `.planning/ROADMAP.md`.
   - `.planning/STATE.md` marks v1.0 final release complete.
2. Open execution:
   - No active phase plans are open.
   - Next work is in future phases:
     - Production Refinement & Integration Cleanup
     - User Data Knowledge Graph & Semantic Search
3. Latest closure and UAT artifacts:
   - `.planning/phases/14.3-graph-availability-sync/14.3-01-SUMMARY.md` through `14.3-07-SUMMARY.md`
   - `.planning/phases/15-self-healing-dynamic-scripting/15-01-SUMMARY.md` through `15-11b-SUMMARY.md`
   - `.planning/phases/15-self-healing-dynamic-scripting/15-UAT.md` (`66` automated checks passed)
4. Governance evidence packs:
   - `reports/14.3/14.3-01/` through `reports/14.3/14.3-07/`
   - `reports/15/15-01/` through `reports/15/15-11b/`

## Phase 14.3 Modules

**Availability and backend routing:**
- `src/graph/backend_resolver.py`
- `src/graph/infra_probe.py`
- `src/graph/incremental_sync.py`
- `src/graph/sync_status.py`
- `src/graph/mcp_response_metadata.py`

**Failure ingestion and healing orchestration:**
- `src/graph/sentry_ingestor.py`
- `src/graph/orchestrate_healers.py`

**Operational scripts and gates:**
- `scripts/graph/bootstrap_graph_backend.py`
- `scripts/graph/graph_status.py`
- `scripts/graph/pretool_gate.py`
- `scripts/governance/graph_availability_gate.py`
- `scripts/observability/sentry_issue_puller.py`

## Phase 15 Modules

**Sandbox and verification:**
- `src/graph/sandbox_verifier.py`
- `src/graph/sandbox_docker.py`
- `src/graph/sandbox_gates.py`
- `src/graph/sandbox_workspace.py`
- `src/graph/sandbox_persistence.py`
- `src/models/sandbox_runs.py`

**Root-cause and remediation learning loop:**
- `src/graph/root_cause_classifier.py`
- `src/graph/fix_generator.py`
- `src/graph/template_extractor.py`
- `src/graph/sentry_feedback_loop.py`

**Runtime optimization and HITL control plane:**
- `src/graph/performance_profiler.py`
- `src/graph/bottleneck_detector.py`
- `src/graph/runtime_optimizer.py`
- `src/graph/telemetry_dashboard.py`
- `src/models/pending_approvals.py`
- `src/api/v1/approvals.py`
- `src/cli/approvals.py`
- `frontend/src/features/approvals/components/ApprovalQueue.tsx`

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
2. Latest synthesis: `reports/meta/journey-synthesis-13-15.md`
3. Next required synthesis: end of the next 3-phase window.
