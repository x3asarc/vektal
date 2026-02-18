---
name: gsd:plan-phase
description: Create detailed execution plan for a phase (PLAN.md) with verification loop
argument-hint: "[phase] [--research] [--skip-research] [--gaps] [--skip-verify]"
agent: gsd-planner
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - Task
  - WebFetch
  - mcp__context7__*
---
<objective>
Create executable phase prompts (PLAN.md files) for a roadmap phase with integrated research and verification.

**Default flow:** Research (if needed) → Plan → Verify → Done

**Orchestrator role:** Parse arguments, validate phase, research domain (unless skipped), spawn gsd-planner, verify with gsd-plan-checker, iterate until pass or max iterations, present results.
</objective>

<execution_context>
@./.claude/get-shit-done/workflows/plan-phase.md
@./.claude/get-shit-done/references/ui-brand.md
</execution_context>

<context>
Phase number: $ARGUMENTS (optional — auto-detects next unplanned phase if omitted)

**Flags:**
- `--research` — Force re-research even if RESEARCH.md exists
- `--skip-research` — Skip research, go straight to planning
- `--gaps` — Gap closure mode (reads VERIFICATION.md, skips research)
- `--skip-verify` — Skip verification loop

Normalize phase input in step 2 before any directory lookups.
</context>

<process>
Execute the plan-phase workflow from @./.claude/get-shit-done/workflows/plan-phase.md end-to-end.

**Mandatory preflight:** if phase CONTEXT.md does not exist, auto-run the discuss-phase question flow first (big context window), create CONTEXT.md, then continue planning.
**Mandatory Q&A evidence gate:** planning cannot continue unless CONTEXT.md records explicit discussion evidence (`questions_answered >= 4`).
**Mandatory research gate:** once CONTEXT.md exists, trigger parallel dual-pass research (`gsd-phase-researcher` + `gsd-phase-research-deep`) and synthesize into canonical RESEARCH.md (unless `--skip-research` or `--gaps`) before generating plans.
**Quality gate:** if synthesized research is shallow/incomplete or lacks Context7 evidence for in-scope libraries/APIs, run one deeper pass + synthesis before planning.

Preserve all workflow gates (validation, research, planning, verification loop, routing).
</process>

