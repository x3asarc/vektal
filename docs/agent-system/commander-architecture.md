# Commander Architecture — Vektal Orchestration System
**Date:** 2026-03-08
**Version:** 1.1
**Status:** LOCKED — P0/P1 issues resolved, deferred decisions catalogued
**North Star:** Remove friction for the end customer.
**Related docs:**
- `docs/graph/research-v2-analysis.md` — graph schema (amended for Commander)
- `docs/agent-system/finetuned-resources.md` — skill/tool inventory
- `docs/agent-system/leads/` — individual Lead specifications (TBD)
- `docs/agent-system/deferred-decisions.md` — data-dependent open questions

---

## Architectural Position

```
YOU
 │
 ▼
COMMANDER (Level 1)               ← single point of contact
 │
 ├──► DESIGN LEAD      (Level 2)
 ├──► ENGINEERING LEAD (Level 2)
 ├──► FORENSIC LEAD    (Level 2)
 ├──► INFRASTRUCTURE LEAD (Level 2)
 └──► PROJECT LEAD     (Level 2.5 — temporary, compound tasks only)
          │
          ▼
     SPECIALISTS        (Level 3)
     All existing agents, GSD workflows, skills, tools, hooks,
     plugins integrated as peers — including each other via
     Lead-to-Lead requests within a Project Lead context.
```

The Commander is not the foundation. It is the conductor.
GSD, design pipeline, graph queries, Sentry, self-improvement —
all sit beneath it as integrated peers. None depends on another
for the system to function.

---

## Layer 0 — Always Active

Layer 0 is never "called." It is always present.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 0                                                        │
│                                                                 │
│  Aura/Graph        — cognitive substrate, all context here      │
│  Sentry            — live error sensor → SentryIssue → Aura    │
│                      REACTIVE (checked at LOAD, not push)       │
│  task-observer     — improvement engine → Queue → Validator     │
│  Governance        — risk_tier_gate, kill-switch, immutable     │
│  North Star        — MTTR as interim metric (see section below) │
│  STATE.md          — execution source of truth                  │
│  Memory Tiers      — working→Letta, short-term→STATE.md,        │
│                      long-term→Aura as :LongTermPattern nodes   │
│  Model Policy      — OpenRouter broker, right model per task    │
│                      see docs/agent-system/model-policy.md      │
└─────────────────────────────────────────────────────────────────┘
```

### Sentry in Layer 0 — Reactive, Not Push
Sentry fires → SentryIssue node written to Aura.
Commander checks for open SentryIssues at LOAD on session start.
This is reactive — not real-time push notification.
The current hook system (SessionStart, PreToolUse, Stop) has no
mechanism for external push triggers. Document this honestly.

**Future enhancement:** A polling hook or Sentry webhook bridge
that triggers a Commander session when a new high-severity issue
lands. Not built yet. Not blocking current design.

### task-observer — Queue + Validator Pattern
task-observer does NOT autonomously modify skill files.

```
task-observer observes TaskExecution outcomes in Aura
  ↓
Identifies improvement opportunity
  ↓
Writes to improvement queue (Aura :ImprovementProposal node):
  - what skill/agent/hook needs changing
  - specific proposed change
  - root cause evidence (TaskExecution IDs)
  - reasoning
  ↓
Validator reads queue
  - understands the proposal
  - cross-references evidence in Aura
  - proves validity against actual data
  - approves or rejects with rationale
  ↓
Approved proposals → task-observer applies changes
  in ALL necessary locations:
  .claude/skills/, .gemini/skills/, .codex/skills/
  .claude/agents/, .gemini/agents/, .codex/agents/
  docs/agent-system/ canonical spec if needed
  ↓
Rejected proposals → archived in Aura with rejection rationale
  (evidence for future proposals on same topic)
