# Model Selection Policy — Vektal Agent System
**Version:** 1.1 | **Date:** 2026-03-08
**Broker:** OpenRouter (via Letta `lc-openrouter/` prefix or `.env` `OPENROUTER_API_KEY`)
**Reference:** Perplexity Computer architecture (19-model orchestration pattern)
**Key insight:** Most models in a well-designed system are tiny glue/utility models.
Frontier models are called rarely. Utility models run on every request.

---

## Architectural Pattern — Meta-Routing Layer

Before any Lead executes, the Commander runs a lightweight meta-routing step.
Tiny classifier models decide what the big models should do.
This is how Perplexity Computer orchestrates 19 models efficiently.

```
Request arrives at Commander
  ↓
[META-ROUTING LAYER — tiny models, always-on]
  Step 1: Task Classifier    → what domain? (coding/design/forensic/infra/compound)
  Step 2: Difficulty Est.    → complexity tier? (LOW / STANDARD / HIGH / CRITICAL)
  Step 3: Tool Selector      → model or tool? (browser / shell / DB / LLM)
  ↓
[MODEL SELECTION — based on classifier + difficulty output]
  Commander picks Lead + model from routing table below
  ↓
[LEAD EXECUTES]
  ↓
[OUTPUT LAYER — tiny models, always-on]
  Step 4: JSON Validator     → Lead outcome schema-valid?
  Step 5: Summarizer-Tiny    → compress outcome for STATE.md / Aura episode
```

The big frontier models (Opus, GPT-5, Gemini Ultra) are called rarely.
Utility models (classifier, estimator, validator, summarizer) run on every request.

---

## Complexity Tiers

| Tier | Meaning | Default model family |
|---|---|---|
| LOW | Mechanical, no reasoning required | haiku-class / GPT-4o-mini |
| STANDARD | Requires reasoning, standard task | sonnet-class / GPT-4o |
| HIGH | Complex multi-step, high stakes | sonnet-class (tools-tuned) |
| CRITICAL | Architecture decisions, max accuracy | opus-class / o3 |

Difficulty Estimator classifies every task before model selection.
Prevents paying opus prices for haiku-grade work.

---

## OpenRouter Model Reference

OpenRouter provides access to all of the below under a single API key.
Use `lc-openrouter/<provider>/<model-id>` format in Letta.

### Anthropic (Claude)

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `opus` | `anthropic/claude-opus-4` | CRITICAL | Deep reasoning, orchestration, multi-step planning, hardest coding/logic |
| `sonnet` | `anthropic/claude-sonnet-4-5` | STANDARD/HIGH | Default for most text + coding — quality without opus cost |
| `sonnet-tools` | `anthropic/claude-sonnet-4-5` + tools header | HIGH | When many function calls, DB queries, or tool hops are expected |
| `haiku` | `anthropic/claude-haiku-3-5` | LOW | Fast classification, rewriting, small edits — latency and price dominate |

> **Internal variants not on OpenRouter (prompt-engineered equivalents):**
> - Claude "Planner" → `opus` + system prompt: task decomposition specialist
> - Claude "Critic" → `sonnet` + system prompt: second-pass adversarial reviewer

### OpenAI (GPT)

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `gpt5` | `openai/gpt-4o` (proxy until GPT-5 on OR) | STANDARD | General workhorse, OpenAI slot |
| `gpt4o` | `openai/gpt-4o` | STANDARD | Multimodal (image + text + speed), everyday UX tasks |
| `gpt4o-mini` | `openai/gpt-4o-mini` | LOW | Super low-latency — routing, tagging, format conversion |
| `o3` | `openai/o3` | CRITICAL | Heavy reasoning — math/logic branches where cost is acceptable |
| `gpt-vision` | `openai/gpt-4o` (vision mode) | STANDARD | OCR, charts, UI screenshots |

### Google (Gemini)

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `gemini-pro` | `google/gemini-pro-1-5` | STANDARD | Structured web research, multi-click browsing, RAG chains |
| `gemini-ultra` | `google/gemini-2-0-flash-exp` (proxy) | HIGH | Max Google reasoning for tough questions |
| `gemini-flash` | `google/gemini-flash-1-5` | LOW | Speed-optimised — short answers, utility tasks with latency budgets |
| `gemini-long` | `google/gemini-pro-1-5` (128k window) | HIGH | Multi-hundred-page specs, large codebases in one pass |

