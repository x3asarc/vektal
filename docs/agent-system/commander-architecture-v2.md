# Commander Architecture v2.0 — Vektal Orchestration System
**Date:** 2026-03-09
**Version:** 2.0 — Forensic Partnership Edition
**Status:** ACTIVE
**Supersedes:** `docs/agent-system/commander-architecture.md` (v1.1 archived — do not delete)
**North Star:** Remove friction for the end customer.

**What changed from v1:**
- Forensic Partnership (Watson + Lestrade) integrated into cognitive loop
- Bundle made mandatory step between routing and Lead execution
- aura-oracle wired as universal read gateway for all graph context
- Model assignments reference model-rationale.md v2.0 (no Anthropic monoculture)
- task-observer oracle shortcoming loop added to Layer 0
- P-LOAD formally defined and wired
- Meta-routing utility models updated to 2026 stack

---

## Architectural Position

```
YOU
 │
 ▼
COMMANDER (Level 1)                ← single point of contact
 │
 ├──► WATSON           (Forensic Partnership peer — scope authority)
 │      └──► LESTRADE  (exceptional deadlock arbiter — o4-mini, one-shot)
 ├──► BUNDLE           (mandatory configuration gate before all Leads)
 ├──► DESIGN LEAD      (Level 2)
 ├──► ENGINEERING LEAD (Level 2)
 ├──► FORENSIC LEAD    (Level 2)
 ├──► INFRASTRUCTURE LEAD (Level 2)
 └──► PROJECT LEAD     (Level 2.5 — compound tasks only)
          │
          ▼
     SPECIALISTS (Level 3)
     GSD workflows, skills, tools, hooks, plugins — integrated as peers
```

Commander is the conductor, not the foundation.
GSD, design pipeline, aura-oracle, Sentry, Watson — all sit beneath it as integrated peers.

---

## Layer 0 — Always Active

Layer 0 is never "called." It is always present.

```
┌──────────────────────────────────────────────────────────────────────┐
│  LAYER 0                                                             │
│                                                                      │
│  aura-oracle       — read gateway for ALL graph context              │
│                      ask(domain, question, context) → structured JSON│
│                      every agent reads Aura through this, not raw    │
│                      Cypher. oracle shortcoming loop feeds back here │
│                                                                      │
│  Aura/Graph        — cognitive substrate, all persistent state here  │
│  Sentry            — live error sensor → SentryIssue → Aura         │
│                      REACTIVE (checked at LOAD via aura-oracle,      │
│                      not push. Future: Sentry webhook bridge)        │
│  task-observer     — improvement engine → Queue → Validator          │
│                      includes oracle gap detection (new in v2)       │
│  Governance        — risk_tier_gate, kill-switch, immutable fields   │
│  North Star        — MTTR as interim metric                          │
│  STATE.md          — execution source of truth                       │
│  Memory Tiers      — working→Letta, short-term→STATE.md,             │
│                      long-term→Aura as :LongTermPattern nodes        │
│  Model Policy      — model-rationale.md v2.0 (base models)          │
│                      model-policy.md (quality floors + utility)      │
│  Meta-Routing      — utility models on every request:                │
│    classifier  → gemini-3.1-flash-lite (domain classification)       │
│    difficulty  → gemini-3.1-flash-lite (LOW/STANDARD/HIGH/CRITICAL)  │
│    json-valid  → mistralai/mistral-small-3.2 (outcome schema)        │
│    summarizer  → openai/gpt-5-nano (STATE.md + Aura compression)     │
└──────────────────────────────────────────────────────────────────────┘
```

### aura-oracle — The Read Gateway

All graph reads flow through `aura-oracle`. No agent writes raw Cypher for discovery.

```python
from .agents.skills.aura_oracle.oracle import ask

# Commander LOAD
p_load = ask(domain="project", context={"domains": [...], "keywords": [...]})

# Watson blind analysis
context = ask(domain="forensic", context={"sigs": [...], "prefix": "src/billing"})

# Engineering Lead pre-execution
ctx = ask(domain="engineering", context={"sigs": [...], "fps": [...]})
```

