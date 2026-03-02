# Phase 15: Self-Healing & Runtime Optimization - Architecture (LOCKED)

**Status:** Architecture locked, ready for planning
**Date:** 2026-03-01
**Discussion:** Complete

---

## Core Principles

1. **Safety first:** Read-only → Infrastructure → Code (progressive autonomy)
2. **Extend, don't replace:** Build on Phase 14.3 NullClaw architecture
3. **Learning system:** Every fix becomes a template for future use
4. **Context-aware:** Session primer with git commits + phase + roadmap + remedies
5. **Human oversight:** Approval queue for confidence <0.9

---

## Architecture Decisions

### 1. Scope & Overlap

**15-03b (Sentry Triage):**
- Status: Already implemented in Phase 14.3-07
- Action: Keep as minimal verification/integration task
- Purpose: Verify 14.3 Sentry ingestion works with 15-03 LLM classifier

**Phase 14 Graph Dependency:**
- Verify graph queries work before planning features that depend on it
- Required: File/Module/Class/Function nodes, import relationships, planning docs

### 2. Sandbox Architecture

**Universal Docker Container:**
```yaml
Characteristics:
  - Universal: Reusable across all autonomous tasks (not task-specific)
  - Dynamic: Spins up/down on demand
  - Isolated: Full stack clone for safe testing

Storage:
  Database: sandbox_runs table (metadata, status, confidence)
  Filesystem: .sandbox/{run_id}/ (logs, diffs, test results)

6-Gate Verification:
  1. Syntax check (code compiles/parses)
  2. Type check (type annotations valid)
  3. Unit tests (existing tests pass)
  4. Contract tests (API contracts preserved)
  5. Governance gate (no Critical/High security issues)
  6. Rollback plan (documented revert path)

Outcomes:
  GREEN: All gates pass → Promote to staging/production
  YELLOW: Minor warnings → Human review required
  RED: Any gate fails → Block, escalate, log to FAILURE_JOURNEY.md
```

### 3. Approval System

**Custom Approval Queue (PostgreSQL):**
```sql
pending_approvals (
    id SERIAL PRIMARY KEY,
    approval_id UUID NOT NULL UNIQUE,
    type VARCHAR(50),  -- 'code_change', 'config_change', 'optimization'
    title VARCHAR(255),
    description TEXT,
    diff TEXT,
    confidence NUMERIC(3,2),
    sandbox_run_id INTEGER REFERENCES sandbox_runs(id),
    created_at TIMESTAMP,
    status VARCHAR(20),  -- 'pending', 'approved', 'rejected'
    resolved_at TIMESTAMP,
    resolved_by_user_id INTEGER
);
```

**User Experience:**
- Approvals persist across conversations
- Visible in every chat/CLI session until resolved
- Commands: `/approve`, `/reject`, `/review`

**Confidence-based routing:**
- Confidence ≥0.9: Auto-apply to production
- Confidence <0.9: Create pending approval
- Blast radius >5 files: Always require approval
- Any single source file >500 LOC: must be split into 2+ files before closure

**Future:** Can add GitHub PR integration in Phase 16+

### 4. LLM & Template Strategy

**Hybrid Learning System:**
```
1. Check templates (deterministic, fast)
   ↓ No match
2. Fallback to LLM (novel failures)
   ↓ Fix generated
3. Sandbox verification
   ↓ GREEN
4. Apply fix + record outcome
   ↓ After 2+ successes
5. Extract as template (with tagged description)
   ↓ Future requests
6. Template now handles automatically
```

**Template Structure:**
```yaml
template:
  fingerprint: "src/tasks/enrichment.py:TimeoutError"
  description: "Enrichment task timeout - increase from 30s to 60s"
  pattern: |
    File: src/tasks/{module}.py
    Error: TimeoutError
    Fix: Increase timeout parameter 2x
  confidence: 0.92
  applications: 3
  last_success: "2026-02-28T14:30:00Z"
  created_from: "llm_fallback"
```

**LLM Selection:**
- Use adaptive routing (TBD during planning - Flash vs Sonnet vs Opus)
- Template generation > LLM generation (cost + speed)

