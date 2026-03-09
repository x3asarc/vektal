# Letta Agent Management — Command Reference

All commands run from the project root.
Set `$env:PYTHONUTF8="1"` in PowerShell to avoid encoding errors.

Model spec: `docs/agent-system/model-rationale.md`
Full registry: `.letta/agent-registry.json`

---

## 1. Register Agents
**Script:** `scripts/letta/register_agents.py`
Reads `.letta/agents/*.md`, creates Letta agents via API, writes IDs to `.letta/agent-registry.json` and `.env`.

| Command | What it does |
|---|---|
| `python scripts/letta/register_agents.py` | Register all 10 core agents (skips existing) |
| `python scripts/letta/register_agents.py --force` | Delete + recreate all agents ⚠️ wipes conversation history |
| `python scripts/letta/register_agents.py --force --agent commander` | Recreate one agent only |
| `python scripts/letta/register_agents.py --all` | Register core + all GSD utility agents |
| `python scripts/letta/register_agents.py --list` | Show current registry (IDs + models) |

> **After `--force`:** always run `populate_agent_memory.py --agent <name>` immediately.

---

## 2. Populate Memory Blocks
**Script:** `scripts/letta/populate_agent_memory.py`
Patches `persona` + `human` blocks on each agent. Raises limits to 100k.

| Command | What it does |
|---|---|
| `python scripts/letta/populate_agent_memory.py` | Populate all 10 agents + auto-verify |
| `python scripts/letta/populate_agent_memory.py --dry-run` | Show what would change, no writes |
| `python scripts/letta/populate_agent_memory.py --agent commander` | Populate one agent only |
| `python scripts/letta/populate_agent_memory.py --verify` | Run all 10 SCs, exit 0=GREEN / 1=RED |

---

## 3. Standard Workflow After a Spec Change

```powershell
$env:PYTHONUTF8="1"

# 1. Edit the spec: .letta/agents/<name>.md
#    Sync to other platforms if wrapper changed:
Copy-Item .letta\agents\commander.md .claude\agents\commander.md
Copy-Item .letta\agents\commander.md .codex\agents\commander.md
Copy-Item .letta\agents\commander.md .gemini\agents\commander.md

# 2. Re-register to bake new system prompt into Letta
python scripts/letta/register_agents.py --force --agent <name>

# 3. Repopulate memory (re-registration wipes blocks)
python scripts/letta/populate_agent_memory.py --agent <name>

# 4. Verify
python scripts/letta/populate_agent_memory.py --verify
```

---

## 4. Full Reset (all agents)

```powershell
$env:PYTHONUTF8="1"
python scripts/letta/register_agents.py --force
python scripts/letta/populate_agent_memory.py
python scripts/letta/populate_agent_memory.py --verify
```

---

## 5. Registered Agent IDs + Models
**Source:** `docs/agent-system/model-rationale.md` — Forensic Mapping v2.0

### High Court (Forensic Reasoning)
| Agent | ID | Model |
|---|---|---|
| watson | `agent-9c3bec2a-cd72-4fe3-bc23-da9acc4cd1de` | `claude-opus-4.6` — multi-step debugging, state persistence |

### Command Tier (Strategic Orchestration)
| Agent | ID | Model |
|---|---|---|
| commander | `agent-d2e3b583-5d02-4e24-98d9-98930db87cea` | `grok-4.1-fast` — 2M+ context, agentic tool calling |
| project-lead | `agent-fa0f01c4-42aa-488c-b79c-085bf4ff350a` | `gemini-3.1-pro-preview` — long-horizon stability |

### Lead Tier (Production Execution)
| Agent | ID | Model |
|---|---|---|
| engineering-lead | `agent-c3599131-49c0-4771-96fb-45ec631a0dc2` | `gpt-5.3-codex` — Terminal-Bench 2.0, CLI/SSH |
| design-lead | `agent-4ec22ba0-5825-4ad0-a738-017b13165c5d` | `kimi-k2.5` — native multimodal, sees Shopify layouts |
| forensic-lead | `agent-5171ac29-a2eb-4eac-ace8-85e55a666e33` | `deepseek-v3.2` — distinct lineage, tie-breaker reasoning |
| infrastructure-lead | `agent-2296fd7a-47a9-4849-9771-36d5f4ae2e48` | `glm-5` — autonomous execution, multi-tenant isolation |

