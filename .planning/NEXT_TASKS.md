# Next Tasks Queue

Last updated: 2026-03-03

## Priority 1: Complete Health → Remediation Routing

**Plan**: `.planning/phases/15-self-healing-dynamic-scripting/health-to-remediation-routing-plan.md`

**Status**: Designed, ready to implement

**What's needed**:
- 2 new remediators: `dependency_remediator.py`, `neo4j_health_remediator.py`
- Enhance `health_monitor.py` to trigger remediation for all detected issues (not just Sentry)
- Update orchestration routing in `orchestrate_healers.py`

**Impact**: 90% of infrastructure issues will self-heal without human intervention

**Phases**:
1. Create dependency_remediator (30 min)
2. Create neo4j_health_remediator (30 min)
3. Update health_monitor.py with routing triggers (20 min)
4. Test end-to-end flow (15 min)

**Total effort**: ~2 hours

**When to do**: Next available session

---

## Priority 2: Deploy to Dokploy for E2E Testing

**Status**: Ready to configure

**What's needed**:
- Configure Dokploy deployment with frontend
- Deploy complete stack: backend, frontend, Neo4j, Redis, Celery
- Test from user perspective (real browser, real workflows)
- Verify all integrations:
  - ✅ Sentry catching real production errors
  - ✅ Neo4j/Graphiti providing code context for classification
  - ✅ Health monitoring detecting issues
  - ✅ Remediation system auto-healing problems
  - ✅ Frontend approval queue for HITL decisions

**Why this matters**:
- **Sentry + Graphiti = Smart Issue Resolution**
  - Sentry: Catches runtime errors with stack traces
  - Graphiti: Provides code relationship context
  - Combined: Classification knows "what broke" AND "why it broke"
  - Example: Sentry says "ConnectionRefusedError" → Graphiti knows it's related to Neo4j → Routes to correct remediator

**Impact**: Validate entire self-healing system works in production conditions

**Total effort**: ~2 hours (Dokploy config + deployment)

**When to do**: After routing completion OR in parallel

---

## Priority 3: Implement Memory System with Hooks

**Plan**: `.planning/memory-system-design.md`

**Status**: Designed, ready to implement

**What's needed**:
- Working memory (short-term cache, session-scoped)
- Long-term memory (persistent across sessions)
- Hooks: SessionEnd, TaskComplete, PhaseComplete
- Auto-update mechanisms

**Impact**: AI assistants maintain context across sessions, learn from patterns

**Total effort**: ~3 hours

**When to do**: After deployment verification

---

## How This File Works

When you ask "what should I work on next?" or "what's next?", check this file.

Tasks are prioritized by:
1. Blocking issues (nothing currently)
2. High-impact completions (routing, memory)
3. Nice-to-haves (future phases)

This file is updated:
- When new tasks are identified
- When tasks are completed (moved to archive section)
- When priorities change

---

## Completed (Archive)

### ✅ Health Daemon System (2026-03-03)
- Replaced 2-5s blocking hooks with 1.5ms cache reads
- 99.97% performance improvement
- Applied across Claude, Gemini, Codex
- **Evidence**: `docs/health-daemon-system.md`

### ✅ Phase 15 Self-Healing (2026-03-02)
- All 12 sub-plans completed
- 66/66 tests passing
- Self-healing infrastructure operational
- **Evidence**: `.planning/phases/15-self-healing-dynamic-scripting/15-UAT.md`