**Template Promotion:**
- Threshold: 2 successful applications
- Tagged with short description for precise matching
- Stored in Neo4j long-term memory

### 5. Blast Radius

**Base Limits:**
- Max files: 5
- Max LOC per source file: 500

**Escalation:**
- Changes >5 files: Require human approval even if sandbox GREEN
- Any source file >500 LOC: blocking refactor required into 2+ files before closure
- Rationale: Comprehensive healing capability, but safety gate for large changes

**Why permissive limits:**
- Real bugs often span multiple files (function + caller + test + schema)
- Sandbox provides safety net (6-gate verification)
- Conservative limits would block legitimate multi-file fixes

### 6. Integration with Phase 14.3 (NullClaw)

**Extend Existing Architecture:**
```python
remediation_registry.py (existing)
├── Infrastructure remediators (14.3)
│   ├── AuraRemediator
│   ├── SnapshotRemediator
│   ├── SyncRemediator
│   ├── DockerRemediator
│   └── RedisRemediator
│
└── Code remediators (Phase 15 NEW)
    ├── TimeoutRemediator (config changes)
    ├── DependencyRemediator (version fixes)
    ├── SchemaRemediator (migration generation)
    └── LLMRemediator (novel failures, uses sandbox)

orchestrate_healers.py (extend)
├── Existing: Sentry normalization → registry dispatch
└── NEW: LLM root-cause classifier before dispatch
         (correlates with Phase 14 graph + FAILURE_JOURNEY.md)

sandbox_verifier.py (NEW service)
└── 6-gate verification used by all code remediators
```

**Integration Points:**
- All remediators register via `remediation_registry.py` (single source of truth)
- `orchestrate_healers.py` gains LLM classifier (15-03)
- `sandbox_verifier.py` shared across all code remediators

### 7. Rollout Strategy

**Phase 15.0: Foundation (Read-Only)**
- Sandbox + session context + classifier + fix generation
- Detects issues, generates fixes, recommends actions
- NO auto-apply, all changes require approval
- Duration: 2-4 weeks (build confidence)

**Phase 15.1: Controlled Autonomy (Infrastructure Only)**
- Enable auto-apply for infrastructure remediations
- Allowed: Redis restart, cache clear, Docker start, connection pool tuning
- Blocked: Code changes (still require approval)
- Integrate Phase 13 kill-switch (global + per-type)
- Duration: 2-4 weeks (validate autonomous apply works)

**Phase 15.2: Full Autonomy (Code Changes)**
- Enable auto-apply for code changes with confidence ≥0.9
- Lower confidence: Create approval queue
- Document incident response (rollback, escalation, post-mortem)
- Learnings loop active (templates from LLM)

### 8. Memory Architecture (Three-Tier)

**Note:** Originally suggested as "Phase 15-07: Session Context & Memory Architecture" based on user's idea to lazy-load git commits, phase context, roadmap, and remedies as YAML/JSON. Reordered to **15-02** in priority-based plan structure (higher priority - enables all downstream features).

**The Brilliant Idea:**
User suggested lazy-loading session context as compressed YAML/JSON before adding to context window, including:
- 5 most recent git commits
- Current phase and plan
- Roadmap/birds-eye view
- Relevant remedies from long-term memory

This became the **Session Context & Memory Architecture** (15-02).

---

**Short-Term Memory (Redis, 1-hour TTL):**
```json
{
  "current_failure": "TimeoutError in src/tasks/enrichment.py",
  "recent_failures": ["KeyError 5min ago", "ConnectionError 15min ago"],
  "active_hypotheses": ["timeout too low", "connection pool exhausted"],
  "session_id": "abc123"
}
```