### xAI (Grok)

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `grok` | `x-ai/grok-2` | STANDARD | Snappy, opinionated answers, decent coding, good cost/speed |
| `grok-lite` | `x-ai/grok-2` (temp 0) | LOW | Micro-tasks: classification, policy checks, small refactors |

### Perplexity (Sonar — search-augmented)

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `sonar-pro` | `perplexity/sonar-pro` | STANDARD | Search + grounding — web results → coherent cited answers. Best default for research. |
| `sonar` | `perplexity/sonar` | LOW | Extraction / compression — distill pages into structured notes, query rewriting |
| `sonar-reasoning` | `perplexity/sonar-reasoning` | HIGH | Web-grounded reasoning — search + think before answering |
| `sonar-reasoning-pro` | `perplexity/sonar-reasoning-pro` | HIGH | Max Sonar — hardest web-grounded reasoning tasks |

> Sonar Router and Sonar Planner are internal Perplexity Computer orchestration models —
> they are NOT the Sonar search API. No OpenRouter equivalent.
> Our approximation: `gpt4o-mini` as task classifier + Commander routing table.

### Code-Specialised

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `codestral` | `mistral/codestral-latest` | STANDARD | Code generation, test writing, config migrations |
| `opus-code` | `anthropic/claude-opus-4` | CRITICAL | Large refactors, subtle bug-hunting, multi-service changes |
| `sonnet-code` | `anthropic/claude-sonnet-4-5` | STANDARD/HIGH | Implement features, everyday coding |
| `gpt5-code` | `openai/gpt-4o` | STANDARD | Cross-stack projects, polyglot repos, cloud infra |

### Image / Vision

| Alias | OpenRouter ID | Tier | Best for |
|---|---|---|---|
| `image-gen` | (DALL-E or Stable Diffusion via OR) | — | UI mocks, illustrations, mockups for Design Lead |
| `vision` | `anthropic/claude-sonnet-4-5` (vision) | STANDARD | Complex diagrams, layouts, design token extraction from images |

### Utility / Glue (tiny, always-on)

These run on every request in the meta-routing layer.
Cost: near-zero per call. Purpose: make the big models usable at scale.

| Alias | Equivalent | Purpose |
|---|---|---|
| `classifier` | `openai/gpt-4o-mini` | Task Classifier — "coding/design/forensic/infra/compound?" |
| `difficulty` | `openai/gpt-4o-mini` | Difficulty Estimator — "LOW/STANDARD/HIGH/CRITICAL?" |
| `tool-selector` | `openai/gpt-4o-mini` | "Model or tool? Browser/shell/DB/LLM?" |
| `summarizer` | `anthropic/claude-haiku-3-5` | Summarizer-Tiny — 1-2 sentence TL;DRs for STATE.md, Aura episodes |
| `formatter` | `openai/gpt-4o-mini` | Format-Transformer — convert raw response to target schema |
| `json-validator` | `openai/gpt-4o-mini` | JSON Validator — fix malformed Lead outcome JSON before Commander parses |
| `chain-optimizer` | task-observer (Aura-backed) | Chain Optimizer — learns from TaskExecution history, prunes steps |

---

## Meta-Routing Layer — Implementation

### Step 1: Task Classifier
```
Model: classifier (gpt4o-mini)
Input: user request text
Output: { domain: "engineering|design|forensic|infra|compound", confidence: 0.0-1.0 }
Cost: ~$0.0001 per call
Fallback: Commander applies priority rules table directly (MODE 1 behavior)
```

### Step 2: Difficulty Estimator
```
Model: difficulty (gpt4o-mini)
Input: user request + domain classification
Output: { tier: "LOW|STANDARD|HIGH|CRITICAL", reasoning: "string" }
Cost: ~$0.0001 per call
Tiers map to model families (see Complexity Tiers table above)
```