Watson's **Casebook reads** are an exception — they use direct Cypher with git-entropy decay
weighting. That logic is too Watson-specific for a generic oracle block.

Watson's **GHOST_DATA detection** (`W-METADATA-DENSITY`) uses oracle count=0 results directly.
When oracle returns `count: 0` for a block with `schema_task` set, that is the GHOST_DATA signal.

### Oracle Shortcoming Loop (Layer 0 self-healing)

When oracle blocks consistently return `count: 0` because a graph sprint hasn't run,
task-observer detects the pattern and surfaces an ImprovementProposal:

```
oracle block returns count=0 (schema_task set)
  ↓
Commander writes oracle_gaps to TaskExecution node
  ↓
task-observer: same block_name appears in oracle_gaps 3+ times in 14 days
  ↓
ImprovementProposal: target="graph-sprint:task-N", sync_command="python scripts/graph/sync_X.py"
  ↓
Commander sees proposal at LOAD → surfaces to user as Layer 0 priority
  ↓
User runs sync script → nodes indexed → oracle returns real data → gap closes
```

### task-observer — Queue + Validator Pattern

Unchanged from v1. See `docs/agent-system/specs/task-observer.md`.

Oracle gap detection is a new pattern class (v2 addition) — see task-observer spec.

### Sentry in Layer 0 — Reactive, Not Push

Unchanged from v1. Future Sentry webhook bridge deferred.

### STATE.md Partition Protocol

Unchanged from v1. Two writers (GSD + Commander), non-overlapping sections.

---

## Forensic Partnership

### Authority Partition

| Authority | Owner | Notes |
|---|---|---|
| Lead selection + domain routing | Commander | Watson cannot re-route |
| Scope tier + loop budget | Watson | Commander cannot downgrade Watson's final |
| GHOST_DATA disclosure | Watson | Sole issuer |
| Lestrade invocation | Watson | Exceptional only — ESCALATE + OVERRIDE deadlock |
| TaskExecution write | Commander | After Lead completes |
| Casebook write | Watson | After adjudication + PostMortem |

### What is Lestrade?

Lestrade is **not an agent**. It is a one-shot call to `openai/o4-mini` fired only when:
1. Watson verdict = `ESCALATE`
2. Commander adjudication = `OVERRIDE` (refuses to accept)

Input: ~300 tokens (Watson's ESCALATE evidence + Commander's override justification).
Output: exactly one word — `WATSON` / `COMMANDER` / `HUMAN_REQUIRED`.
No memory, no system prompt, no Aura access. Timeout: 60s. Default on timeout: WATSON + human notification.

Named after Inspector Lestrade (Sherlock Holmes) — the third party who decides when
two strong opinions deadlock.

### Blind Spawn Protocol

Watson and Commander run **in parallel** on the same P-LOAD. No communication until
Watson calls `W-LOCK-ASSESSMENT`. If Commander sends Watson its RoutingDraft before
Watson locks — `BLIND_PROTOCOL_VIOLATION` — task restarts from scratch.

### P-LOAD Definition

The P-LOAD is the raw context object passed identically to both Commander and Watson
at session start. Built by Commander via `ask(domain="project")`.

```json
{
  "sentry_issues":                [],   // open SentryIssue nodes
  "long_term_patterns":           [],   // LongTermPattern nodes (domain match)
  "task_executions":              [],   // recent TaskExecution history
  "skill_quality":                [],   // SkillDef quality scores
  "improvement_proposals_pending":[],   // queued ImprovementProposal nodes
  "oracle_gaps_recent":           [],   // blocks returning count=0 in last 7 days
  "bundle_template_history":      [],   // BundleTemplate quality + trigger counts
  "agent_defs":                   [],   // registered agents + Letta IDs
  "planning_docs":                []    // PlanningDoc nodes (task keyword match)
}
```