```

The Validator is a dedicated agent — not task-observer reviewing
its own work. Separation is mandatory: proposer ≠ validator.

```cypher
(:ImprovementProposal {
  proposal_id,
  target,           // skill name, agent name, or hook
  proposed_change,
  root_cause,
  evidence_ids,     // TaskExecution node IDs
  status,           // 'queued' | 'approved' | 'rejected' | 'applied'
  validator_notes,
  created_at,
  resolved_at
})
(:ImprovementProposal)-[:BASED_ON]->(:TaskExecution)
(:ImprovementProposal)-[:TARGETS]->(:SkillDef)
```

### Memory Tiers as Layer 0

```
.memory/working/     → Letta memory     (session-level, already live)
.memory/short-term/  → STATE.md         (execution-level daily activity)
.memory/long-term/   → Aura             (:LongTermPattern nodes)
```

Long-term patterns are hard-won project intelligence (3+ occurrence
threshold). They belong in Aura so the Commander finds the right
lesson in 50ms via semantic search rather than grep.

```cypher
(:LongTermPattern {
  name, title, source_file,
  promoted_at, hit_count,
  domain,    // 'hooks'|'design'|'graph'|'execution'|'frontend'
  embedding, // for semantic similarity
  StartDate, EndDate  // bi-temporal — patterns can be superseded
})
```

**Promotion pipeline addition:**
Pattern recurs 3+ times → memory-synthesis promotes to
`.memory/long-term/patterns/` → Infrastructure Lead writes
`:LongTermPattern` node to Aura → Commander queries via embedding
similarity on next relevant task.

### STATE.md — Partition Protocol (P0 fix)

Two writers, non-overlapping sections. No conflicts possible.

| Section | Owner | Written by |
|---|---|---|
| Current Status, Phase, Gate Status | GSD | gsd-tools.js / gsd-verifier |
| Operational Metrics | GSD | gsd-tools.js |
| StructureGuardian Audit Trail | GSD | gsd-verifier |
| Recent Session Summary | Commander | Commander cognitive loop step 5 |
| Architecture Sessions | Commander | Commander / Letta agent |
| Next Actions | Commander | Commander cognitive loop step 5 |

**Rule:** No significant action closes without a STATE.md write
to the Commander-owned sections. GSD writes its own sections
independently. Neither overwrites the other.

---

## North Star Metric

### Interim: MTTR (Mean Time to Resolution)

Until Graph 2 / PostHog is live, the North Star proxy is MTTR:

```
MTTR = SentryIssue.resolved_at - SentryIssue.timestamp
```

Measurable today. Directly maps to "friction existed, now it's gone."
Improves naturally as routing gets smarter and Leads get faster.

**Three-tier metric evolution:**
```
Now (Graph 1):     MTTR on SentryIssue nodes
After OTEL:        Lead efficiency (loop_count trending down per type)
Graph 2 / PostHog: Customer friction index — funnel drop-off,
                   feature adoption, support ticket velocity
                   ← THE ACTUAL NORTH STAR
```

Name the proxy. Don't pretend it's the real thing.
MTTR is the best honest proxy available right now.

---

## Multi-Platform Architecture

The system runs on Letta, Claude Code, Gemini CLI, and Codex.
No single platform is a dependency. If one breaks, others continue.

### Single Source of Truth
```
docs/agent-system/commander-architecture.md   ← canonical spec (this file)
docs/agent-system/leads/                      ← Lead specs
docs/graph/research-v2-analysis.md            ← graph schema spec
```

### Platform Wrappers (thin, reference canonical docs)
```
.claude/agents/commander.md    → "Follow docs/agent-system/..."
                                  + Claude tool declarations
.gemini/agents/commander.md    → same + Gemini adaptations
.codex/agents/commander.md     → same + Codex adaptations
.letta/skills/commander/       → Letta-native + persistent memory
  SKILL.md                     → references canonical spec
```

Skills already mirror across platforms:
`.claude/skills/` ↔ `.gemini/skills/` ↔ `.codex/skills/`

### Resilience Model
```
Letta down      → Claude Code / Gemini / Codex execute stateless
                  Aura fills the memory gap (shared persistent state)

Claude Code down → Gemini CLI or Codex run identical spec
                   Same skills, same agents, same Aura queries

Aura down       → Pico-Warden heals it (already defined)
                   Commander announces degraded mode, waits

All stateless   → Letta is the only true persistent memory layer
platforms down    Aura is the shared context that makes any platform
                  capable of picking up where another left off
