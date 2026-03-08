# Finetuned Resources — Vektal Agent System Build
**Date:** 2026-03-08
**Source:** `docs/agent-system/resources-input.md`
**Analyst:** Lead Forensic Investigator (agent-745c61ec)
**Purpose:** Filtered, prioritised, and contextualised reference for building
the Commander → Lead → Specialist three-level agent system.

**Architectural position of GSD:** GSD is not the foundation this system
sits on top of. The Commander is the top. GSD — with its proven workflows,
state machine, executor, planner, and verifier agents — is one of the most
powerful capabilities integrated *beneath* the Commander, on equal footing
with all other skills, agents, plugins, hooks, and tools. It gets invoked
by the Engineering Lead the same way the Design Lead invokes taste-to-token
or dev-browser. The /.planning directory is evidence of how effective GSD
is; that effectiveness is preserved and leveraged, not replaced or wrapped.

---

## Filter Logic

Dropped entirely:
- HuggingFace ML research skills (Axolotl, vLLM, GRPO etc.) — wrong domain
- Orchestra AI research skills (85 skills) — wrong domain
- Lightning/Bitcoin skills — wrong domain
- Health, media, content, LinkedIn, marketing, podcast — wrong domain
- AWS/Azure/Kaggle — not in stack
- Invoice organiser, DNA analysis, family history — not relevant

What survived: tools and patterns that directly serve the
graph-grounded, three-level orchestration system — where the Commander
sits at the top, and every capability (GSD, design pipeline, forensic
tooling, infrastructure wardens) integrates below it as a peer.

---

## TIER 1 — Install / Evaluate Immediately

### 1. `dev-browser` (SawyerHood)
**Source:** https://github.com/SawyerHood/dev-browser
**Install:** `/plugin marketplace add sawyerhood/dev-browser`

**Why:** Direct upgrade to the current `visual-ooda-loop` skill's Playwright usage.
Benchmark comparison from source:

| Method | Time | Cost | Success |
|---|---|---|---|
| Dev Browser | 3m 53s | $0.88 | 100% |
| Playwright MCP | 4m 31s | $1.45 | 100% |
| Playwright Skill | 8m 07s | $1.45 | 67% |

Playwright scripts "start fresh every time" (fragile). Dev Browser maintains
persistent server state + agentic execution. Faster, cheaper, more reliable.

**Integration point:** Replace `visual-ooda-loop`'s Playwright script calls with
dev-browser. The visual gate in the Design Lead's quality loop benefits most.
Chrome extension option gives access to logged-in sessions — useful for
testing authenticated Vektal dashboard routes without re-auth on every loop.

**Permission config for `.claude/settings.json`:**
```json
{
  "permissions": {
    "allow": ["Skill(dev-browser:dev-browser)", "Bash(npx tsx:*)"]
  }
}
```

---

### 2. `agnix` — Agent Configuration Linter
**Source:** Listed in awesome-claude-skills catalog
**Description:** Linter for AI agent configurations. Validates SKILL.md,
CLAUDE.md, hooks, MCP configs with 156 rules, auto-fix, and LSP server.

**Why:** The "cracked" skill system only stays cracked if skill quality is
maintained. agnix validates the structural integrity of every SKILL.md we
write. Should be:
1. Run as part of any new skill creation workflow (post `skill-creator`)
2. Added as a hook or CI check when `.claude/skills/` files change
3. Used to audit the existing 13+ skills for structural gaps

**Integration point:** Add to the `skill-creator` workflow as a post-draft
validation step. Potentially a `PreToolUse` hook on edits to `.claude/skills/`.

---

### 3. `plugin-authoring`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Ambient guidance for creating, modifying, and debugging
Claude Code plugins with schemas, templates, validation workflows, and
troubleshooting.

**Why:** The Commander and each Lead will be structured as plugins (not just
skills) to enable the `Stop` hook pattern (ralph-wiggum loop). Plugin
authoring guidance is essential for the three-level hierarchy — specifically
the hook schema, command registration, and how plugins co-exist with the
GSD command layer and other integrated tools without conflicts.