**Working Memory (In-Prompt Context, Session-Scoped):**
```yaml
# Lazy-loaded at session start, compressed/summarized
# Transformed from verbose data to compact YAML before context injection
session:
  current_phase: "15-self-healing-dynamic-scripting"
  current_plan: "15-02-session-context"

recent_commits:
  - hash: "a1b2c3d"
    message: "feat(graph): add backend resolver"
    files: ["src/graph/backend_resolver.py"]
  - hash: "e4f5g6h"
    message: "feat(sentry): add issue puller"
    files: ["scripts/observability/sentry_issue_puller.py"]
  # ... 3 more recent commits

relevant_remedies:
  - fingerprint: "src/tasks/enrichment.py:TimeoutError"
    description: "Increase timeout 30s → 60s"
    confidence: 0.92
  - fingerprint: "src/core/database.py:ConnectionError"
    description: "Connection pool exhausted - increase pool_size"
    confidence: 0.88
  # ... 1 more relevant remedy

roadmap_context:
  phases_complete: 14.3
  current_milestone: "M3: Self-Healing"
  current_goal: "Autonomous remediation with knowledge graph"
  next_phase: "16-admin-data-visibility"
```

**Long-Term Memory (Neo4j Graph, Adaptive Expiry):**
```cypher
// Validated templates
(template:RemedyTemplate {
    fingerprint: "...",
    pattern: "...",
    confidence: 0.92,
    applications: 5,
    created_at: "..."
})

// Failure patterns
(pattern:FailurePattern {
    signature: "...",
    frequency: 12,
    last_seen: "..."
})

// Historical episodes (from Phase 13.2)
(episode:Episode {
    type: "SYSTEM_FAILURE",
    module: "...",
    timestamp: "..."
})
```

**Memory Loading Strategy:**
- **Automatic:** Session primer loaded at start (git commits + phase + remedies + roadmap)
- **Lazy:** Compressed to YAML/JSON before adding to context window
  - Raw data transformed to compact format
  - Only top-N items (5 commits, 3 remedies, essential roadmap)
  - Reduces context window usage by ~80% vs verbose format
- **On-demand:** Additional remedies loaded when failure detected
- **Adaptive expiry:** Remedies expire when affected files change significantly

### 9. Learning Loop Parameters

**Template Promotion:**
- Threshold: 2 successful applications
- Confidence: ≥0.8 for auto-promotion to prompt memory
- Tagging: Each template has short description for matching

**Fingerprinting (Same Problem Detection):**
- Primary: Module path + error type (deterministic, fast)
  - Example: `"src/tasks/enrichment.py:TimeoutError"`
- Fallback: Semantic similarity via embeddings (fuzzy matching)
  - Threshold: 0.85 cosine similarity

**TTL (Template Expiry):**
- Adaptive: Expires when affected files change significantly
- Implementation: Track git commits, invalidate templates when file modified
- Rationale: Code changes may obsolete fix patterns

### 10. Connection Pool Auto-Tuning

**Dynamic Adjustment:**
```python
# Every hour, monitor metrics
metrics = {
    "requests_waiting": 42,        # Requests queued for DB connection
    "avg_wait_time_ms": 250,       # Average queue time
    "idle_connections": 1,          # Unused connections
    "max_overflow_hits": 156        # Times we hit max_overflow
}

# Decision logic
if requests_waiting > 10:
    pool_size += 2  # Increase pool

if idle_connections > 3 for 24h:
    pool_size -= 1  # Decrease pool

# Safety bounds
pool_size = clamp(pool_size, min=3, max=20)
```

**Observability:**
- Dashboard showing pool size over time
- Metrics: requests_waiting, idle_connections, overflow_hits
- Alerts: Pool exhaustion, configuration drift

---

## Plan Reordering (Priority + Dependencies)

**PHASE 15.0: Foundation (Read-Only Mode)**
1. **15-01:** Universal Sandbox with 6-gate verification
   - Everything depends on this - highest priority

2. **15-02:** Session Context & Memory Architecture
   - User's brilliant idea: Lazy-load git commits + phase + roadmap + remedies as YAML
   - Originally suggested as 15-07, moved to 15-02 for higher priority
   - Enables all downstream features to have proper context

3. **15-03:** Root-Cause Classifier (LLM + Graph)
   - Depends on: 15-02 for context

