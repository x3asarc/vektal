# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-16)

**Core value:** Store owners can maintain accurate, SEO-optimized product catalogs from 8+ vendors without manual data entry, through an intelligent, self-healing SaaS platform.

## Current Status (2026-03-06)

**Phase:** Phase 17 - Product Data Command Center + Chat-First Product Ops - **COMPLETE**
**Gate Status:** `GREEN` (Phase 17 summary artifacts + verification report published)
**Target Milestone:** Catalog health mission control with real-time sync and governed rollback

**COMPLETED: v1.0 + Context OS Lifecycle**
- Phases 1-13.2: Core Infrastructure, API, Frontend, AI, Governance (Complete)
- Phase 14-14.3: Knowledge Graph, Hybrid RAG, Tool Calling, Availability (Complete)
- Phase 15: Self-Healing, Runtime Optimization, Learning Loop, Approval Queue (Complete)
- Phase 16: Agent Context OS (entrypoint docs, graph-first broker, lifecycle memory hooks, governance gate) (Complete)
- Phase 15.1: Sentry autonomous intake, deduped routing, and verified closure gating (Complete)
- Phase 17: Product Data Command Center, Webhook Sync, and Live Reconcile Rollback (Complete)

**Next:** Future production refinement execution:
- `priority-2-dokploy-e2e` (deployment evidence closure)
- `priority-3-native-llm-capability-context` (native conversational fallback + capability-aware grounding)

## Context Snapshot

- **Infrastructure:** Production-ready containerized stack (12+ services) with active memory/context hooks.
- **AI/Agents:** Self-healing runtime plus graph-first context broker with reason-coded fallback.
- **Data Layer:** PostgreSQL (psycopg3) + Redis + Neo4j (Graphiti-enabled) + append-only `.memory/events`.
- **SaaS Readiness:** Multi-tier auth, Stripe billing, versioned API, progressive onboarding.
- **Governance:** Binary Context OS gate (`GREEN|RED`) with operator runbook and verification harness.

## Operational Metrics
- **Verification Coverage:** Phase 15 (66/66) and Phase 16 closure suite (24/24 targeted tests) passed.
- **Context Gate:** `GREEN` on `python scripts/governance/context_os_gate.py --window-hours 24`.
- **Phase 16 Verification Harness:** `GREEN` on `python scripts/context/verify_phase16.py --mode full`.
- **Phase 15.1 Verification:** `GREEN` on `python -m pytest tests/graph/test_sentry_feedback.py tests/graph/test_sentry_integration.py -q` (13 passed).
- **Autonomy:** Infrastructure auto-apply enabled; Code changes require confidence >= 0.9.
- **Learning:** Template extractor active (min 2 hits for promotion).
- **Performance:** Bottleneck detection and week-over-week telemetry active.

## Final Phase 15 Summary
All 12 sub-plans (15-01 through 15-11b) successfully executed and verified.
- **Sandbox:** Secure Docker-based execution with 6-gate hardening.
- **Memory:** YAML-priming reduces token overhead by 80%.
- **Classification:** 3-tier root-cause analysis (Pattern/Graph/LLM).
- **Remediation:** Template-first fixes with LLM fallback and sandbox gating.
- **Infrastructure:** Bash agent with allowlisted command execution.
- **Optimization:** Telemetry-driven self-tuning (pools, timeouts, batching).
- **HITL:** Persistent approval queue (CLI + Web UI) for lower-confidence fixes.

## StructureGuardian Audit Trail
- 2026-03-02: Phase 15 closure evidence sync (GREEN).
- 2026-03-02: Final v1.0 metadata update (GREEN).
- 2026-03-04: Added Phase 15.1 (Sentry autonomous intake + verified auto-resolution) to roadmap; planning artifacts initialized.
- 2026-03-03: Phase 16 context-os closure artifacts and lifecycle state sync (GREEN).
- 2026-03-04: Completed Phase 15.1 execution plans 01-04 and published required governance reports (GREEN).
- 2026-03-06: Completed Phase 17 execution plans 17.1-17.6; Sentry dev-integration verified; Phase summary and verification reports published (GREEN).

## Recent Session Summary (2026-03-06)
- Implemented Phase 17: Product Data Command Center + Chat-First Product Ops.
- Extended `Product` model with completeness scoring and forensic field tracking.
- Implemented secure Shopify Webhook receiver and periodic Reconciliation Poller.
- Created brutalist Dashboard UI (`CommandCenter`) with embedded Chat Dock.
- Integrated Sentry SDK for development environment telemetry.
- Published wave summaries (17.1-17.6) and final Phase 17 verification report.

## Architecture Sessions (2026-03-07 — 2026-03-08) via Letta
Work conducted through Letta agent (agent-745c61ec). No GSD phase executed.
All artifacts committed to master (e1e8431).

### Graph Schema Research
- Aura baseline verified: 2,098 Function, 667 Class, 602 File, 469 PlanningDoc nodes.
  CALLS graph (2,090 edges) confirmed live. Episodic layer empty (no episodes written yet).
- Graphiti episode classification established: CODE_INTENT / BUG_ROOT_CAUSE_IDENTIFIED /
  CONVENTION_ESTABLISHED → Developer KG. ENRICHMENT_OUTCOME / ORACLE_DECISION → Graph 2 (deferred).
- `src/graph/intent_capture.py` lazy import fix applied (GREEN — test_wave_sync.py patched).
- Research docs produced:
  - `docs/graph/research-input.md` — Gemini v1 research
  - `docs/graph/gemini-deep-research-analysis.md` — v1 analysis
  - `docs/graph/research-input-v2.md` — Gemini v2 research (Graphiti-aware)
  - `docs/graph/research-v2-analysis.md` — v2 analysis + implementation spec (BASIS FOR GRAPH SPRINT)

### Agent System Architecture
- Full workspace map completed: GSD, skills, agents, hooks, plugins, Letta skills inventoried.
- Three-level Commander hierarchy designed: Commander → Leads → Specialists.
- Layer 0 defined: Aura, Sentry, task-observer, Governance, North Star, STATE.md, LongTermPatterns.
- Memory tier mapping: working→Letta, short-term→STATE.md, long-term→Aura (:LongTermPattern).
- Docs produced:
  - `docs/agent-system/resources-input.md` — raw resource dump
  - `docs/agent-system/finetuned-resources.md` — filtered resource inventory (15 tools)
  - `docs/agent-system/commander-architecture.md` — Commander design spec (LOCKED)

### Next Actions
1. Graph sprint tasks 1–6 (static layer: full re-sync, APIRoute, CeleryTask, EnvVar, Table, bi-temporal)
2. Graph sprint tasks 7–12 (bridges: Graphiti, Sentry, indexes, validation)
3. Build Commander + Lead agent files (`.claude/agents/`)
4. Graph sprint task 13 (orchestration + memory layer: SkillDef, AgentDef, LongTermPattern nodes)