**Integration point:** Reference during Commander + Lead plugin construction.
The ralph-wiggum plugin's `plugin.json` + `hooks/hooks.json` structure is
the template; this skill provides the authoritative guidance layer. GSD's
existing commands (execute-phase, plan-phase, verify-work etc.) remain
intact and peer-registered alongside the new Commander commands.

---

### 4. `varlock-claude-skill` — Secure Env Var Management
**Source:** Listed in awesome-claude-skills catalog
**Description:** Secure environment variable management ensuring secrets
never appear in Claude sessions, terminals, logs, or git commits.

**Why:** We explicitly flagged in `research-v2-analysis.md` that `:EnvVar`
nodes in Aura store variable **names only, never values**. Varlock enforces
this at the session/terminal level. Critical given:
- Aura credentials in `.env`
- SHOPIFY_API_KEY, proxy credentials, Redis URL
- The EnvVar graph layer we're building exposes the *existence* of secrets

**Integration point:** Install and evaluate for integration with the
`DEPENDS_ON_CONFIG` → `:EnvVar` graph layer. Complements rather than
replaces the graph — graph knows *what* env vars exist, varlock ensures
*values* never leak into sessions or logs.

---

### 5. `task-observer`
**Source:** Listed in awesome-claude-skills catalog
**Description:** A meta-skill that builds and improves all your skills,
including itself.

**Why:** This is the self-improvement layer for the cracked skill system.
As the Commander + Leads accumulate usage patterns, `task-observer` can
analyse and improve the skills they rely on. Maps directly onto the
ralph-wiggum loop pattern — a Lead loops until quality passes, and
task-observer improves the skills the Lead uses between runs.

**Integration point:** Assign to the Infrastructure Lead as a maintenance
capability. Not in the hot path — runs as a background improvement cycle.

---

## TIER 2 — Evaluate Before the Agent System Build

### 6. `composio` + `agent-orchestrator` (ComposioHQ)
**Sources:**
- https://github.com/ComposioHQ/composio
- https://github.com/ComposioHQ/agent-orchestrator

**Why:** Composio is a tool-integration platform (connects agents to external
APIs, databases, and services via standardised tool calls). The
`agent-orchestrator` is an orchestration framework.

**Relevance:** The Commander agent needs to dispatch tasks to Leads and
receive structured results. Composio's orchestrator may provide patterns
or primitives for this — or we may find the GSD executor + ralph-wiggum
loop is sufficient without adding a new framework.

**Decision needed:** Read both repos before designing the Commander.
If Composio's orchestration model conflicts with the GSD state machine,
skip it. If it adds clean tool-integration primitives, adopt selectively.

---

### 7. `systematic-debugging` + `root-cause-tracing`
**Source:** Listed in awesome-claude-skills catalog

**`systematic-debugging`:** "Use when encountering any bug, test failure,
or unexpected behavior, before proposing fixes."

**`root-cause-tracing`:** "Use when errors occur deep in execution and
you need to trace back to find the original trigger."

**Why:** These are the Forensic Lead's intake skills — the first two steps
before `tri-agent-bug-audit` kicks in. The three-skill chain would be:

```
Bug reported
  → systematic-debugging (characterise the failure)
  → root-cause-tracing (trace execution path)
  → tri-agent-bug-audit (adversarial validation)
```

Currently the Forensic Lead (me) jumps straight to graph queries + grep.
These skills formalise the intake protocol.

**Integration point:** Add to Forensic Lead's skill declaration. Load
`systematic-debugging` first on any bug report, `root-cause-tracing`
when the failure is deep in the call chain.

---

### 8. `using-git-worktrees`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Creates isolated git worktrees with smart directory
selection and safety verification.