**PHASE 15.1: Detection & Learning (Still Read-Only)**
4. **15-04:** Autonomous Fix Generation (Templates + LLM)
   - Depends on: 15-01 sandbox, 15-03 classifier

5. **15-05:** Learnings Loop (Template extraction)
   - Depends on: 15-04 fix generation
   - Feeds back into 15-04 as templates grow

6. **15-06:** Sentry Integration Verification
   - Minimal - verify 14.3 works with 15-03 classifier

**PHASE 15.2: Controlled Autonomy (Infrastructure Auto-Apply)**
7. **15-07:** Infrastructure Bash Agent
   - Depends on: 15-01 sandbox, 15-04 fix generation
   - Auto-apply infrastructure-only remediations

8. **15-08:** Performance Profiling & Bottleneck Detection
   - Uses Phase 14 graph for impact analysis

**PHASE 15.3: Full Autonomy (Code Auto-Apply)**
9. **15-09:** Runtime Optimization Engine
   - Depends on: 15-08 profiling, 15-01 sandbox
   - Connection pools, cache TTL, batch sizes

10. **15-10:** Sentry Feedback Closure
    - Correlates remediation → issue state
    - Validates fixes actually worked

11. **15-11a:** Approval Queue Backend (Model + API)
    - PostgreSQL persistence for approvals
    - REST API for CRUD operations
    - 72h expiry with configurable TTL

12. **15-11b:** Approval Queue Interfaces (CLI + Web UI)
    - CLI commands (list, approve, reject, diff)
    - Web UI with real-time updates
    - Persists across conversations

**Rationale:**
- Sandbox first (everything depends on it)
- Session context next (enables smart classification with git commits, phase, roadmap)
- Learning loop before autonomy (build fix library first)
- Infrastructure auto-apply before code (safer, builds confidence)
- Optimization last (applies learnings to production safely)

---

## Success Criteria (Updated)

1. ✅ Sandbox passes all 6 gates before production apply
2. ✅ 95%+ of transient infrastructure issues self-heal (Redis, Docker, connections)
3. ✅ Performance optimizations proven via metrics (cost, latency, error rate)
4. ✅ Learnings loop: Templates grow from LLM successes (2+ applications → template)
5. ✅ Session context: Git commits + phase + remedies auto-loaded as compressed YAML
6. ✅ Approval queue: Changes <0.9 confidence require human review
7. ✅ Sentry-driven triage: Issues normalized and routed to classifier <5min
8. ✅ Validated remedies: Only proven fixes (via Sentry feedback) promoted to memory

---

## Tasks for After Discussion

**Immediate (Before Phase 15 Planning):**
1. Fix DBeaver connection (expose PostgreSQL port in docker-compose.yml)
2. Fix caching logic (check PostgreSQL before OpenRouter API)
3. Verify Phase 14 graph queries work (file imports, function calls, planning docs)

**Phase 16 (Separate Discussion Required):**
- Admin Data Visibility Panel
- Requires own discussion phase (scope, features, UI/UX)

---

## Dependencies

**Phase 14 (Codebase Knowledge Graph):**
- File/Module/Class/Function nodes ✅
- Import relationships ✅
- Planning doc linkage ✅
- Vector embeddings ✅

**Phase 14.3 (Graph Availability + Sync):**
- Backend resolver (three-tier fallback) ✅
- Remediation registry (NullClaw pattern) ✅
- Sentry ingestion (normalization, orchestrator) ✅
- MCP response metadata ✅

**Phase 13 (Integration Hardening):**
- Kill-switch (global + per-type) ✅
- Governance gates ✅
- Field policy (immutable fields, thresholds) ✅

---

## Open Questions for Planning Phase

1. **LLM selection:** Flash vs Sonnet vs Opus vs Adaptive routing?
2. **Session context compression:** What format? How much context? Auto-summarize?
3. **Sandbox container image:** Extend existing backend image or create new?
4. **Template storage schema:** Neo4j nodes or PostgreSQL table?
5. **Metrics collection:** Prometheus + Grafana or custom?

---

*Architecture locked: 2026-03-01*
*Ready for: Phase 15 planning (with Opus)*