Watson receives this object as **Input Contract A** (blind phase).
Commander builds its RoutingDraft from the same object.
Neither receives the other's analysis until Watson locks.

---

## Cognitive Loop (v2)

```
1. LOAD
   ask(domain="project", context={task_keywords}) → P-LOAD
   Surface oracle gap proposals if any (Layer 0 check — non-blocking)
   Surface queued ImprovementProposals (Layer 0 check — non-blocking)
   Read STATE.md: current phase, active decisions, blockers
   Read Letta memory: session context
   Announce: MODE 0 (Aura offline) | MODE 1 (rules-based) | MODE 2 (graph-informed)

2. UNDERSTAND
   [META-ROUTING — gemini-3.1-flash-lite, near-zero cost]
   Task Classifier → domain: coding/design/forensic/infra/compound
   Difficulty Estimator → tier: LOW/STANDARD/HIGH/CRITICAL
   Tool Selector → model or tool?
   Map to North Star: MTTR reduction or developer friction?
   Check: compound task (2+ domains)? YES → Project Lead, NO → single Lead

3. BLIND SPAWN (parallel)
   Commander begins RoutingDraft
   Watson spawned simultaneously with Input Contract A (P-LOAD, no RoutingDraft)
   Watson runs W-ORACLE + W-METADATA-DENSITY + W-CASEBOOK-READ + Three Lenses
   Watson calls W-LOCK-ASSESSMENT → signals Commander: "locked, ready for Reveal"

4. FORENSIC PARTNERSHIP — REVEAL
   Commander sends RoutingDraft to Watson (Input Contract B)
   Watson computes delta + coupling check + scope authority
   Watson returns ChallengeReport (Output Contract A):
     - calibration_score + calibration_label
     - verdict: APPROVED / REVISE / ESCALATE
     - scope_tier_final + loop_budget_final (binding)
     - challenges[] with evidence
     - ghost_data_flags[]
   
   Commander adjudicates:
     APPROVED → proceed to BUNDLE
     REVISE   → update context package, re-send to Bundle (Watson's scope still binding)
     ESCALATE + ACCEPT → proceed with Watson's scope
     ESCALATE + OVERRIDE → Lestrade → WATSON/COMMANDER/HUMAN_REQUIRED

5. BUNDLE
   Commander sends Watson-validated context package to Bundle
   Bundle queries Aura: BundleTemplate match + Lesson injection
   Bundle returns BundleConfig:
     - leads[] + lead_configs (model, loop_budget, lessons_from_history)
     - scope_tier_final + watson_validation_summary (echoed to Lead)
     - difficulty_tier
   If NANO bypass (blast_radius ≤ 2, sentry_errors = 0): Bundle skips Aura queries,
   returns minimal config immediately.

6. EXECUTE
   Spawn Lead(s) with BundleConfig context package
   Lead owns all loop iterations (ralph-wiggum pattern — Commander has no visibility)

7. RECEIVE
   [OUTPUT META-LAYER — before Commander processes]
   JSON Validator (mistral-small-3.2) → validates outcome schema, fixes if malformed
   Summarizer-Tiny (gpt-5-nano) → compresses for STATE.md + Aura episode
   Commander receives: result, loop_count, quality_gate_passed, skills_used,
                       affected_functions, oracle_gaps (from Lead's aura-oracle calls)

8. VALIDATE + CLOSE
   quality_gate_passed = true?
     → Write TaskExecution to Aura (includes oracle_gaps field)
     → Signal Watson: PostMortem (Input Contract C)
     → Apply STATE.md update (Commander-owned sections)
     → Return result to user
   quality_gate_passed = false AND budget not exceeded?
     → Re-route with amended context (max 1 re-route)
   quality_gate_passed = false AND re-route also failed?
     → CIRCUIT BREAKER (see Failure Modes)

9. LEARN (background — task-observer)
   task-observer reads new TaskExecution from Aura
   Oracle gap detection: block_name in oracle_gaps 3+ times → ImprovementProposal
   Quality detection: loop_count > budget, gate failures → ImprovementProposal
   Validator processes queue → approved changes applied everywhere
   Watson PostMortem: writes OBSERVED edge + Outcome node to Casebook
```

