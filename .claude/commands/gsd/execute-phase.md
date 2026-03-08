---
name: gsd:execute-phase
description: Execute all plans in a phase with wave-based parallelization
argument-hint: "<phase-number> [--gaps-only]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
  - TodoWrite
  - AskUserQuestion
---
<objective>
Execute all plans in a phase using wave-based parallel execution.

Orchestrator stays lean: discover plans, analyze dependencies, group into waves, spawn subagents, collect results. Each subagent loads the full execute-plan context and handles its own plan.

Context budget: ~15% orchestrator, 100% fresh per subagent.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/execute-phase.md
@./.claude/get-shit-done/references/ui-brand.md
</execution_context>

<context>
Phase: $ARGUMENTS

**Flags:**
- `--gaps-only` — Execute only gap closure plans (plans with `gap_closure: true` in frontmatter). Use after verify-work creates fix plans.

@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<process>
Preflight routing before execution:
1. If CONTEXT.md is missing for the phase, trigger discuss-phase question flow first and write CONTEXT.md.
2. If PLAN.md files are missing, trigger plan-phase next (which includes context gate + verification loop).
3. Run mandatory Plan Verification Gate (gsd-plan-checker) and continue only on pass.
4. If Plan Verification Gate fails, stop and route to:
   - Codex: `/prompts:gsd-plan-phase <phase>`
   - Claude: `/gsd:plan-phase <phase>`
   (or gaps flow).
5. Only then execute this workflow.

Preserve all workflow gates (wave execution, checkpoint handling, verification, state updates, routing).
</process>
</phase-number>