### Guardian Tier (Validation & Logistics)
| Agent | ID | Model |
|---|---|---|
| bundle | `agent-526568af-2163-490d-bcf0-f9871b8dd64f` | `gemini-3-flash-preview` — JSON gating, near-Pro at Flash speed |
| task-observer | `agent-552af620-4c9b-46d3-9855-14ae034972fe` | `gemini-2.5-flash-lite` — $0.10/M telemetry |
| validator | `agent-139a6dce-0a00-44a0-a8b6-cac02686ffe9` | `gpt-5-mini` — different critique flavour |

### Sidecars (not managed by register_agents.py)
| Agent | ID | Model |
|---|---|---|
| Pico-Warden | `agent-24c66e02-7099-4027-9d66-24e319a17251` | `claude-haiku-4.5` |
| Analyst (you) | `agent-745c61ec-da1a-4e13-b142-ff28a1fe7b09` | — |

---

## 6. Research Engine

Sonar and Tongyi are **not** Letta base models — they're called via direct OpenRouter API
within agent execution for research subtasks. Use this router pattern:

```python
import requests, os

def research_router(query: str, urgency: str = "low") -> str:
    """
    urgency="high"  -> Sonar Deep Research (fast, cited, real-time web)
    urgency="low"   -> Tongyi DeepResearch (exhaustive, 100-step agentic loop, cheap)
    """
    model = (
        "perplexity/sonar-deep-research"          # $2/M + $5/1k searches, ~6-10s
        if urgency == "high" else
        "alibaba/tongyi-deepresearch-30b-a3b"     # $0.02-0.08/10min, 100 tool calls
    )
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={"model": model, "messages": [{"role": "user", "content": query}]},
    )
    return r.json()["choices"][0]["message"]["content"]
```

### When to use which

| Scenario | Model | Why |
|---|---|---|
| Shopify API endpoint changed today? | Sonar | Real-time web index, citations |
| Pricing/SKUs across 50+ competitor sites | Tongyi | 100 sequential tool calls, exhaustive |
| Find exact library version for a fix | Sonar | Fast, verifiable link |
| 3 years of Neo4j forum deadlock posts | Tongyi | Long-horizon, cost-efficient |
| Unblocking a sprint (human waiting) | Sonar | ~6-10s time-to-first-answer |
| Background deep-dive report | Tongyi | Autonomous, fractional cost |

### Perplexity model tier reference

| Model | OpenRouter ID | Cost | Best for |
|---|---|---|---|
| Sonar | `perplexity/sonar` | $1/M | Quick Q&A, citations |
| Sonar Pro | `perplexity/sonar-pro` | $3/M + $18/1k req | Multi-step enterprise queries |
| Sonar Pro Search | `perplexity/sonar-pro-search` | $3/M + $18/1k req | Agentic full research workflows |
| Sonar Deep Research | `perplexity/sonar-deep-research` | $2/M + $5/1k searches | Citation-heavy forensic reports |
| Sonar Reasoning Pro | `perplexity/sonar-reasoning-pro` | $2/M | DeepSeek R1 + web grounding |

---

## 7. Spec Files

| Agent | Canonical spec | Letta platform wrapper |
|---|---|---|
| commander | `docs/agent-system/specs/commander.md` (v2.0) | `.letta/.claude/.codex/.gemini/agents/commander.md` |
| watson | `docs/agent-system/specs/watson.md` (v1.0) | `.letta/.claude/.codex/.gemini/agents/watson.md` |
| bundle | `docs/agent-system/specs/bundle.md` | `.letta/.claude/.codex/.gemini/agents/bundle.md` |
| leads | `docs/agent-system/specs/<lead>.md` | `.letta/.claude/.codex/.gemini/agents/<lead>.md` |

---

## 8. Notes

- **`--force` deletes conversation history.** Use `--agent <name>` to limit blast radius.
- **Watson's casebook** lives in the `persona` memory block. Re-populating resets it to cold-start. Long-term calibration moves to Aura eventually.
- **Lestrade** is not a registered Letta agent — it's a one-shot `o4-mini` API call from Commander's adjudication flow.
- **LETTA_API_KEY** must be in `.env`. `OPENROUTER_API_KEY` needed for research engine calls.
- **Embedding model:** `letta/letta-free` (hardcoded in register_agents.py).
- **Block limit:** 100,000 chars per block.