### Step 3: Tool Selector (within Lead execution)
```
Model: tool-selector (gpt4o-mini)
Input: subtask description within Lead
Output: { use: "model|browser|shell|db", model_if_llm: "alias" }
Cost: ~$0.0001 per call
Used by: Engineering Lead (model vs postgres tool), Design Lead (model vs dev-browser)
```

### Step 4: JSON Validator (output layer)
```
Model: json-validator (gpt4o-mini)
Input: raw Lead outcome JSON + contract schema
Output: { valid: bool, fixed_json: "string if invalid" }
Cost: ~$0.0001 per call
Runs after every Lead returns. Fixes malformed JSON before Commander parses.
```

### Step 5: Summarizer-Tiny (output layer)
```
Model: summarizer (haiku)
Input: full Lead outcome
Output: { state_md_summary: "1-2 sentences", episode_content: "1 sentence for Aura" }
Cost: ~$0.001 per call
Replaces using sonnet to write STATE.md updates and episode content.
```

---

## Agent Model Routing Table

Commander selects model based on: Task Classifier output + Difficulty Estimator tier.
Model is passed in context package. Escalation trigger is explicit condition.

### @Commander (meta-routing + coordination)

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Task classification | `classifier` | — | — |
| Difficulty estimation | `difficulty` | — | — |
| Standard routing decision | `haiku` | — | — |
| Compound task CoT decomposition | `sonnet` | Novel architecture | `opus` |
| Circuit breaker diagnostic | `sonnet` | — | — |
| STATE.md write | `summarizer` | — | — |

---

### @Design-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Tool selection (model vs dev-browser) | `tool-selector` | — | — |
| Token extraction (vision input) | `vision` (sonnet-vision) | Multi-brand complex | `opus` |
| Atomic/molecular design | `sonnet` | — | — |
| UX quality review | `sonnet` | Accessibility audit | `opus` |
| Frontend assembly | `sonnet-code` | — | — |
| Mockup generation | `image-gen` | — | — |
| E2E test writing | `codestral` | Complex async flows | `sonnet-code` |
| Outcome schema validation | `json-validator` | — | — |
| Outcome summarisation | `summarizer` | — | — |

---

### @Engineering-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Tool selection (model vs postgres/shell) | `tool-selector` | — | — |
| Plan validation | `haiku` | — | — |
| TDD test writing | `codestral` | Complex domain logic | `sonnet-code` |
| GSD plan creation | `sonnet` | — | — |
| GSD execution (tool-heavy) | `sonnet-tools` | Architectural deviation | `opus` |
| Security review | `sonnet` | CRITICAL tier | `opus` |
| Large codebase research | `gemini-long` | — | — |
| Web-augmented research | `sonar-pro` | Needs reasoning + search | `sonar-reasoning-pro` |
| Data verification (postgres) | `haiku` | — | — |
| Outcome schema validation | `json-validator` | — | — |
| Outcome summarisation | `summarizer` | — | — |

---

### @Forensic-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Sentry intake | `haiku` | — | — |
| Failure characterisation | `sonnet` | — | — |
| Root cause tracing | `sonnet` | — | — |
| ACH hypothesis generation | `sonnet` | — | — |
| tri-agent-bug-audit (Neutral Mapper) | `sonnet` | — | — |
| tri-agent-bug-audit (Bug Finder) | `sonnet-tools` | — | — |
| tri-agent-bug-audit (Adversary) | `opus` | — | — |
| tri-agent-bug-audit (Referee) | `opus` | Blast radius > 10 | `opus` + `o3` |
| Episode write content | `summarizer` | — | — |
| Outcome schema validation | `json-validator` | — | — |

---

### @Infrastructure-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Aura health probe | `haiku` | — | — |
| Deployment validation | `haiku` | — | — |
| varlock security check | `haiku` | Secret detected | `sonnet` |
| Improvement queue processing | `haiku` | — | — |
| Pattern promotion write | `summarizer` | — | — |
| Outcome schema validation | `json-validator` | — | — |

---

### @Project-Lead

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Compound decomposition | `sonnet` (planner prompt) | Cross-cutting architecture | `opus` |
| Lead coordination | `haiku` | — | — |
| Overall quality gate validation | `sonnet` | — | — |
| Outcome aggregation schema | `json-validator` | — | — |

