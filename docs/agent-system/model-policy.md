# Model Selection Policy — Vektal Agent System
**Version:** 1.0 | **Date:** 2026-03-08
**Broker:** OpenRouter (via Letta `lc-openrouter/` prefix or `.env` `OPENROUTER_API_KEY`)
**Principle:** Right model for the right task. Not one model for everything.
**Reference:** `docs/agent-system/commander-architecture.md`

---

## How It Works

The Commander selects the appropriate model at routing time and passes it
in the context package to every Lead. The Lead uses that model for its
execution. No Lead assumes a default — the model is always explicitly set
by the Commander based on the task type, complexity, and domain.

Model selection improves over time: `task-observer` reads the `model` field
from `TaskExecution` nodes in Aura and tracks `quality_gate_passed` per
model per task type. If a model consistently underperforms on a task type,
the Validator queue receives an ImprovementProposal to update this policy.

**Context package addition:**
```json
{
  "model": "lc-openrouter/anthropic/claude-sonnet-4-5",
  "escalation_model": "lc-openrouter/anthropic/claude-opus-4-5",
  "escalation_trigger": "string — condition that warrants escalation"
}
```

---

## OpenRouter Model Reference (Vektal-relevant)

| Alias | OpenRouter ID | Strengths | Cost tier |
|---|---|---|---|
| `haiku` | `lc-openrouter/anthropic/claude-haiku-4-5` | Fast routing, simple tasks | Low |
| `sonnet` | `lc-openrouter/anthropic/claude-sonnet-4-5` | Code, reasoning, default | Mid |
| `opus` | `lc-openrouter/anthropic/claude-opus-4-5` | Complex reasoning, architecture | High |
| `gemini-flash` | `lc-openrouter/google/gemini-flash-1-5` | Fast research, multimodal | Low |
| `gemini-pro` | `lc-openrouter/google/gemini-pro-1-5` | Deep research, long context | Mid |
| `perplexity` | `lc-openrouter/perplexity/sonar-pro` | Web-augmented research | Mid |
| `codestral` | `lc-openrouter/mistral/codestral-latest` | Code generation, completions | Mid |
| `mistral-small` | `lc-openrouter/mistral/mistral-small-latest` | Lightweight coordination | Low |

---

## Model Routing Table

### @Commander

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Session LOAD + Aura queries | `haiku` | — | — |
| Standard single-domain routing | `haiku` | — | — |
| Compound task CoT decomposition | `sonnet` | Novel architecture / ambiguous domain | `opus` |
| Circuit breaker diagnostic | `sonnet` | — | — |

**Rationale:** Commander does routing and coordination — not deep reasoning.
`haiku` handles 80% of Commander work. Escalate only for compound task
decomposition where Chain-of-Thought quality matters.

---

### @Design-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Token extraction (vision input) | `sonnet` (vision) | Complex multi-brand systems | `opus` |
| Atomic design (atoms/molecules/interactions) | `sonnet` | — | — |
| UX quality review | `sonnet` | Accessibility audit needed | `opus` |
| Frontend implementation assembly | `sonnet` | — | — |
| Visual verification (dev-browser) | No LLM — browser tool | — | — |
| E2E test writing | `codestral` | Complex async flows | `sonnet` |

**Rationale:** Design work needs strong reasoning for visual fidelity — `sonnet`
is the right default. `codestral` for test writing (code-specialised, cheaper).
Visual verification is tool-driven, no model cost.

---

### @Engineering-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Plan validation | `haiku` | — | — |
| TDD test writing | `codestral` | Complex domain logic tests | `sonnet` |
| GSD plan creation (gsd-planner) | `sonnet` | — | — |
| GSD execution (gsd-executor) | `sonnet` | Architectural deviation Rule 4 | `opus` |
| Security review (defense-in-depth) | `sonnet` | CRITICAL tier changes | `opus` |
| Data verification (postgres) | `haiku` | — | — |
| Architecture research (deep-research) | `perplexity` | Novel architecture question | `gemini-pro` |
| Branch completion | `haiku` | — | — |

