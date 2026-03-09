# Letta Agent Management — Command Reference

All commands run from the project root.
Set `$env:PYTHONUTF8="1"` in PowerShell to avoid encoding errors.

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

> **After `--force`:** always run `populate_agent_memory.py --agent <name>` immediately — re-registration wipes memory blocks.

---

## 2. Populate Memory Blocks
**Script:** `scripts/letta/populate_agent_memory.py`
Patches `persona` + `human` blocks on each agent with real project content. Raises limits to 100k.

| Command | What it does |
|---|---|
| `python scripts/letta/populate_agent_memory.py` | Populate all 10 agents + auto-verify |
| `python scripts/letta/populate_agent_memory.py --dry-run` | Show what would change, no writes |
| `python scripts/letta/populate_agent_memory.py --agent commander` | Populate one agent only |
| `python scripts/letta/populate_agent_memory.py --verify` | Run all 10 SCs, exit 0=GREEN / 1=RED |

### What goes into each block

| Block | Content |
|---|---|
| `persona` | Role identity, authority partition, key partner agent IDs |
| `human` | Project overview + conventions + commands + agent registry |

Watson's `persona` also carries the casebook-summary (calibration state across sessions).

---

## 3. Standard Workflow After a Spec Change

```powershell
$env:PYTHONUTF8="1"

# 1. Edit the spec
#    .letta/agents/<name>.md  (also sync to .claude/.codex/.gemini if wrapper changed)

# 2. Re-register to bake new system prompt into Letta
python scripts/letta/register_agents.py --force --agent <name>

# 3. Repopulate memory (re-registration wipes blocks)
python scripts/letta/populate_agent_memory.py --agent <name>

# 4. Verify
python scripts/letta/populate_agent_memory.py --verify
```

---

## 4. Full Reset (nuclear — all agents)

```powershell
$env:PYTHONUTF8="1"

python scripts/letta/register_agents.py --force
python scripts/letta/populate_agent_memory.py
python scripts/letta/populate_agent_memory.py --verify
```

---

## 5. Registered Agent IDs

| Agent | Letta ID | Model |
|---|---|---|
| commander | `agent-17b34ed8-3b70-486d-b794-b3a9fc2891fe` | letta/auto |
| watson | `agent-3547bcdb-93be-48be-b4c9-5917ec492f8e` | lc-openrouter/anthropic/claude-opus-4 |
| bundle | `agent-80089217-55b3-4526-a1f8-dd33fdf5b15e` | letta/auto |
| engineering-lead | `agent-96ae8a2e-2ff4-431f-8dae-aa775b14e5a5` | letta/auto |
| design-lead | `agent-8ddeb2a5-7b72-45fb-a0d8-b2313e2a5a46` | letta/auto |
| forensic-lead | `agent-22f85d3d-63ea-420f-89a5-522e16024172` | letta/auto |
| infrastructure-lead | `agent-c2ac96eb-7f4c-425d-9219-07eb58eae94a` | letta/auto |
| project-lead | `agent-40f05e64-c48c-4a64-b9aa-835b37f3a12a` | letta/auto |
| task-observer | `agent-68dae0cf-fee2-4315-8baa-c9b2b6789b95` | letta/auto |
| validator | `agent-37edc9bd-7f29-4fad-bcdc-5cd61f9fe444` | lc-openrouter/anthropic/claude-sonnet-4 |
| Pico-Warden | `agent-24c66e02-7099-4027-9d66-24e319a17251` | lc-openrouter/anthropic/claude-haiku-4.5 |
| Analyst (you) | `agent-745c61ec-da1a-4e13-b142-ff28a1fe7b09` | — |

Full registry (auto-updated by scripts): `.letta/agent-registry.json`
Env vars: `LETTA_AGENT_COMMANDER_ID`, `LETTA_AGENT_WATSON_ID`, etc. (in `.env`)

---

## 6. Spec Files

| Agent | Spec | Wrapper (all platforms) |
|---|---|---|
| commander | `docs/agent-system/specs/commander.md` (v2.0) | `.letta/.claude/.codex/.gemini/agents/commander.md` |
| watson | `docs/agent-system/specs/watson.md` (v1.0) | `.letta/.claude/.codex/.gemini/agents/watson.md` |
| bundle | `docs/agent-system/specs/bundle.md` | `.letta/.claude/.codex/.gemini/agents/bundle.md` |
| leads | `docs/agent-system/specs/<lead>.md` | `.letta/.claude/.codex/.gemini/agents/<lead>.md` |

> Canonical spec lives in `docs/`. Platform wrappers in `.letta/.claude/.codex/.gemini/` are thin references — keep them in sync when the spec changes.

---

## 7. Notes

- **`--force` deletes conversation history** on that agent. Use `--agent <name>` to limit blast radius.
- **Watson's casebook** lives in the `persona` memory block. Re-populating resets it to cold-start. Watson's actual long-term calibration should eventually move to Aura (planned).
- **LETTA_API_KEY** must be set in `.env`. Script will exit 1 if missing.
- **Embedding model:** `letta/letta-free` (hardcoded in register_agents.py — confirmed working).
- **Block limit:** 100,000 chars per block. Sufficient for all current content.