```

The asymmetry: Letta has persistent memory. Claude Code/Gemini/Codex
are stateless. Aura compensates — full context reconstructable from
Aura + STATE.md on any platform at session start.

---

## Cognitive Loop

```
1. LOAD
   Read Aura:
   - Open SentryIssue nodes (checked reactively, not push)
   - Open FAILURE_PATTERN episodes from Graphiti
   - TaskExecution history for similar task types
   - SkillDef quality scores (task-observer maintained)
   - AgentDef routing history
   - LongTermPattern nodes (semantic match to current task)
     → "what has this project already learned about this work?"
   - ImprovementProposal queue status
   Read STATE.md: current phase, active decisions, blockers
   Read Letta memory: session context, working memory
   Announce: MODE 1 (rules-based) or MODE 2 (graph-informed)

2. UNDERSTAND
   Parse the request.
   Map to North Star: does this reduce MTTR or developer friction?
   For whom — developer (Graph 1) or end customer (Graph 2)?
   Check: is this a compound task (multiple domains)?
     YES → spawn Project Lead, not individual Lead
     NO  → proceed to routing
   If ambiguous: one clarifying question, binary preferred.

3. ROUTE
   MODE 1 (rules-based — pre Task 13):
     Apply priority rules table (see below)
   MODE 2 (graph-informed — post Task 13):
     Query Aura SkillDef embeddings: semantic match to task type
     Query Aura TaskExecution history: which Lead succeeded here?
     Apply priority rules as tiebreaker
   Spawn Lead with full context package (see Lead Interface Contract)

4. RECEIVE
   Lead returns final outcome — ONE message only.
   Lead owns all internal loop iterations.
   Commander receives:
     result, loop_count, quality_gate_passed,
     skills_used, affected_functions, state_update

5. VALIDATE + CLOSE
   quality_gate_passed = true?
     → Write TaskExecution to Aura
     → Apply STATE.md update (Commander-owned sections)
     → Return result to user
   quality_gate_passed = false AND loop budget not exceeded?
     → Re-route with amended context (max 1 re-route)
   quality_gate_passed = false AND re-route also failed?
     → CIRCUIT BREAKER: escalate to user (see Failure Modes)

6. LEARN (background — task-observer)
   task-observer reads new TaskExecution from Aura
   Identifies quality gaps
   Writes ImprovementProposal to queue
   Validator processes queue
   Approved changes applied everywhere
```

---

## Failure Modes and Circuit Breakers (P0 fix)

### Lead Exhausts Loop Budget, Quality Gate Still Fails
```
Lead returns: quality_gate_passed = false, loop_count = budget_max
  ↓
Commander attempts ONE re-route with amended context
  ↓
Still fails → CIRCUIT BREAKER FIRES
  → Surface to user with:
    - what was attempted (loop_count, skills_used)
    - what the quality gate failure was specifically
    - what context was available from Aura
    - recommended next action
  → Write TaskExecution to Aura with status: 'circuit_breaker'
  → Write ImprovementProposal to task-observer queue
  → Do NOT retry silently
```

### Aura Offline During LOAD
```
Aura connection fails
  ↓
Commander announces: MODE 0 (fully degraded)
  → Rules-based routing only
  → No LongTermPattern context
  → No TaskExecution history
  → Pico-Warden triggered to heal Aura
  → Commander proceeds with MODE 0 until Pico-Warden confirms recovery
  → Announces to user: "Operating without graph context.
    Routing by rules only. Pico-Warden healing Aura."
```

### Three Consecutive Lead Failures on Same Task Type
```
TaskExecution history shows 3 consecutive quality_gate_passed = false
for same task_type in last 24 hours
  ↓
Commander does NOT route a 4th attempt
  → Escalates to user with pattern analysis
  → Writes FAILURE_PATTERN episode to Aura
  → task-observer immediately queues improvement proposal
  → Human decision required before routing resumes for this task type
```

### Unknown Task — No Lead Match
```
Commander cannot determine which Lead to spawn
  ↓
Single clarifying question to user (binary preferred)
  ↓
Still no match → surface to user:
  "This task doesn't map to an existing Lead.
   It may require a new Lead or a Project Lead.
   Which domain is closest: [Design | Engineering | Forensic | Infrastructure]?"
