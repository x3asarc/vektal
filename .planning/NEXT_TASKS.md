# Next Tasks Queue

Last updated: 2026-03-06

## Session State: Agent Context OS & Sentry Intake Completion (2026-03-06)

### Status
- **Project Phase:** Phase 16 (Agent Context OS) & Phase 15.1 (Sentry Intake) — **COMPLETE**
- **Artifacts Updated:** `.planning/STATE.md`, `README.md`, `docs/DIRECTORY_STRUCTURE.md`
- **Verification:** 
  - Phase 16 closure suite (24/24 tests) passed.
  - Phase 15.1 Sentry integration (13/13 tests) passed.
  - Context OS compatibility gate: `GREEN`.
  - GitHub Sync: All modified tracked files and essential new planning/source files pushed to `master`.

### Technical Effort & Successes
1. **Agent Context OS:** Implemented graph-first context broker with reason-coded fallback and lifecycle memory hooks.
2. **Sentry Autonomous Intake:** Completed automated pulling, routing, and verified closure loop for system issues.
3. **Neo4j Direct Integration:** Refined `context_broker.py` to use direct Neo4j queries for higher reliability in assistant context assembly.
4. **Documentation Overhaul:** Updated `README.md` and `DIRECTORY_STRUCTURE.md` to reflect the modern graph-first, self-healing architecture.

---

## 🚀 Priority 1: Phase 17 - Product Data Command Center

**Status**: **ACTIVE** (Planning artifacts initialized)

**What this phase delivers**:
- **Unified Dashboard**: Real-time metrics for catalog integrity, ingestion health, and resolution success.
- **Data Contract Enforcement**: Hardened Pydantic-based validation for all vendor data imports.
- **Live Ingestion Listener**: SSE-based stream for tracking bulk imports and resolution jobs in the UI.
- **Rollback UX**: One-click restoration for failed or low-confidence enrichment jobs.

**Planning Artifacts**:
- `.planning/phases/17-product-data-command-center/17-PLAN.md`
- `.planning/phases/17-product-data-command-center/17-UX-SPEC.md`
- `.planning/phases/17-product-data-command-center/17-GRAPH-LINKS.md`

**Next Step**: Execute `17.1-data-contract` to harden the ingestion pipeline.

---

## 🌐 Priority 2: Deploy to Dokploy for E2E Testing

**Status**: `PARTIAL` (Local readiness `GREEN`, Deployment pending)

**What remains to close Priority 2**:
- Configure Dokploy project/env and deploy full stack (backend, frontend, Neo4j, Redis, Celery).
- Run real browser E2E (Playwright) against deployed URLs.
- Verify Sentry issue capture from the deployed Dokploy environment.
- Publish evidence bundle under `reports/future-production-refinement/priority-2-dokploy-e2e/`.

**Impact**: Validate entire self-healing system and Context OS in production conditions.

---

## 🤖 Priority 3: Native LLM Capability Context for Chat UX

**Status**: Planned (Research complete, Execution not started)

**What this phase delivers**:
- Capability-packet-grounded fallback responses for unclear intents.
- Anti-repetition conversational guardrails in `src/assistant/`.
- Cost-aware model policy (OpenRouter default vs. fallback).
- Playwright verification loop for deployed chat UX.

**Impact**: Transition the assistant from "command-first" to "native conversational" while staying grounded in system limits.

---

## How This File Works

When you ask "what should I work on next?" or "what's next?", check this file.

Tasks are prioritized by:
1. Blocking issues (nothing currently)
2. High-impact completions (Phase 17)
3. Infrastructure & UX refinements (Priority 2 & 3)

---

## ✅ Completed (Archive)

### ✅ Phase 16: Agent Context OS (2026-03-04)
- Graph-first context broker with reason-coded fallback.
- Lifecycle memory hooks for task-level state persistence.
- Binary governance gates (Structure/Integrity/Review).
- **Evidence**: `reports/16/` (Closure reports verified).

### ✅ Phase 15.1: Sentry Autonomous Intake (2026-03-04)
- Automated Sentry issue pulling and routing.
- Verified auto-resolution loop with recurrence journaling.
- Health-monitor integration for issue-level telemetry.
- **Evidence**: `tests/graph/test_sentry_integration.py` (Passed).

### ✅ Phase 15: Self-Healing Dynamic Scripting (2026-03-02)
- All 12 sub-plans (15-01 to 15-11b) completed.
- 66/66 tests passing.
- **Evidence**: `.planning/phases/15-self-healing-dynamic-scripting/15-UAT.md`.

### ✅ Health Daemon System (2026-03-03)
- Performance improvement for health checks (1.5ms cache reads).
- **Evidence**: `docs/health-daemon-system.md`.