**Rationale:** Code execution is `sonnet` territory. `codestral` for pure test
writing. `perplexity` for research (web-augmented answers beat pure LLM for
architecture questions). `opus` only on true architectural decisions.

---

### @Forensic-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Sentry issue intake | `haiku` | — | — |
| Failure characterisation (systematic-debugging) | `sonnet` | — | — |
| Root cause tracing | `sonnet` | — | — |
| ACH hypothesis generation | `sonnet` | — | — |
| tri-agent-bug-audit (all 4 agents) | `sonnet` | Blast radius > 10 functions | `opus` |
| Resolution brief writing | `sonnet` | — | — |
| Episode write (Graphiti) | `haiku` | — | — |

**Rationale:** Forensic work needs strong reasoning — `sonnet` default.
`opus` only when blast radius is large enough that a missed hypothesis
could cause cascading failures. `haiku` for mechanical tasks (intake, episode write).

---

### @Infrastructure-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Aura health probe | `haiku` | — | — |
| Graph sync (sync_to_neo4j.py) | No LLM — script | — | — |
| Deployment validation | `haiku` | — | — |
| varlock security check | `haiku` | Secret detected in code | `sonnet` |
| ImprovementProposal queue processing | `haiku` | — | — |
| LongTermPattern promotion | `haiku` | — | — |

**Rationale:** Infrastructure work is largely mechanical — `haiku` default.
Most tasks are tool invocations or simple status checks. No reasoning-heavy tasks.

---

### @Project-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Compound task decomposition | `sonnet` | Cross-cutting architectural concern | `opus` |
| Lead coordination | `haiku` | — | — |
| Overall quality gate validation | `sonnet` | — | — |

**Rationale:** Project Lead needs reasoning for decomposition — `sonnet`.
Coordination is mechanical — `haiku`.

---

### @Validator

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| ImprovementProposal review | `sonnet` | Proposal touches governance/auth | `opus` |
| Evidence cross-referencing (Aura) | `sonnet` | — | — |
| Rejection rationale writing | `sonnet` | — | — |

**Rationale:** Validator needs genuine reasoning to prove validity — `sonnet`.
Cannot use `haiku` here. Approving a bad proposal has downstream consequences.

---

### task-observer (background process)

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| TaskExecution outcome analysis | `haiku` | — | — |
| ImprovementProposal writing | `sonnet` | Proposal affects multiple agents | `sonnet` |

---

## Aura Integration — Model Tracking

`TaskExecution` nodes track which model was used:

```cypher
(:TaskExecution {
  ...existing fields...,
  model_used,            // e.g. "lc-openrouter/anthropic/claude-sonnet-4-5"
  model_cost_usd,        // approximate cost if available from OpenRouter response
  escalation_triggered   // bool — was escalation model used?
})
```

task-observer reads this and identifies:
- Which models have best `quality_gate_passed` rate per task type
- Which models cause loop_count > budget most often
- Where escalation is happening more than expected (→ model policy update proposal)

**This makes model selection data-driven over time.** The routing table above
is the starting point, not a fixed contract.

---

## .env Configuration

```env
# OpenRouter
OPENROUTER_API_KEY=<key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Model aliases (override defaults if needed)
MODEL_HAIKU=lc-openrouter/anthropic/claude-haiku-4-5
MODEL_SONNET=lc-openrouter/anthropic/claude-sonnet-4-5
MODEL_OPUS=lc-openrouter/anthropic/claude-opus-4-5
MODEL_RESEARCH=lc-openrouter/perplexity/sonar-pro
MODEL_CODE=lc-openrouter/mistral/codestral-latest
```

## Deferred Decisions (model-specific)

**DD-08: Model performance calibration**
Question: Are the default models above actually optimal per task type?
Why deferred: Need real TaskExecution data with model_used + quality_gate_passed.
Trigger: 20+ TaskExecutions per Lead type with model tracking.
Evidence: `avg(loop_count)` and `quality_gate_passed` rate grouped by `model_used`.
Action: task-observer proposes model policy updates based on evidence.