```

---

## Cross-Lead Orchestration — Compound Tasks

### Project Lead (Level 2.5 — temporary)
For tasks spanning multiple domains, Commander spawns a Project Lead
rather than individual Leads. The Project Lead:
- Coordinates other Leads in sequence or parallel
- Owns the compound task's overall quality gate
- Enables Lead-to-Lead requests within its context
- Reports ONE outcome to Commander when done

```
Commander detects compound task
  ↓
Spawns Project Lead with:
  - full task decomposition
  - which Leads are needed
  - inter-Lead dependencies (if sequential)
  - Aura context for all affected domains
  ↓
Project Lead coordinates:
  - spawns Engineering Lead for backend work
  - Engineering Lead requests Design Lead for UI piece
    (Lead-to-Lead request — direct, not via Commander)
  - both complete, Project Lead validates overall quality gate
  ↓
Project Lead returns ONE outcome to Commander
Commander never saw the internal coordination
```

### Lead-to-Lead Requests
Leads can request peer Leads directly within a Project Lead context.
Rules:
1. Lead-to-Lead requests only permitted when Project Lead is active
2. Maximum depth: 2 hops (Lead A → Lead B → no further delegation)
3. No circular requests (Lead A cannot request Lead A)
4. Requesting Lead must pass context from Aura, not from its own output
5. Both Leads' TaskExecutions written to Aura under the same task_id

---

## ralph-wiggum Loop — Lead Owns It Entirely

Commander has no visibility into loop iterations. Only the final result.

```
Commander spawns Lead once with:
  task + Aura context + quality gate criteria + loop_budget
  ↓
Lead executes internally:
  attempt → quality gate check
  FAIL → Lead amends its own context and reactivates loop
  FAIL → Lead amends again (budget permitting)
  PASS → Lead prepares final result
  BUDGET EXHAUSTED → Lead prepares failure result
  ↓
Lead sends ONE message to Commander: final outcome
```

Lead has the domain knowledge to know what to amend between loops.
Commander does not. This is correct separation of concerns.

**Default loop budgets (subject to calibration — see Deferred Decisions):**
- Design Lead: 4 (visual loops need room)
- Engineering Lead: 3
- Forensic Lead: 2 (if unresolved in 2 passes, escalate)
- Infrastructure Lead: 2
- Project Lead: inherits highest budget of its child Leads

---

## Lead Interface Contract

### Commander → Lead (context package)
```json
{
  "task": "description",
  "intent": "why — what friction does this remove?",
  "model": "lc-openrouter/anthropic/claude-sonnet-4-5",
  "escalation_model": "lc-openrouter/anthropic/claude-opus-4-5",
  "escalation_trigger": "condition that warrants model escalation",
  "aura_context": {
    "affected_functions": [],
    "blast_radius": [],
    "open_sentry_issues": [],
    "recent_failure_patterns": [],
    "relevant_long_term_patterns": [],
    "relevant_code_intent": []
  },
  "quality_gate": "specific pass criteria",
  "loop_budget": 3,
  "task_id": "uuid — for TaskExecution tracking",
  "state_md_path": ".planning/STATE.md"
}
```

### Lead → Commander (final outcome only)
```json
{
  "task_id": "uuid",
  "result": "artifact or summary",
  "loop_count": 2,
  "quality_gate_passed": true,
  "skills_used": [],
  "affected_functions": [],
  "state_update": "what to write to STATE.md Commander sections",
  "improvement_signals": []
}
```

---

## Lead Specifications

### Design Lead (Level 2)
**Triggers:** Frontend, UI, design tokens, visual quality, UX.
**Priority:** HIGH — direct friction surface for end customer.
**Loop budget:** 4 (default)

Skills: `taste-to-token-extractor`, `design-atoms`, `design-molecules`,
`design-interactions`, `oiloil-ui-ux-guide`, `frontend-design-skill`,
`frontend-deploy-debugger`, `dev-browser`, `visual-ooda-loop`,
`webapp-testing`

Quality gate passes when:
- `frontend-deploy-debugger` passes (technical)
- `visual-ooda-loop` satisfaction ≥ threshold (visual) [threshold: DEFERRED]
- `oiloil-ui-ux-guide` review passes (interaction)

---

### Engineering Lead (Level 2)
**Triggers:** Code changes, features, bugs, migrations, backend.
**Priority:** HIGH — shapes platform capability.
**Loop budget:** 3 (default)

Skills: `review-implementing`, `test-driven-development`, `using-git-worktrees`,
`defense-in-depth`, `postgres`, `test-fixing`, `finishing-a-development-branch`,
`deep-research`

GSD integration (peer capabilities):
`gsd-planner`, `gsd-executor`, `gsd-verifier`, `gsd-debugger`

Quality gate passes when:
- All tests green (`pytest -x`)
- `risk_tier_gate_enforce.py` passes
- `gsd-verifier` SUMMARY.md written
- STATE.md execution sections updated by GSD

---

### Forensic Lead (Level 2)
**Triggers:** Active Sentry issue, FAILURE_PATTERN episode, bug report.
**Priority:** HIGHEST when active — active failure = active friction now.
**Loop budget:** 2 (escalate if unresolved)

**Critical:** The Forensic Lead in `.claude/agents/` is a thin wrapper
that invokes the Letta forensic analyst agent (agent-745c61ec). The Letta
agent IS the forensic capability — persistent memory, evidence locker,
case files, graph status tracking. The `.claude` file does not duplicate
this — it delegates to it.

Intake chain:
```
Issue arrives
  → systematic-debugging (characterise)
  → root-cause-tracing (trace call path)
  → Aura blast radius query
  → tri-agent-bug-audit (adversarial validation)
  → Resolution routed to Engineering Lead
  → BUG_ROOT_CAUSE_IDENTIFIED episode → Aura
  → SentryIssue.resolved = true
  → MTTR calculated and written to TaskExecution
