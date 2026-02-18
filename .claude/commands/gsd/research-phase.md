---
name: gsd:research-phase
description: Research how to implement a phase (standalone - usually use /gsd:plan-phase instead)
argument-hint: "[phase]"
allowed-tools:
  - Read
  - Bash
  - Task
---

<objective>
Research how to implement a phase. Runs dual-pass research in parallel (`gsd-phase-researcher` + `gsd-phase-research-deep`) and synthesizes to canonical RESEARCH.md.

**Note:** This is a standalone research command. For most workflows, use `/gsd:plan-phase` which integrates research automatically.

**Use this command when:**
- You want to research without planning yet
- You want to re-research after planning is complete
- You need to investigate before deciding if a phase is feasible

**Orchestrator role:** Parse phase, validate against roadmap, check existing research, gather context, run parallel researchers, synthesize output, present results.

**Why subagent:** Research burns context fast (WebSearch, Context7 queries, source verification). Fresh 200k context for investigation. Main context stays lean for user interaction.
</objective>

<context>
Phase number: $ARGUMENTS (required)

Normalize phase input in step 1 before any directory lookups.
</context>

<process>

## 0. Initialize Context

```bash
INIT=$(node ./.claude/get-shit-done/bin/gsd-tools.js init phase-op "$ARGUMENTS")
```

Extract from init JSON: `phase_dir`, `phase_number`, `phase_name`, `phase_found`, `commit_docs`, `has_research`.

Resolve researcher model:
```bash
RESEARCHER_MODEL=$(node ./.claude/get-shit-done/bin/gsd-tools.js resolve-model gsd-phase-researcher --raw)
```

## 1. Validate Phase

```bash
PHASE_INFO=$(node ./.claude/get-shit-done/bin/gsd-tools.js roadmap get-phase "${phase_number}")
```

**If `found` is false:** Error and exit. **If `found` is true:** Extract `phase_number`, `phase_name`, `goal` from JSON.

## 2. Check Existing Research

```bash
ls .planning/phases/${PHASE}-*/RESEARCH.md 2>/dev/null
```

**If exists:** Offer: 1) Update research, 2) View existing, 3) Skip. Wait for response.

**If doesn't exist:** Continue.

## 3. Gather Phase Context

```bash
# Phase section already loaded in PHASE_INFO
echo "$PHASE_INFO" | jq -r '.section'
cat .planning/REQUIREMENTS.md 2>/dev/null
cat .planning/phases/${PHASE}-*/*-CONTEXT.md 2>/dev/null
grep -A30 "### Decisions Made" .planning/STATE.md 2>/dev/null
```

Present summary with phase description, requirements, prior decisions.

## 4. Spawn Parallel Researchers + Synthesis

Run two researcher agents in parallel:
- baseline: `gsd-phase-researcher`
- deep: `gsd-phase-research-deep`

Write intermediates:
- `.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH-core.md`
- `.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH-deep.md`

Then synthesize both into canonical:
- `.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH.md`

Use the same context package for both passes (phase description, requirements, prior decisions, CONTEXT.md).
Synthesis must dedupe overlap, preserve concrete contracts/failure modes, and keep Context7 evidence.

## 5. Handle Agent Return

**`## RESEARCH COMPLETE`:** Display summary, offer: Plan phase, Dig deeper, Review full, Done.

**`## CHECKPOINT REACHED`:** Present to user, get response, spawn continuation.

**`## RESEARCH INCONCLUSIVE`:** Show what was attempted, offer: Add context, Try different mode, Manual.

## 6. Spawn Continuation Agent

```markdown
<objective>
Continue research for Phase {phase_number}: {phase_name}
</objective>

<prior_state>
Research file: @.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH.md
</prior_state>

<checkpoint_response>
**Type:** {checkpoint_type}
**Response:** {user_response}
</checkpoint_response>
```

```
Task(
  prompt="First, read ./.claude/agents/gsd-phase-researcher.md for your role and instructions.\n\n" + continuation_prompt,
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Continue research Phase {phase}"
)
```

</process>

<success_criteria>
- [ ] Phase validated against roadmap
- [ ] Existing research checked
- [ ] gsd-phase-researcher and gsd-phase-research-deep spawned in parallel with context
- [ ] Parallel outputs synthesized to canonical RESEARCH.md
- [ ] Checkpoints handled correctly
- [ ] User knows next steps
</success_criteria>