---

## Degraded Launch Modes

**MODE 0 — Fully Degraded (Aura offline)**
aura-oracle returns error. Rules-based routing only. No graph context. No P-LOAD.
Pico-Warden healing in progress. Watson NOT spawned (no P-LOAD to give it).
Bundle bypassed (NANO config only). Announce to user.

**MODE 1 — Rules-Based**
aura-oracle returns data. P-LOAD populated. Watson spawned normally.
No semantic SkillDef matching (TaskExecution history thin). Routing by priority rules.

**MODE 2 — Graph-Informed**
Full Aura context. Semantic routing via SkillDef embeddings. TaskExecution history.
LongTermPattern context. Watson calibrated (Casebook populated).
Activates when: SkillDef + AgentDef + LongTermPattern nodes indexed AND 20+ TaskExecutions.

---

## aura-oracle Domain Profiles (reference)

| Domain | Used by | Key blocks |
|---|---|---|
| `project` | Commander LOAD | agent_defs, skill_defs, improvement_proposals, oracle_gaps_recent, sentry_unresolved, long_term_patterns, bundle_template_history, cross_domain_* |
| `forensic` | Watson blind phase | calls_inbound_deep, sentry_unresolved, blast_radius, failure_timeline, full_call_chain, cross_domain_impact |
| `engineering` | Engineering Lead | calls_inbound, function_nodes, blast_radius, import_chain, sentry_for_files, data_access_chain |
| `design` | Design Lead | file_owners, function_nodes, files_by_prefix, long_term_patterns |
| `infrastructure` | Infrastructure Lead | env_var_nodes, celery_task_nodes, table_nodes, cross_domain_env_coupling |
| `bundle` | Bundle (config) | agent_defs, skill_defs, active_lessons, bundle_template_history |

Full block definitions: `.agents/skills/aura-oracle/oracle.py`

---

## Lead Interface Contract (v2)

### Commander → Bundle
```json
{
  "task": "string",
  "intent": "string — what friction does this remove?",
  "domain_hint": "engineering | design | forensic | infrastructure | compound",
  "quality_gate": "string",
  "scope_tier_proposed": "NANO | MICRO | STANDARD | COMPOUND | RESEARCH",
  "scope_tier_final": "string — Watson's binding final",
  "loop_budget_proposed": 3,
  "loop_budget_final": 4,
  "nano_bypass": false,
  "watson_validation": { "verdict": "...", "calibration_score": 0.0, ... },
  "aura_context": { "...p_load fields..." }
}
```

### Bundle → Lead (via BundleConfig)
```json
{
  "task": "string",
  "intent": "string",
  "scope_tier_final": "STANDARD",
  "watson_validation_summary": "string — condensed challenge report",
  "model_requested": "lc-openrouter/...",
  "quality_floors": { "security_critical": "..." },
  "loop_budget": 4,
  "skills_override": [],
  "lessons_from_history": [],
  "task_id": "uuid",
  "oracle_context": { "...aura-oracle results for this lead's domain..." }
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
  "oracle_gaps": [],
  "state_update": "string",
  "improvement_signals": []
}
```

---

## Model Assignments (v2)

**Base models:** See `docs/agent-system/model-rationale.md` (Forensic Mapping v2.0)
**Quality floors + utility models:** See `docs/agent-system/model-policy.md`

Summary:
| Agent | Base model | Source |
|---|---|---|
| Commander | grok-3 | model-rationale.md |
| Watson | claude-opus-4.6 | model-rationale.md (only Anthropic in stack) |
| Bundle | gemini-2.5-flash | model-rationale.md |
| Engineering Lead | gpt-4o | model-rationale.md |
| Design Lead | kimi-k2.5 | model-rationale.md |
| Forensic Lead | deepseek-v3.2 | model-rationale.md |
| Infrastructure Lead | glm-4.6 | model-rationale.md |
| Project Lead | gemini-2.5-flash | model-rationale.md |
| task-observer | gemini-2.5-flash-lite | model-rationale.md |
| Validator | gpt-4o-mini | model-rationale.md |
| Lestrade | o4-mini (direct API) | Watson spec — not a registered Letta agent |