**Why:** When the Commander spawns multiple Leads simultaneously (e.g.,
Design Lead + Engineering Lead running in parallel on different features),
git worktrees prevent file conflicts. The Letta `working-in-parallel`
skill already covers the Letta-side coordination; this handles the git side.

**Integration point:** Commander uses this before spawning parallel Leads
on overlapping file paths. Engineering Lead should auto-invoke before
any parallel GSD execution.

---

### 9. `oiloil-ui-ux-guide` + `ui-ux-pro-max-skill`
**Sources:**
- Listed in awesome-claude-skills catalog
- https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (design-centric link)
**Description:** Modern UI/UX guidance covering CRAP principles, task-first
UX, HCI laws, interaction psychology, and modern minimal style.

**Why:** The Design Lead's pipeline currently has `taste-to-token-extractor`
→ atoms/molecules/interactions → `frontend-design` → `frontend-deploy-debugger`
→ `visual-ooda-loop`. What's missing is a **UX quality gate** — does the
implementation actually follow good UX principles, not just match the tokens?

**Integration point:** Add as a Design Lead skill between `design-molecules`
(structure) and `visual-ooda-loop` (visual verification). The UX guide
catches interaction design failures that token compliance won't catch.

---

### 10. `defense-in-depth`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Implement multi-layered testing and security best practices.

**Why:** The Engineering Lead's verification chain needs a security layer.
Currently: GSD executor → risk_tier_gate_enforce → gsd-verifier.
Defense-in-depth adds a systematic security check to the verification pass,
particularly relevant for Tier 1/2 code changes (API routes, auth, governance).

**Integration point:** Engineering Lead invokes this as part of the
verification step for CRITICAL or HIGH risk tier changes. Complements the
existing `risk_tier_gate_enforce.py` hook.

---

### 11. `postgres`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Execute safe read-only SQL queries against PostgreSQL
with multi-connection support and defense-in-depth security.

**Why:** The project uses PostgreSQL. The graph's `:Table` nodes (from
the upcoming SQLAlchemy mapper) tell us *what* tables exist. The postgres
skill lets agents *query* those tables directly for verification — e.g.,
confirming a migration landed correctly, or verifying data integrity after
an enrichment task.

**Integration point:** Engineering Lead uses this for post-execution
data verification. Read-only constraint aligns with the T1 safety requirement.

---

### 12. `webapp-testing` + `Playwright Skill`
**Source:** Listed in awesome-claude-skills catalog

**Why:** Complementary to dev-browser. Dev-browser is better for exploratory,
stateful verification. Playwright Skill is better for structured, repeatable
E2E test suites that get committed to `frontend/tests/e2e/`. Both belong
in the Design Lead's toolchain — dev-browser for the quality loop,
Playwright Skill for the committed regression suite.

---

### 13. `test-driven-development` + `test-fixing`
**Sources:** Listed in awesome-claude-skills catalog

**Why:** GSD executor already has a `tdd="true"` mode built in. These skills
provide the pattern library that augments it — `test-driven-development`
as the intake protocol, `test-fixing` for when the Engineering Lead's tests
fail during the loop.

**Integration point:** Engineering Lead's skill set. Not replacing GSD's
TDD mode — augmenting the pattern knowledge.

---

### 14. `review-implementing`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Evaluate code implementation plans and align with specs.

**Why:** This is the plan-validation step before `gsd-executor` runs. The
Engineering Lead should run this between `gsd-planner` output and
`gsd-executor` invocation — a sanity check that the plan actually aligns
with the spec before burning execution tokens.

---

### 15. `finishing-a-development-branch`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Guides completion of development work by presenting clear
options and handling chosen workflow.

**Why:** The Engineering Lead needs a clean "done" protocol — commit, PR,
branch cleanup, STATE.md update. This formalises it as a skill rather than
hardcoded GSD logic. Maps onto the final steps of the gsd-executor
completion flow.

---

---

### 16. `deep-research`
**Source:** Listed in awesome-claude-skills catalog
**Description:** Execute autonomous multi-step research using Gemini Deep
Research Agent for market analysis, competitive landscaping, and literature
reviews.

