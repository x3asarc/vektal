---
name: gsd:compound-execute
description: Run discuss, plan, execute, and verify with Compound Engineering OS gates in one command
argument-hint: "<phase-number> [--plan <NN>] [--task <phase.n-slug>] [--skip-discuss] [--skip-verify]"
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
Execute one end-to-end workflow that combines GSD phase execution with Compound Engineering OS governance gates.

This command bootstraps gate artifacts, runs discuss/plan/execute/verify, validates governance evidence, and updates canonical planning state.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/compound-execute.md
</execution_context>

<context>
Arguments: $ARGUMENTS

@solutionsos/compound-engineering-os-policy.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/config.json
</context>

<process>
Execute the compound workflow from @./.claude/get-shit-done/workflows/compound-execute.md end-to-end.
Preserve governance gates, phase workflow gates, and canonical state update discipline.
</process>