All via `lc-openrouter/*` prefix — routes through `OPENROUTER_API_KEY`. No Letta credits.

---

## Aura Node Types — Full Schema (v2)

### Layer 0 — Always present
```cypher
(:TaskExecution {
  task_id, task_type, lead_invoked, skills_used,
  loop_count, quality_gate_passed,
  mttr_seconds, friction_proxy,
  model_used, model_cost_usd,
  escalation_triggered, escalation_reason,
  difficulty_tier, scope_tier_final,
  oracle_gaps: [string],    // NEW v2 — block names that returned count=0
  timestamp, triggered_by, status
})

(:ImprovementProposal {
  proposal_id, target, proposed_change, root_cause,
  evidence_ids, sync_command,    // NEW v2 — for oracle gap proposals
  status, validator_notes,
  created_at, resolved_at
})

(:SkillDef { name, description, embedding, installed_at, tier, quality_score, trigger_count })
(:AgentDef { name, description, embedding, level, tools, color, provider, version, letta_agent_id })
(:HookDef  { event, script, blocking, provider })
(:LongTermPattern { name, title, domain, embedding, hit_count, StartDate, EndDate })
```

### Forensic Partnership — Watson Casebook
```cypher
(:Case { task_id, domain, opened_at, git_hash_at_open, commit_count_at_open })

(:AgentDef {name:'commander'})-[:DEDUCED {
  routing_draft, scope_claimed, quality_gate
}]->(c:Case)

(:AgentDef {name:'watson'})-[:OBSERVED {
  challenge_report, scope_set, calibration_score, verdict
}]->(c:Case)

(c:Case)-[:RESULTED_IN]->(o:Outcome {
  task_id, outcome_rating, failure_mode,
  git_commits_since, watson_verdict_correct, commander_override_correct
})
```

### Bundle Learning
```cypher
(:BundleTemplate { template_id, name, domains, leads, model_assignments,
                   budget_allocation, skills_override, compound_gate,
                   trigger_count, last_quality_score, avg_loop_count,
                   is_template, created_at, updated_at })

(:Lesson { lesson, confidence, failure_count, pattern, status,
           applies_to_bundle })-[:APPLIES_TO]->(:AgentDef)
```

### Codebase (graph sprint)
```
File, Function, Class, APIRoute [T6], CeleryTask [T6],
EnvVar [T7], Table [T8], Episode [T11]
```
[T6–T11]: available after corresponding graph sprint task runs.

---

## Failure Modes and Circuit Breakers

### Lead Exhausts Budget, Gate Fails
Unchanged from v1. Commander re-routes once. Still fails → CIRCUIT BREAKER.
Writes `status: 'circuit_breaker'` to TaskExecution. ImprovementProposal queued.

### Aura Offline During LOAD
MODE 0. aura-oracle raises connection error. Watson NOT spawned.
Bundle returns NANO config. Pico-Warden triggered.

### Three Consecutive Failures Same Task Type
Unchanged from v1. Human decision required before 4th routing.

### Watson BLIND_PROTOCOL_VIOLATION
Commander sends RoutingDraft before Watson locks assessment.
Task restarted from scratch. Human notified. Logged to Aura.

### Lestrade Timeout
Watson ESCALATE + Commander OVERRIDE + Lestrade fails to return in 60s.
Default: WATSON verdict applied. Human notified with both arguments.

---

## Routing Priority Rules

