---
name: invoke-agent
description: >
  Spawn any agent from .letta/agents/ (Commander, Leads, GSD agents, etc.) as a Letta subagent.
  Use this whenever the user asks to run Commander, a Lead, or any named agent. Letta's spawn
  mechanism automatically shows the user a high-level overview before execution — this is the
  preferred way to run agents in this project, superior to direct @agent invocation in Claude Code.
triggers:
  - "run commander"
  - "invoke"
  - "use the .* agent"
  - "spawn .* lead"
  - "run engineering lead"
  - "run forensic"
  - "run gsd"
  - "ask commander"
---

# invoke-agent

## Purpose

Letta's Task spawning gives users an automatic high-level overview before any agent executes.
This skill makes it trivial to invoke ANY agent from `.letta/agents/` as a Letta subagent.

## Available Agents

### Commander System
| Agent | File | Use When |
|---|---|---|
| `commander` | `.letta/agents/commander.md` | Any non-trivial task — routes to the right Lead |
| `bundle` | `.letta/agents/bundle.md` | Project configuration + team setup for compound tasks |
| `engineering-lead` | `.letta/agents/engineering-lead.md` | Code implementation, tests, bug fixes |
| `design-lead` | `.letta/agents/design-lead.md` | UI/UX, frontend components, visual design |
| `forensic-lead` | `.letta/agents/forensic-lead.md` | Bug investigation, blast radius, root cause |
| `infrastructure-lead` | `.letta/agents/infrastructure-lead.md` | Docker, CI/CD, deployment, ops |
| `project-lead` | `.letta/agents/project-lead.md` | Compound multi-phase tasks |
| `validator` | `.letta/agents/validator.md` | Pre-merge quality gate |
| `task-observer` | `.letta/agents/task-observer.md` | Background improvement + lesson inference |

### GSD Agents
| Agent | File | Use When |
|---|---|---|
| `gsd-executor` | `.letta/agents/gsd-executor.md` | Execute a PLAN.md atomically |
| `gsd-planner` | `.letta/agents/gsd-planner.md` | Create a PLAN.md for a phase |
| `gsd-debugger` | `.letta/agents/gsd-debugger.md` | Debug a specific bug |
| `gsd-verifier` | `.letta/agents/gsd-verifier.md` | Verify a completed phase |
| `gsd-codebase-mapper` | `.letta/agents/gsd-codebase-mapper.md` | Map codebase structure |

## How to Invoke

Use the Task tool with the agent's content as protocol:

```python
# Example: Invoke Commander
Task(
  subagent_type="general-purpose",
  description="Commander: route task",
  prompt=f"""
Read `.letta/agents/commander.md` completely — that is your operating protocol.
Then execute the following task as Commander:

{user_task}
""",
  model="claude-sonnet-4-5"  # or openrouter/auto
)
```

## Rules

1. **Declare scope tier first** — ALWAYS state the tier + budget before spawning: `[SCOPE: RESEARCH | Budget: 2 Leads × 30 steps | ~10 min]`
2. **Always read the agent .md file first** — the prompt must instruct the subagent to read its own spec
3. **Commander for routing** — if unsure which Lead to use, invoke Commander and let it decide
4. **Aura before file reads** — Commander must run Aura P-LOAD (Part III) before any Lead is spawned. Leads use Aura for discovery, not grep sweeps.
5. **Model selection** — follow `docs/agent-system/model-policy.md`:
   - Default: `openrouter/auto`
   - Validator, security tasks: `claude-sonnet-4-5` minimum
   - Forensic adversary/referee: `claude-opus-4-5` minimum
6. **Letta spawn advantage** — the Task tool shows a high-level overview to the user automatically. This is intentional — don't suppress it.
7. **Pass STATE.md context** — always include current phase context from `.planning/STATE.md`
8. **Hard stop at budget** — if a Lead returns `[BUDGET EXCEEDED]`, do not re-spawn. Return partial output to human and ask for approval to continue.

## Scope Tiers (from Commander Part XI)

| Tier | Max Leads | Steps/Lead | Wall time |
|---|---|---|---|
| NANO | 1 | 10 | 2 min |
| MICRO | 1 | 20 | 5 min |
| STANDARD | 2 | 30 | 10 min |
| COMPOUND | 3 | 40 | 20 min |
| RESEARCH | 2 (read-only) | 30 | 10 min |

## Quick Invocation Template

For any user request, determine the right agent and invoke:

```
"Run the [AGENT_NAME] agent on this task: [TASK_DESCRIPTION]"

→ Task(
    subagent_type="general-purpose",
    description="[AGENT_NAME]: [3-word summary]",
    prompt="Read `.letta/agents/[agent-name].md` as your operating protocol. [FULL_TASK]"
  )
```