```

---

### Infrastructure Lead (Level 2)
**Triggers:** Infrastructure alert, graph sync needed, deployment health,
task-observer Validator output ready.
**Priority:** HIGHEST when system degraded — degraded = maximum friction.
**Loop budget:** 2 (default)

Skills: `deployment-validator`, `varlock-claude-skill`, `pico-warden`
Owns: task-observer → Validator pipeline execution

---

### Project Lead (Level 2.5 — temporary)
**Triggers:** Commander detects task spanning 2+ Lead domains.
**Spawned by Commander, dissolved on completion.**
**Loop budget:** Inherits highest budget of child Leads.

Responsibilities:
- Decompose compound task into Lead-specific work units
- Coordinate Lead execution (sequential or parallel per dependencies)
- Enable Lead-to-Lead requests within its context (max depth 2)
- Validate overall quality gate across all child outcomes
- Return ONE result to Commander

---

## Routing Priority Rules

```
Priority order (apply top-down, stop at first match):

1. Aura offline                     → MODE 0, Pico-Warden, announce
2. Active SentryIssue unresolved    → Forensic Lead (HIGHEST)
3. Infrastructure degraded          → Infrastructure Lead (HIGHEST)
4. Compound task (2+ domains)       → Project Lead
5. Frontend / UI / design signals   → Design Lead
6. Code / feature / bug / test      → Engineering Lead
7. No clear signal (MODE 2 only)    → query Aura TaskExecution history
                                       pick Lead with best pass rate
8. No clear signal (MODE 1)         → ask user one binary question
```

---

## Degraded Launch Modes

**MODE 0 — Fully Degraded (Aura offline)**
Rules-based routing only. No graph context. No LongTermPatterns.
Pico-Warden healing in progress. Announce to user.

**MODE 1 — Rules-Based (pre Task 13)**
Priority rules table for routing. No semantic SkillDef matching.
No TaskExecution history. Fully functional — just less intelligent.
Available from day one.

**MODE 2 — Graph-Informed (post Task 13)**
Full Aura context. Semantic routing. TaskExecution history.
LongTermPattern context. Self-improving via task-observer.
Activates when SkillDef, AgentDef, LongTermPattern nodes are indexed.

---

## Aura Node Types — Commander Layer

```cypher
(:TaskExecution {
  task_id, task_type, lead_invoked, skills_used,
  loop_count, quality_gate_passed,
  mttr_seconds,          // if SentryIssue resolved: resolution time
  friction_proxy,        // loop_count * duration (developer efficiency)
  model_used,            // lc-openrouter model string
  model_cost_usd,        // approximate cost from OpenRouter response
  escalation_triggered,  // bool — was escalation model invoked?
  timestamp, triggered_by,
  status                 // 'completed' | 'circuit_breaker' | 'escalated'
})