---

### @Validator

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| Proposal review + CoT verdict | `sonnet` (critic prompt) | Governance/auth path | `opus` |
| Blast radius Aura query | `haiku` | — | — |
| Adversarial check | `sonnet` | — | — |
| Rejection rationale write | `summarizer` | — | — |

---

### task-observer (background)

| Subtask | Model | Escalation trigger | Escalation model |
|---|---|---|---|
| TaskExecution outcome analysis | `haiku` | — | — |
| ImprovementProposal writing | `sonnet` | Multi-agent impact | `sonnet` |
| Cost/model performance analysis | `classifier` + `difficulty` | — | — |

---

## Aura Integration — Model Tracking

`TaskExecution` node tracks model performance over time:

```cypher
(:TaskExecution {
  ...existing fields...,
  model_used,              // primary model for this execution
  utility_models_used,     // ["classifier", "difficulty", "json-validator"]
  model_cost_usd,          // total cost including utility models
  escalation_triggered,    // bool
  escalation_reason,       // what triggered the escalation
  difficulty_tier          // what Difficulty Estimator classified this as
})
```

`task-observer` reads this data to:
- Track which models produce best `quality_gate_passed` rate per task type
- Track escalation frequency (escalating too often → base model needs upgrade)
- Track utility model accuracy (classifier wrong too often → retrain prompt)
- Propose model policy updates via ImprovementProposal queue (DD-08)

---

## .env Configuration

```env
# OpenRouter (single key covers all models)
OPENROUTER_API_KEY=sk-or-...

# Optional: per-Lead keys with spending caps set in OpenRouter dashboard
# Falls back to OPENROUTER_API_KEY if not set
OPENROUTER_KEY_ENGINEERING=sk-or-...
OPENROUTER_KEY_FORENSIC=sk-or-...
OPENROUTER_KEY_DESIGN=sk-or-...
OPENROUTER_KEY_INFRA=sk-or-...
OPENROUTER_KEY_VALIDATOR=sk-or-...

# Model aliases (swap without touching specs)
MODEL_OPUS=anthropic/claude-opus-4
MODEL_SONNET=anthropic/claude-sonnet-4-5
MODEL_HAIKU=anthropic/claude-haiku-3-5
MODEL_CODESTRAL=mistral/codestral-latest
MODEL_SONAR=perplexity/sonar-pro
MODEL_SONAR_REASONING=perplexity/sonar-reasoning-pro
MODEL_GEMINI_LONG=google/gemini-pro-1-5
MODEL_GPT4O=openai/gpt-4o
MODEL_GPT4O_MINI=openai/gpt-4o-mini
MODEL_O3=openai/o3
```

---

## Models NOT on OpenRouter (internal Perplexity variants)

These exist in Perplexity Computer but have no direct OpenRouter equivalent.
Approximate via prompt engineering:

| Perplexity internal | Our equivalent |
|---|---|
| Sonar Router | `gpt4o-mini` as task classifier (prompt-engineered) |
| Sonar Planner | `sonnet` + planner system prompt (Project Lead) |
| Claude Planner (internal fine-tune) | `opus` + decomposition system prompt (Commander) |
| Claude Critic (internal fine-tune) | `sonnet` + adversarial system prompt (Validator) |
| Chain Optimizer | task-observer (Aura-backed, not LLM-only) |
| Sonar Safety | `haiku` + safety system prompt / varlock skill |

---

## Deferred Decisions

**DD-08: Model performance calibration**
Trigger: 20+ TaskExecutions per Lead type with `model_used` + `quality_gate_passed` tracked.
Evidence: grouped by `model_used` per `task_type` in Aura.
Action: task-observer proposes model policy updates.

**DD-09: Meta-routing layer accuracy calibration**
Question: Is `gpt4o-mini` accurate enough as a task classifier and difficulty estimator?
Trigger: 50+ classifications logged in TaskExecution `utility_models_used`.
Evidence: cases where Commander overrode classifier output (indicates classifier error).
Action: refine classifier system prompt or upgrade to `gpt4o` if error rate > 10%.