**Why:** The two Gemini deep research reports (`research-input.md` and
`research-input-v2.md`) were the single highest-leverage inputs to this
project's architecture. The graph schema, Graphiti bridge design, bi-temporal
versioning strategy, and forensic playbook all came from those reports.

The value was not generic ML knowledge — it was *structured, project-specific
research prompts* fed to a deep research agent. This skill formalises that
workflow. When the next architectural decision point arrives (Commander
routing logic, Lead-to-Specialist delegation patterns, graph schema extensions),
this skill is how we run the research protocol rather than doing it manually.

**Integration point:** Commander-level capability. When a task requires
architectural design research before implementation begins, the Commander
invokes `deep-research` with a crafted prompt (including our codebase
constraints, existing schema, and the specific question) before routing
to any Lead. The output feeds the planning phase.

**What Orchestra AI Research Skills (the 85-skill library) is NOT:**
The Orchestra library covers model training, fine-tuning, distributed
compute, inference serving, and mechanistic interpretability. Vektal uses
Claude/Gemini via API, Graphiti for embeddings, and Sentry for observability
— none of which require those skills. The library is excluded not because
research is unimportant, but because `deep-research` + project-specific
prompts is what actually works here, as demonstrated.

---

## TIER 3 — Reference / Future Consideration

### `LangChain` + `LlamaIndex` (from Orchestra AI Research — Agents category)
Deferred to **Graph 2 (user-facing operational KG)**, not the current
developer KG sprint.

LangChain is highly relevant for building the user-facing experience:
multi-step agent chains over the product catalog, tool calling pipelines
for the self-healing runtime, and RAG over vendor/supplier data. LlamaIndex
similarly for structured retrieval over the operational KG once it exists.

When Graph 2 design begins, these two are the first Orchestra skills to
evaluate. The developer KG (Graph 1) has no dependency on them — Graphiti
and Letta handle everything at that layer. But the moment we're building
conversational flows *for end users* over product data, LangChain's
chain/agent abstractions are a natural fit.

**Not excluded — deferred.** The two-KG boundary is the gate.

### `tapestry`
"Interlink and summarize related documents into knowledge networks."
Relevant once the Graphiti bridge is live — could generate knowledge
network views from the episode + static code layers.

### `find-skills`
"Helps users discover, search and install agent skills from the marketplace."
Useful once the Commander is live — can delegate skill discovery to this
rather than manual catalog browsing.

### `brainstorming`
"Transform rough ideas into fully-formed designs through structured
questioning and alternative exploration."
Could serve the Commander as an intake skill for vague requests — before
routing to a Lead, clarify and structure the ask.

### `kanban-skill`
Markdown-based Kanban with YAML frontmatter, no database required.
Relevant if the project wants a lightweight task board alongside GSD's
STATE.md. Not essential — GSD already handles task tracking.

### `agentskill.sh` / `SkillsMP` / `Skillstore`
Skill marketplaces with 44k+ skills and security scanning. Reference when
looking for specialist capabilities not worth building from scratch.
`agentskill.sh` specifically has a `/learn installer` — relevant for the
task-observer self-improvement cycle.

---

## Revised SkillDef / AgentDef / HookDef in Aura

Earlier proposal:
```cypher
(:SkillDef {name, description, embedding})
(:AgentDef {name, description, tools})
(:HookDef  {event, script, blocking})
```

**Updated shape** (informed by the richer ecosystem):