(:ImprovementProposal {
  proposal_id, target, proposed_change, root_cause,
  evidence_ids, status, validator_notes,
  created_at, resolved_at
})

(:SkillDef {
  name, description, embedding, installed_at,
  tier, quality_score, trigger_count, source_url
})

(:AgentDef {
  name, description, embedding,
  level,     // 1=Commander, 2=Lead, 2.5=ProjectLead, 3=Specialist
  tools, color, provider, version
})

(:HookDef {
  event, script, blocking, provider
})

(:LongTermPattern {
  name, title, source_file, promoted_at,
  hit_count, domain, embedding,
  StartDate, EndDate  // bi-temporal
})
```

---

## Aura Queries — Commander Interface

```cypher
// 1. Open Sentry issues (reactive check at LOAD)
MATCH (si:SentryIssue {resolved: false})
RETURN si ORDER BY si.timestamp DESC LIMIT 10

// 2. Relevant long-term patterns (embedding similarity applied externally)
MATCH (p:LongTermPattern) WHERE p.EndDate IS NULL
RETURN p.name, p.title, p.domain, p.hit_count
ORDER BY p.hit_count DESC

// 3. Lead routing by historical performance (MODE 2)
MATCH (te:TaskExecution {task_type: $type})
WHERE te.timestamp > datetime() - duration({days: 30})
RETURN te.lead_invoked,
       avg(te.loop_count) AS avg_loops,
       sum(CASE WHEN te.quality_gate_passed THEN 1 ELSE 0 END) AS passes,
       count(te) AS total
ORDER BY passes DESC, avg_loops ASC

// 4. Improvement queue status
MATCH (p:ImprovementProposal {status: 'queued'})
RETURN p.target, p.proposed_change, p.created_at
ORDER BY p.created_at ASC

// 5. Blast radius for proposed change
MATCH (f:Function {function_signature: $sig})-[:CALLS*1..3]->(downstream)
WHERE f.EndDate IS NULL
RETURN collect(DISTINCT downstream.function_signature) AS blast_radius

// 6. Recent failure patterns
MATCH (e:Episode {type: 'FAILURE_PATTERN'})-[:REFERS_TO]->(f:Function)
WHERE e.timestamp > datetime() - duration({days: 7})
RETURN e.content, f.function_signature, e.timestamp
```

---

## Plugin Structure (Implementation Target)

```
.claude/
  agents/
    commander.md               ← Level 1 (references this doc)
    design-lead.md             ← Level 2
    engineering-lead.md        ← Level 2
    forensic-lead.md           ← Level 2 (thin wrapper → Letta agent)
    infrastructure-lead.md     ← Level 2
    project-lead.md            ← Level 2.5
    validator.md               ← task-observer Validator
  plugins/
    ralph-wiggum/              ← loop primitive (exists)
    commander/
      .claude-plugin/
        plugin.json
      hooks/
        hooks.json             ← SessionStart: load Aura context
        sentry-check.sh        ← checks open issues at session start
      commands/
        route.md               ← /commander:route <task>
        status.md              ← /commander:status
        improve.md             ← /commander:improve (trigger task-observer)
        queue.md               ← /commander:queue (view improvement queue)