```
1. Aura offline                     → MODE 0, Pico-Warden, announce
2. Active SentryIssue unresolved    → Forensic Lead (HIGHEST)
3. Infrastructure degraded          → Infrastructure Lead (HIGHEST)
4. Compound task (2+ domains)       → Project Lead
5. Frontend / UI / design signals   → Design Lead
6. Code / feature / bug / test      → Engineering Lead
7. No clear signal (MODE 2 only)    → Aura TaskExecution history — best Lead pass rate
8. No clear signal (MODE 1)         → one binary question to user
```

NANO bypass condition: `blast_radius ≤ 2 AND sentry_error_count = 0`
→ Watson invoked but lock is advisory only. Bundle returns minimal config.

---

## Deferred Decisions (v2)

Carried forward from v1 (DD-01 through DD-09 — unchanged):
DD-01: Loop budget calibration | DD-02: Visual quality gate threshold
DD-03: MTTR baseline | DD-04: Project Lead overhead threshold
DD-05: task-observer frequency | DD-06: Lead-to-Lead rate limits
DD-07: Validator SLA | DD-08: Model performance calibration
DD-09: Meta-routing classifier accuracy

**New in v2:**

### DD-10: Oracle Gap Threshold
**Question:** What is the correct occurrence threshold before task-observer fires an oracle gap ImprovementProposal?
**Why deferred:** Default of 3 occurrences in 14 days is a guess. May produce false positives if a task type genuinely never touches certain domains (e.g., a pure frontend task never needs `api_route_nodes`).
**Trigger:** First ImprovementProposal that is rejected by Validator because the block gap was expected (domain mismatch, not a real schema gap).
**Action:** Refine threshold per domain pair (block × task_type). Infrastructure Lead applies.

### DD-11: LongTermPattern Promotion Pipeline
**Question:** When does the `memory-synthesis → .memory/long-term/ → Infrastructure Lead → :LongTermPattern` pipeline get built?
**Why deferred:** Requires real session data to identify which patterns actually recur 3+ times. Currently patterns are manually promoted.
**Trigger:** 50+ TaskExecutions in Aura with detectable recurring patterns that aren't captured as LongTermPattern nodes.
**Action:** Build promotion script. Infrastructure Lead owns the pipeline.

---

## Multi-Platform Architecture

Unchanged from v1.
Aura compensates for stateless platforms — full context reconstructable from Aura + STATE.md.
Letta is the only platform with persistent memory.
If Letta is down → Claude Code / Gemini / Codex execute stateless using Aura + STATE.md.

---

## What's Implemented vs Deferred

| Feature | Status |
|---|---|
| Commander registered in Letta (grok-3) | LIVE |
| Watson registered in Letta (claude-opus-4.6) | LIVE |
| Bundle registered + Watson-aware contract | LIVE |
| All Leads registered with model-rationale.md models | LIVE |
| aura-oracle skill (oracle.py + queries.py) | LIVE — schema_task guard bug pending fix |
| Commander LOAD via aura-oracle | PENDING — T2 of current plan |
| Watson Casebook (Case/Outcome nodes in Aura) | EMPTY — cold start, builds with usage |
| task-observer oracle gap detection | PENDING — T3 of current plan |
| Graph sprint Tasks 6–9 (APIRoute, EnvVar, Table, CeleryTask) | PARTIAL — sync scripts exist, not run |
| sync_orchestration.py (AgentDef + SkillDef nodes) | EXISTS — needs run with new agent IDs |
| Lestrade arbitration | SPEC ONLY — no implementation needed (1 API call) |
| NANO bypass | SPEC ONLY — Commander + Bundle spec, not coded |
| Sentry webhook bridge | DEFERRED — DD future |
| LongTermPattern promotion pipeline | DEFERRED — DD-11 |
| PostHog customer friction index | DEFERRED — Graph 2 |

---

*Canonical spec. Platform wrappers in `.letta/.claude/.codex/.gemini/agents/commander.md` reference this document.*
*Model assignments: `docs/agent-system/model-rationale.md`*
*Quality floors: `docs/agent-system/model-policy.md`*
*Watson spec: `docs/agent-system/specs/watson.md`*
*aura-oracle: `.agents/skills/aura-oracle/oracle.py`*
