# Model Selection Policy — Vektal Agent System
**Version:** 1.1 | **Date:** 2026-03-08
**Broker:** OpenRouter (via Letta `lc-openrouter/` prefix or `.env` `OPENROUTER_API_KEY`)
**Reference:** Perplexity Computer architecture (19-model orchestration pattern)
**Key insight:** Most models in a well-designed system are tiny glue/utility models.
Frontier models are called rarely. Utility models run on every request.

---

## Architectural Pattern — Meta-Routing Layer

### Primary: openrouter/auto

OpenRouter provides a built-in meta-model that does everything our manual
classifier + difficulty estimator was going to do — trained on millions of
requests, free routing overhead, returns which model was used.

```
ID:      openrouter/auto
Context: 2,000,000 tokens
Routing: $0 — you pay at the routed model's rate only
Returns: model attribute in response → write to TaskExecution.model_used
```

**Model pool (as of 2026-03-08):**
```
anthropic/claude-haiku-4.5       anthropic/claude-sonnet-4.5
anthropic/claude-sonnet-4.6      anthropic/claude-opus-4.6
openai/gpt-5                     openai/gpt-5.1
openai/gpt-5.2                   openai/gpt-5.2-pro
openai/gpt-5-mini                openai/gpt-5-nano
openai/gpt-oss-120b              google/gemini-2.5-flash-lite
google/gemini-3-flash-preview    google/gemini-3-pro-preview
google/gemini-3.1-pro-preview    deepseek/deepseek-r1
mistralai/codestral-2508         mistralai/mistral-large
mistralai/mistral-medium-3.1     mistralai/mistral-small-3.2-24b-instruct-2506
meta-llama/llama-3.3-70b-instruct perplexity/sonar
moonshotai/kimi-k2-thinking      moonshotai/kimi-k2.5
qwen/qwen3-235b-a22b             minimax/minimax-m2.5
x-ai/grok-3                      x-ai/grok-3-mini
x-ai/grok-4                      z-ai/glm-5
```

This pool is maintained and updated by OpenRouter automatically.
The model attribute returned is written to `TaskExecution.model_used`
so we get full model tracking without building a classifier.

### The Hybrid Rule

```
DEFAULT:  openrouter/auto        ← most tasks, let OpenRouter decide
OVERRIDE: explicit model         ← only where a quality floor is non-negotiable
```

**Quality floors — explicit model required:**

| Agent | Subtask | Minimum | Reason |
|---|---|---|---|
| @Validator | Proposal review + CoT | `sonnet` | Can't risk haiku — bad approvals have downstream consequences |
| @Forensic-Lead | tri-audit adversary role | `opus` | Adversarial reasoning quality is the whole point |
| @Forensic-Lead | tri-audit referee | `opus` | Final verdict must survive max scrutiny |
| @Commander | Compound task CoT decomposition | `sonnet` | Decomposition quality determines all downstream routing |
| @Engineering-Lead | Security review (CRITICAL tier) | `sonnet` | Security misses are catastrophic |
| @Validator | Governance/auth proposals | `opus` | Highest stakes approval in the system |

Everything else: `openrouter/auto`.

### Aura Integration

The `model` attribute from every OpenRouter response is written to Aura:
```cypher
(:TaskExecution {
  model_used,          // what auto actually routed to
  model_requested,     // "openrouter/auto" or explicit model
  escalation_triggered // true if explicit override was used
})
```

task-observer reads this to understand routing patterns over time.
If auto consistently routes to expensive models for a task type →
propose explicit model cap via ImprovementProposal queue.

### Updated Flow

```
Request arrives at Commander
  ↓
[COMMANDER UNDERSTAND — uses openrouter/auto]
  → Routes to optimal model for understanding + domain classification
  → model attribute logged
  ↓
[COMMANDER ROUTES to Lead with context package]
  model: "openrouter/auto"  ← default
  OR explicit model if quality floor applies
  ↓
[LEAD EXECUTES — openrouter/auto per subtask unless quality floor]
  ↓
[OUTPUT LAYER — still needed, these are cheap mechanical tasks]
  JSON Validator (gpt4o-mini) → schema enforcement
  Summarizer-Tiny (haiku)     → STATE.md + Aura episode compression
```