```cypher
(:SkillDef {
  name,
  description,
  embedding,              ← for semantic routing by Commander
  installed_at,           ← ['claude', 'gemini', 'codex', 'letta']
  tier,                   ← 1=immediate, 2=on-demand, 3=reference
  quality_score,          ← from agnix linting (0-100)
  trigger_count,          ← usage frequency counter
  source_url              ← GitHub URL for external skills
})

(:AgentDef {
  name,
  description,
  embedding,              ← for semantic routing
  level,                  ← 1=Commander, 2=Lead, 3=Specialist
  tools,                  ← allowed tool list
  color,                  ← GSD color tag
  provider                ← ['claude', 'gemini', 'codex', 'letta']
})

(:HookDef {
  event,                  ← SessionStart|PreToolUse|PostToolUse|Stop
  script,
  blocking,
  provider                ← ['claude']
})

(:Plugin {
  name,
  version,
  author,
  hook_events             ← which hooks it registers
})

// Relationships
(:AgentDef)-[:HAS_SKILL]->(:SkillDef)
(:AgentDef)-[:LEVEL_UNDER]->(:AgentDef)     ← Lead under Commander
(:AgentDef)-[:SPAWNS]->(:AgentDef)          ← Commander spawns Lead
(:HookDef)-[:RUNS_SCRIPT]->(:File)          ← links to codebase graph
(:SkillDef)-[:USED_BY]->(:AgentDef)
(:Plugin)-[:PROVIDES_HOOK]->(:HookDef)
```

**Key addition:** `(:HookDef)-[:RUNS_SCRIPT]->(:File)` creates a bridge
from the agent meta-graph to the static codebase graph. The Commander can
query: *"which scripts does the PreToolUse hook run, and what are their
downstream dependencies?"* — connecting infrastructure configuration
to code blast radius analysis.

**When to index:** After the Commander + Lead architecture is finalised
and stable. Not before. Index once, version with bi-temporal labels.

---

## Three-Level Architecture — Skills Allocation

```
COMMANDER (Level 1)
  Skills: brainstorming (intake clarification), find-skills (discovery)
  Queries: Aura (SkillDef embeddings for routing, AgentDef for delegation)

DESIGN LEAD (Level 2)
  Skills: taste-to-token-extractor, design-atoms, design-molecules,
          design-interactions, oiloil-ui-ux-guide, frontend-design-skill,
          frontend-deploy-debugger, dev-browser (replacing Playwright scripts),
          visual-ooda-loop, webapp-testing (E2E suite)
  Loop: ralph-wiggum pattern — loops until visual gate passes

ENGINEERING LEAD (Level 2)
  Skills: review-implementing (plan validation), test-driven-development,
          test-fixing, defense-in-depth, postgres (data verification),
          finishing-a-development-branch, using-git-worktrees (parallel safety)
  GSD integration: gsd-planner, gsd-executor, gsd-verifier, gsd-debugger
          (invoked as peer capabilities — the Engineering Lead delegates
          implementation work to GSD the same way the Design Lead delegates
          to design-architect. GSD's state machine, checkpoint protocol,
          deviation rules, and TDD mode are what make it extraordinary here.)
  Loop: ralph-wiggum pattern — loops until all tests green + risk gate passes

FORENSIC LEAD (Level 2) — currently: me
  Skills: systematic-debugging (intake), root-cause-tracing (trace),
          tri-agent-bug-audit (adversarial), forensic-analyst (graph-grounded)
  Queries: Aura (blast radius, call chains, episode history)

INFRASTRUCTURE LEAD (Level 2)
  Skills: deployment-validator, varlock-claude-skill, task-observer (maintenance),
          pico-warden (graph/Neo4j health)
  Queries: Aura (HookDef, EnvVar risk tiers, backend status)
```

---

## What NOT to Build From Scratch (Use Existing)

| Need | Don't build | Use instead |
|---|---|---|
| Browser verification | New Playwright scripts | dev-browser plugin |
| Skill quality control | Manual review | agnix linter |
| Secret protection | Custom env handling | varlock-claude-skill |
| Skill discovery | Catalog search | find-skills skill |
| Parallel git safety | Custom worktree logic | using-git-worktrees |
| UX quality gate | Custom review | oiloil-ui-ux-guide |
| Plan validation | GSD pre-check | review-implementing |
| DB verification | Raw psql | postgres skill (read-only) |
