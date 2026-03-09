---
name: aura-oracle
description: >
  Centralised Aura query composition engine. Domain-aware — knows what each agent type
  needs. Answers WHO/WHAT/WHERE/WHY/WHEN/HOW questions about the codebase by composing
  Cypher from building blocks. Every Lead calls this instead of writing raw Cypher.
  Add new building blocks here as the graph schema grows (Tasks 6-9 add APIRoute,
  CeleryTask, EnvVar, Table nodes — add blocks, every agent gets them for free).
triggers:
  - "query aura"
  - "ask the oracle"
  - "aura-oracle"
---

# aura-oracle — Graph Query Composition Engine

## Purpose

Agents never write raw Cypher. They call aura-oracle with:
1. **Who they are** (domain: engineering / design / forensic / infrastructure / project / bundle)
2. **What they need** (question type: WHO / WHAT / WHERE / WHY / WHEN / HOW)
3. **Context** (task description, affected paths, keywords, function signatures)

aura-oracle composes the right query from building blocks and returns structured JSON.

---

## API

```python
from .claude.skills.aura-oracle.oracle import ask

# Full domain query (recommended — runs all relevant W-questions for your domain)
result = ask(domain="engineering", context={
    "sigs": ["src.api.v1.billing.routes.create_checkout"],
    "prefix": "src/billing",
    "task": "Fix Stripe checkout session creation"
})

# Single W-question
result = ask(domain="forensic", question="WHO", context={
    "suspect": "handle_checkout_completed"
})

# Explicit building blocks (advanced)
result = ask(blocks=["calls_inbound", "sentry_unresolved", "failure_patterns"], context={
    "sigs": ["src.billing.webhooks.handle_checkout_completed"]
})
```

---

## Domain Profiles (default W-question sets per agent)

| Domain | WHO | WHAT | WHERE | WHY | WHEN | HOW |
|---|---|---|---|---|---|---|
| **engineering** | inbound callers, file owners | functions, API routes, tables | blast radius files | code intent, LT patterns | recent executions, sentry | call chain depth 2 |
| **design** | component owners | frontend files, functions | frontend/ prefix | design patterns, UX lessons | recent design executions | component hierarchy |
| **forensic** | all callers (depth 3) | sentry issues, failure patterns | culprit files | episode intent, bug patterns | failure timeline | full call chain, ACH |
| **infrastructure** | env var owners, task owners | celery tasks, routes, tables | config/, docker files | ops patterns, infra lessons | deployment history | dependency map |
| **project** | lead history, skill quality | templates, lessons, patterns | all domains | architectural decisions | execution history | compound routing |
| **bundle** | template history | skill defs, agent defs | all | lessons per lead | quality scores | model assignment |

---

## Building Blocks (composable units — add new ones as schema grows)

### Node Selectors
- `file_nodes` — File nodes (path, module)
- `function_nodes` — Function nodes (sig, name, file_path) — active only
- `class_nodes` — Class nodes
- `api_route_nodes` — APIRoute nodes (method, path, handler) [Task 6]
- `celery_task_nodes` — CeleryTask nodes (name, queue) [Task 6]
- `env_var_nodes` — EnvVar nodes — names + risk_tier ONLY, never values [Task 7]
- `table_nodes` — SQLAlchemy Table nodes [Task 8]
- `sentry_unresolved` — Unresolved SentryIssue nodes
- `bundle_templates` — BundleTemplate nodes (ranked by quality)
- `active_lessons` — Lesson nodes with status=active
- `long_term_patterns` — LongTermPattern nodes by domain
- `task_executions` — TaskExecution history
- `skill_defs` — SkillDef nodes
- `agent_defs` — AgentDef nodes
- `planning_docs` — PlanningDoc nodes

### Traversals
- `calls_outbound_1` — [:CALLS] depth 1 outbound
- `calls_outbound_2` — [:CALLS*1..2] depth 2 outbound
- `calls_inbound` — inbound [:CALLS] callers
- `calls_inbound_deep` — inbound [:CALLS*1..3] all ancestors
- `defined_in` — [:DEFINED_IN] function→file
- `imports_graph` — [:IMPORTS] file→file
- `applies_to_lead` — [:APPLIES_TO]→AgentDef (for Lessons)
- `refers_to_function` — [:REFERS_TO]→Function (Episode bridge)

### HOW Blocks (Data Flow & Dependency Chains)
- `full_call_chain` — full inbound + outbound call graph for a suspect function
- `data_access_chain` — Function→ACCESSES→Table (what DB tables does this code touch) [Task 8]
- `route_to_function_chain` — APIRoute→handler function chain [Task 6]

### Cross-Domain Blocks (Gemini recommendation — the missing link)
- `cross_domain_impact` — detects IMPORTS/CALLS crossing folder boundaries (frontend→src, billing→core, etc.) — #1 source of hidden regressions
- `cross_domain_env_coupling` — EnvVar nodes consumed across domain boundaries — infra change silently breaks engineering [Task 7]
- `cross_domain_route_coupling` — API routes called by unexpected domains — shared state / race condition detector [Task 6]

**These three blocks are automatically included in project-lead (all three), engineering-lead, design-lead, forensic-lead, and infrastructure-lead profiles.**

### Filters
- `active_only` — EndDate IS NULL
- `path_prefix` — file path STARTS WITH $prefix
- `path_keywords` — file path contains any keyword from $keywords
- `in_domain` — domain IN $domains
- `unresolved` — resolved = false (Sentry)
- `sigs_match` — function_signature IN $sigs
- `contains_suspect` — function_signature CONTAINS $suspect

---

## How to Add a New Building Block

1. Add an entry to `BLOCKS` dict in `oracle.py`
2. Add it to the relevant `DOMAIN_PROFILES` question sets
3. That's it — all agents using that domain get the new block automatically

```python
# Example: Task 6 adds CeleryTask nodes
BLOCKS["celery_task_nodes"] = {
    "description": "All CeleryTask nodes with queue assignment",
    "cypher": "MATCH (ct:CeleryTask) RETURN ct.name, ct.queue, ct.file_path",
    "limit": 30,
    "schema_task": 6,  # available after graph sprint Task 6
}
DOMAIN_PROFILES["infrastructure"]["WHAT"].append("celery_task_nodes")
```

---

## CLI Usage

```bash
# List all available blocks
python .claude/skills/aura-oracle/oracle.py --list

# Run full domain profile
python .claude/skills/aura-oracle/oracle.py --domain engineering --context '{"prefix":"src/billing"}'

# Ask a single W-question
python .claude/skills/aura-oracle/oracle.py --domain forensic --question WHO --context '{"suspect":"handle_checkout"}'

# Run specific blocks
python .claude/skills/aura-oracle/oracle.py --blocks calls_inbound,sentry_unresolved --context '{"sigs":["src.billing.webhooks.handle_checkout_completed"]}'
```