Note: JSON Validator and Summarizer-Tiny remain explicit — auto routing
is overkill for pure format-fixing and compression tasks.

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
| `classifier` | `google/gemini-3.1-flash-lite` | Task Classifier — "coding/design/forensic/infra/compound?" (2026: lower latency, better native intent detection) |
| `difficulty` | `google/gemini-3.1-flash-lite` | Difficulty Estimator — "LOW/STANDARD/HIGH/CRITICAL?" (2026: same rationale as classifier) |
| `tool-selector` | `google/gemini-3.1-flash-lite` | "Model or tool? Browser/shell/DB/LLM?" (2026: within Lead execution) |
| `summarizer` | `openai/gpt-5-nano` | Summarizer-Tiny — 1-2 sentence TL;DRs for STATE.md, Aura episodes (2026: haiku-4-5 is Reasoning-Light, overkill for compression) |
| `formatter` | `google/gemini-3.1-flash-lite` | Format-Transformer — convert raw response to target schema |
| `json-validator` | `mistralai/mistral-small-3.2` | JSON Validator — fix malformed Lead outcome JSON (2026: higher schema strictness for complex Shopify GraphQL payloads) |
| `chain-optimizer` | task-observer (Aura-backed) | Chain Optimizer — learns from TaskExecution history, prunes steps |

---

## Meta-Routing Layer — Implementation

### Step 1: Task Classifier
```
Model: classifier (google/gemini-3.1-flash-lite)       ← 2026 recommendation
Input: user request text
Output: { domain: "engineering|design|forensic|infra|compound", confidence: 0.0-1.0 }
Cost: ~$0.0001 per call
Fallback: Commander applies priority rules table directly (MODE 1 behavior)
```

### Step 2: Difficulty Estimator
```
Model: difficulty (google/gemini-3.1-flash-lite)       ← 2026 recommendation
Input: user request + domain classification
Output: { tier: "LOW|STANDARD|HIGH|CRITICAL", reasoning: "string" }
Cost: ~$0.0001 per call
Tiers map to model families (see Complexity Tiers table above)
```

### Step 3: Tool Selector (within Lead execution)
```
Model: tool-selector (google/gemini-3.1-flash-lite)    ← 2026 recommendation
Input: subtask description within Lead
Output: { use: "model|browser|shell|db", model_if_llm: "alias" }
Cost: ~$0.0001 per call
Used by: Engineering Lead (model vs postgres tool), Design Lead (model vs dev-browser)
```

### Step 4: JSON Validator (output layer)
```
Model: json-validator (mistralai/mistral-small-3.2)    ← 2026 recommendation
Input: raw Lead outcome JSON + contract schema
Output: { valid: bool, fixed_json: "string if invalid" }
Cost: ~$0.0001 per call
Runs after every Lead returns. Fixes malformed JSON before Commander parses.
Higher schema strictness for complex Shopify GraphQL payloads.
```

### Step 5: Summarizer-Tiny (output layer)
```
Model: summarizer (openai/gpt-5-nano)                  ← 2026 recommendation
Input: full Lead outcome
Output: { state_md_summary: "1-2 sentences", episode_content: "1 sentence for Aura" }
Cost: ~$0.001 per call
haiku-4-5 is now Reasoning-Light — overkill for compression tasks.
```

---

## Agent Model Routing Table

> **v2.0 (2026-03-09):** Primary agent models now defined in `docs/agent-system/model-rationale.md`
> (Forensic Mapping v2.0 — Deep Reasoning Edition). The table below documents subtask-level
> quality floors which remain valid. Primary model column reflects model-rationale.md assignments.

### @Commander — `lc-openrouter/x-ai/grok-4.1-fast`

| Subtask | Model | Note |
|---|---|---|
| All standard routing + UNDERSTAND | primary (grok-4.1-fast) | Default |
| Compound task CoT decomposition | primary minimum | 2M context handles full blast radius |
| Circuit breaker diagnostic | primary minimum | |
| STATE.md write | `summarizer` (haiku) | Utility — compression only |

### @Design-Lead

| Subtask | Model | Note |
|---|---|---|
| All design + assembly + UX review | `auto` | Default |
| Mockup generation | `image-gen` explicit | Requires image generation model — auto won't select it |
| E2E test writing | `auto` | Default (auto routes to codestral-class) |
| Outcome schema validation | `json-validator` (gpt4o-mini) | Utility |
| Outcome summarisation | `summarizer` (haiku) | Utility |

### @Engineering-Lead

| Subtask | Model | Note |
|---|---|---|
| All plan + code + GSD execution | `auto` | Default |
| Security review (CRITICAL tier) | `sonnet` floor | QUALITY FLOOR — miss = production vulnerability |
| GSD execution (architectural deviation) | `opus` floor | QUALITY FLOOR — Rule 4 architectural decision |
| Web-augmented research | `sonar-pro` explicit | Requires search-augmented model — auto won't select Sonar |
| Web-grounded reasoning | `sonar-reasoning-pro` explicit | As above |
| Outcome schema validation | `json-validator` (gpt4o-mini) | Utility |
| Outcome summarisation | `summarizer` (haiku) | Utility |

### @Forensic-Lead

