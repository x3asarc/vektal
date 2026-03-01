# Phase 15 Research: Self-Healing & Runtime Optimization

**Date:** 2026-03-01
**Status:** Research Complete (Foundation for Implementation)

## 1. Goal: Autonomous Remediation Loop
Transform the platform into an "active organism" that detects, triages, fixes, and learns from failures without human intervention.

---

## 2. Core Architecture: The Universal Sandbox
A safe environment to verify autonomous code changes before deployment.

### 6-Gate Verification Protocol
1. **Syntax Gate:** `ast.parse()` to ensure code is valid Python.
2. **Type Gate:** `mypy` or `pyright` for static type analysis.
3. **Unit Gate:** `pytest` scoped to changed modules and their dependents.
4. **Contract Gate:** Validate API schema and data integrity.
5. **Governance Gate:** Security and `STANDARDS.md` compliance check.
6. **Rollback Gate:** Dry-run revert logic to ensure high-confidence recoverability.

### Implementation Strategy
- **Isolation:** Use `docker-py` with unique `COMPOSE_PROJECT_NAME` for ephemeral full-stack clones.
- **FS Strategy:** Copy `src/`, `tests/`, and key config files into a `.sandbox/{run_id}/` directory.
- **Resource Limits:** Enforce CPU and memory limits to prevent sandbox escapes/host DoS.

---

## 3. Failure Triage & Root-Cause Classification
Leveraging Sentry and the Codebase Knowledge Graph.

### Sentry Integration (Feedback Loop)
- **Ingestion:** Poll unresolved `level:error` issues via Sentry REST API.
- **Normalization:** Map tracebacks to Phase 14 nodes (`File`, `Function`).
- **Context:** Use `capture_exception` and `set_context` to feed structured metadata back into the graph.

### Root-Cause Classifier (LLM + Graph)
- **Cypher Patterns:**
    - `VectorCypherRetriever`: Correlate traceback functions with semantic codebase nodes.
    - `impact_radius`: Trace dependents of failing functions.
    - `similar_failures`: Query historical `Episode` nodes for similar root causes.
- **Logic:** Combine Sentry's `culprit` and stack frames with Neo4j's import/call graph to pinpoint the "blast radius."

---

## 4. Persistent Learning (The Remedy Catalog)
Closing the loop to prevent repeated failures.

### Mechanism: Remedy Promotion
- Successful fixes are initially logged as `RemedyCandidate` nodes.
- After passing sandbox and **2 stable production applies**, promote to `RemedyTemplate`.
- Templates are injected into future prompt contexts for relevant categories.

### Knowledge Artifacts
- **Neo4j:** Stores structural, machine-readable patterns.
- **FAILURE_JOURNEY.md:** Records the human-engineering narrative (Dead ends, hard lessons).

---

## 5. Technical Stack Prerequisites
- **Docker SDK for Python (`docker-py`):** For dynamic container orchestration.
- **Sentry SDK:** For programmatic issue retrieval.
- **Neo4j GraphRAG:** For advanced semantic-structural correlation.
- **PyYAML:** For compressed, lazy-loaded session contexts.

---
*Reference: See `.planning/phases/15-self-healing-dynamic-scripting/changes.md` for the initial skeleton implemented during this research session.*
