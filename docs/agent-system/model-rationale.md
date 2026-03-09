# Vektal Agent Model Assignments — OpenRouter Source of Truth
**Version:** 3.0 | **Date:** 2026-03-09
**Supersedes:** v2.0 (Letta-inference assumption — incorrect)

---

## Architectural Principle

**Letta = memory store only. Never inference.**

| Layer | Tool | Notes |
|---|---|---|
| Inference | OpenRouter direct (`OPENROUTER_API_KEY`) | All models go here |
| Memory / state | Letta Cloud | Agent IDs, memory blocks, `send_message` for Pico-Warden only |
| Execution | CLI tools (Claude Code, Gemini CLI, Codex) | Each CLI configured to use OpenRouter as backend |

Every agent is invoked by the user from a CLI session. The CLI calls OpenRouter directly with the
agent's spec (`.claude/agents/`, `.gemini/agents/`, `.codex/agents/`) as the system prompt.
Letta agent IDs exist for inter-agent messaging (Pico-Warden escalation) and memory persistence —
never as an inference endpoint.

**Letta model field** in `agent-registry.json` and `register_agents.py` is metadata only.
It documents intent. It does not route inference.

---

## Agent Model Assignments

### Confirmed available on OpenRouter (verified 2026-03-09)

| Agent | OpenRouter Model ID | Rationale |
|---|---|---|
| **Watson** | `anthropic/claude-opus-4-6` | Best-in-class multi-step forensic reasoning. Only Anthropic model in stack — deliberate monoculture break for adversarial review. |
| **Commander** | `x-ai/grok-3` | 131K context, flagship xAI model. Agentic tool calling, strategic routing. |
| **Forensic Lead** | `deepseek/deepseek-v3.2` | Distinct training lineage from Anthropic — different reasoning failure modes. Critical for independent blast-radius analysis. |
| **Design Lead** | `moonshotai/kimi-k2.5` | Native multimodal. 262K context. Can process Shopify theme screenshots directly. |
| **task-observer** | `google/gemini-2.5-flash-lite` | Token-efficient telemetry. Pattern detection over large TaskExecution sets. |
| **Lestrade** | `deepseek/deepseek-v3.2` | One-shot arbitrator — same as Forensic Lead. Non-Anthropic, non-xAI lineage breaks Commander/Watson deadlock. |

### Confirmed available — pragmatic assignments

| Agent | OpenRouter Model ID | Rationale |
|---|---|---|
| **Engineering Lead** | `openai/gpt-4o` | Strong code quality, tool calling, deterministic at temp=0.1. Upgrade to `openai/o3` when available. |
| **Bundle** | `google/gemini-2.5-flash` | Near-Pro reasoning at flash speed. JSON gating doesn't need frontier models. |
| **Infrastructure Lead** | `z-ai/glm-4.6` | 203K context. Multi-tenant isolation awareness. GLM-5 when available. |
| **Project Lead** | `google/gemini-2.5-flash` | Long-horizon stability. Upgrade to `google/gemini-2.5-pro` when confirmed available. |
| **Validator** | `openai/gpt-4o-mini` | "Different flavor" critique. Upgrade to `openai/gpt-5-mini` when available. |

### Aspirational (not yet on OpenRouter as of 2026-03-09)

| Fictional ID | Intended for | Notes |
|---|---|---|
| `x-ai/grok-4.1-fast` | Commander | Use `x-ai/grok-3` until available |
| `openai/gpt-5.3-codex` | Engineering Lead | Use `openai/gpt-4o` until available |
| `z-ai/glm-5` | Infrastructure Lead | Use `z-ai/glm-4.6` until available |
| `google/gemini-3-flash-preview` | Bundle | Use `google/gemini-2.5-flash` |
| `google/gemini-3.1-pro-preview` | Project Lead | Use `google/gemini-2.5-flash` |
| `openai/gpt-5-mini` | Validator | Use `openai/gpt-4o-mini` |

---

## Research Engine

For Commander's deep-research subtasks (not Letta — direct OpenRouter API call):

| Use case | Model | OpenRouter ID |
|---|---|---|
| High urgency, cited, real-time | Perplexity Sonar Deep Research | `perplexity/sonar-deep-research` |
| Low urgency, exhaustive, cheap | Tongyi DeepResearch | `alibaba/tongyi-deepresearch-30b-a3b` |

```python
def research_router(query: str, urgency: str) -> str:
    model = (
        "perplexity/sonar-deep-research"
        if urgency == "high"
        else "alibaba/tongyi-deepresearch-30b-a3b"
    )
    return call_openrouter(model, query)
```

---

## Configuring CLIs to use OpenRouter

### Claude Code (Letta Code)
All Claude models run through Anthropic natively. For non-Claude agents (Commander/Watson
when invoked from a Codex/Gemini session), point the CLI at OpenRouter:

```bash
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=<your key>
```

### Codex
Set `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and `OPENAI_API_KEY=$OPENROUTER_API_KEY`.
Then use any OpenRouter model ID as the `--model` flag.

### Gemini CLI
Use `GOOGLE_GENAI_USE_VERTEXAI=false` and point at OpenRouter with an OpenAI-compatible adapter.

---

## Diversity rationale

No two agents in the same tier share the same provider family:

| Tier | Agent | Provider |
|---|---|---|
| Forensic | Watson | Anthropic |
| Forensic | Lestrade (arbitrator) | DeepSeek |
| Command | Commander | xAI |
| Command | Project Lead | Google |
| Execution | Engineering Lead | OpenAI |
| Execution | Design Lead | MoonshotAI |
| Execution | Forensic Lead | DeepSeek |
| Execution | Infrastructure Lead | Z.ai |
| Utility | Bundle | Google |
| Utility | task-observer | Google |
| Utility | Validator | OpenAI |

Watson is the **only** Anthropic model in the stack — by design. Forensic adversarial review
must come from a different reasoning lineage than the CLI running the session.

---

*This file is the single source of truth for model assignments.*
*CLI config: `.env` — `OPENROUTER_API_KEY`*
*Agent specs: `.claude/agents/`, `.gemini/agents/`, `.codex/agents/`*
*Letta memory: `.letta/agent-registry.json` (model field = label only)*