| Subtask | Model | Note |
|---|---|---|
| Intake + characterisation + trace + ACH | `auto` | Default |
| tri-audit Neutral Mapper | `auto` | Default |
| tri-audit Bug Finder | `auto` | Default |
| tri-audit Adversary | `opus` floor | QUALITY FLOOR — adversarial quality is the feature |
| tri-audit Referee | `opus` floor | QUALITY FLOOR — final verdict, max scrutiny |
| Episode write content | `summarizer` (haiku) | Utility |
| Outcome schema validation | `json-validator` (gpt4o-mini) | Utility |

### @Infrastructure-Lead

| Subtask | Model | Note |
|---|---|---|
| All health + sync + queue tasks | `auto` | Default |
| varlock secret detection | `sonnet` floor | QUALITY FLOOR — secret miss = security incident |
| Pattern promotion write | `summarizer` (haiku) | Utility |
| Outcome schema validation | `json-validator` (gpt4o-mini) | Utility |

### @Project-Lead

| Subtask | Model | Note |
|---|---|---|
| All decomposition + coordination | `auto` | Default |
| Compound CoT (cross-cutting architecture) | `sonnet` floor | QUALITY FLOOR — decomposition quality |
| Outcome aggregation validation | `json-validator` (gpt4o-mini) | Utility |

### @Validator

| Subtask | Model | Note |
|---|---|---|
| Standard proposal review + CoT | `sonnet` floor | QUALITY FLOOR — bad approval has downstream consequences |
| Governance/auth proposals | `opus` floor | QUALITY FLOOR — highest stakes in the system |
| Rejection rationale write | `summarizer` (haiku) | Utility |

### task-observer (background — invoked by Infrastructure Lead)

| Subtask | Model | Note |
|---|---|---|
| TaskExecution analysis + proposal writing | `auto` | Default |
| ImprovementProposal content | `auto` | Default |

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
# OpenRouter — single key covers all models including auto
OPENROUTER_API_KEY=sk-or-...

# Optional: per-Lead keys with spending caps set in OpenRouter dashboard
# Falls back to OPENROUTER_API_KEY if not set
OPENROUTER_KEY_ENGINEERING=sk-or-...
OPENROUTER_KEY_FORENSIC=sk-or-...
OPENROUTER_KEY_DESIGN=sk-or-...
OPENROUTER_KEY_INFRA=sk-or-...
OPENROUTER_KEY_VALIDATOR=sk-or-...

# Default model — auto routing for most tasks
MODEL_DEFAULT=openrouter/auto

# Quality floor overrides — explicit models where auto cannot be trusted
MODEL_FLOOR_SONNET=anthropic/claude-sonnet-4-5   # minimum for Validator, security review
MODEL_FLOOR_OPUS=anthropic/claude-opus-4-6        # minimum for Forensic adversary/referee, governance

# Utility/glue models — explicit (auto is overkill for these)
MODEL_UTILITY_VALIDATOR=openai/gpt-4o-mini        # JSON schema enforcement
MODEL_UTILITY_SUMMARIZER=anthropic/claude-haiku-4-5 # STATE.md + episode compression
MODEL_UTILITY_SONAR=perplexity/sonar-pro           # web-grounded research
MODEL_UTILITY_SONAR_REASONING=perplexity/sonar-reasoning-pro
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

## Research Engine (v2026.3)

Two models for research subtasks — called via direct OpenRouter API within execution,
not as Letta base models. See `.commands/agents.md` for the full router pattern.

| Model | OpenRouter ID | Use when | Cost |
|---|---|---|---|
| Tongyi DeepResearch | `alibaba/tongyi-deepresearch-30b-a3b` | Exhaustive: 100 sequential tool calls, background agents, long-horizon reports | $0.02–0.08 / 10 min |
| Sonar Deep Research | `perplexity/sonar-deep-research` | Fast: real-time web, citations, unblocking a sprint | $2/M + $5/1k searches |

**Rule:** `urgency="high"` → Sonar. `urgency="low"` → Tongyi.

Agents with research subtasks: Engineering Lead (web research), Forensic Lead (evidence sourcing).

---

## Deferred Decisions

**DD-08: Model performance calibration**
Trigger: 20+ TaskExecutions per Lead type with `model_used` + `quality_gate_passed` tracked.
Evidence: grouped by `model_used` per `task_type` in Aura.
Action: task-observer proposes model policy updates.

**DD-09: Auto routing cost control**
Question: Is `openrouter/auto` routing to expensive models more than necessary?
Trigger: 50+ TaskExecutions with `model_requested = "openrouter/auto"` in Aura.
Evidence: distribution of `model_used` values — are expensive models being called for simple tasks?
Action: if high-cost models appear > 20% of time on LOW-tier tasks → add explicit model cap
for those task types via ImprovementProposal queue.