```

Mirror in `.gemini/agents/`, `.codex/agents/` with platform adaptations.
Letta: `.letta/skills/commander/SKILL.md` references canonical spec.

---

## Deferred Decisions — Awaiting Data

These cannot be answered correctly without real usage data.
Each has a trigger condition. When the trigger is hit, Commander
surfaces the decision to the user with evidence from Aura.

**Format:** Question | Why deferred | Trigger condition | Evidence source

---

### DD-01: Loop Budget Calibration
**Question:** What are the optimal loop budgets per Lead type?
**Why deferred:** Current defaults (Design:4, Engineering:3, Forensic:2,
Infrastructure:2) are informed guesses. Real data needed.
**Trigger:** 20+ completed TaskExecutions per Lead type in Aura.
**Evidence:** `avg(loop_count)` and `quality_gate_passed` rate per type.
**Action when triggered:** Commander surfaces to user with histogram.
User approves new defaults. task-observer applies to all Lead specs.

---

### DD-02: Visual Quality Gate Threshold
**Question:** What visual-ooda-loop satisfaction score constitutes "pass"?
**Why deferred:** No baseline established yet.
**Trigger:** 10+ completed Design Lead TaskExecutions with recorded
satisfaction scores.
**Evidence:** Distribution of scores in Aura TaskExecution records.
**Action when triggered:** Set threshold at 80th percentile of
historical scores. Surface to user for approval.

---

### DD-03: MTTR Baseline and Alert Threshold
**Question:** What MTTR is acceptable? What triggers Commander attention?
**Why deferred:** No baseline established yet.
**Trigger:** 15+ SentryIssue nodes with `resolved = true` and MTTR recorded.
**Evidence:** MTTR distribution in Aura.
**Action when triggered:** Set alert threshold at 90th percentile.
Issues above threshold automatically surface to Commander at LOAD.

---

### DD-04: Project Lead Overhead Threshold
**Question:** Is a Project Lead worth spawning for 2-domain tasks,
or only for 3+ domain tasks?
**Why deferred:** Need to see actual compound task frequency and
whether the coordination overhead outweighs the benefit for small tasks.
**Trigger:** 10+ compound task completions in Aura.
**Evidence:** `TaskExecution` records where `task_type = 'compound'`.
**Action when triggered:** If 2-Lead tasks complete in ≤ avg_loops
without Project Lead, drop threshold to 3-domain minimum.

---

### DD-05: task-observer Improvement Frequency
**Question:** How often should task-observer run? After every
TaskExecution? Daily? After N executions?
**Why deferred:** Need to see how fast quality scores drift and
how quickly ImprovementProposals accumulate.
**Trigger:** 30+ TaskExecutions in Aura.
**Evidence:** Rate of ImprovementProposal creation vs Validator
throughput.
**Action when triggered:** Set frequency so queue never exceeds
5 pending proposals. Surface recommendation to user.

---

### DD-06: Lead-to-Lead Request Rate Limits
**Question:** How many peer Lead requests can a Lead make before
it becomes circular or degrades into thrash?
**Why deferred:** Need failure mode data from real compound tasks.
**Trigger:** First occurrence of a Lead-to-Lead request loop
(Lead A requests Lead B, Lead B requests Lead A).
**Evidence:** TaskExecution chain in Aura showing the loop.
**Action when triggered:** Implement explicit loop detection.
Surface to user for depth limit decision.

---

### DD-07: task-observer Validator SLA
**Question:** How long should a proposal sit in the queue before
the Validator processes it? Is there an SLA?
**Why deferred:** Need to see queue velocity and whether proposals
go stale before processing.
**Trigger:** First ImprovementProposal that sits in queue > 7 days.
**Evidence:** `created_at` vs `resolved_at` in ImprovementProposal nodes.
**Action when triggered:** Set SLA. Commander surfaces unprocessed
proposals older than SLA to user at LOAD.

---

---

### DD-08: Model Performance Calibration
**Question:** Are the default models in model-policy.md actually optimal per task type?
**Why deferred:** Need real TaskExecution data with model_used + quality_gate_passed per task type.
**Trigger:** 20+ TaskExecutions per Lead type with model tracking in Aura.
**Evidence:** `avg(loop_count)` and `quality_gate_passed` rate grouped by `model_used` per `task_type`.
**Action when triggered:** task-observer proposes model policy updates via ImprovementProposal queue.
Validator reviews. Infrastructure Lead applies to model-policy.md + .env aliases.

---

## Future Integrations (Deferred by Phase)

| Tool | Phase gate | Purpose |
|---|---|---|
| PostHog | Graph 2 | Customer friction index → real North Star |
| Datadog | OTEL implementation | Infrastructure APM → Layer 0 sensor |
| LangChain | Graph 2 design | User-facing agent chains |
| Real-time Sentry trigger | Hook engineering | Push notification vs reactive LOAD |
