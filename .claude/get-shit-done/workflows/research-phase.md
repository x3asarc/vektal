<purpose>
Research how to implement a phase. Spawns `gsd-phase-researcher` and `gsd-phase-research-deep` in parallel, then synthesizes to canonical RESEARCH.md.

Standalone research command. For most workflows, use `/gsd:plan-phase` which integrates research automatically.
</purpose>

<process>

## Step 0: Resolve Model Profile

@./.claude/get-shit-done/references/model-profile-resolution.md

Resolve model for:
- `gsd-phase-researcher`
- `gsd-phase-research-deep`

## Step 1: Normalize and Validate Phase

@./.claude/get-shit-done/references/phase-argument-parsing.md

```bash
PHASE_INFO=$(node ./.claude/get-shit-done/bin/gsd-tools.js roadmap get-phase "${PHASE}")
```

If `found` is false: Error and exit.

## Step 2: Check Existing Research

```bash
ls .planning/phases/${PHASE}-*/RESEARCH.md 2>/dev/null
```

If exists: Offer update/view/skip options.

## Step 3: Gather Phase Context

## Step 3.5: Context7 Gate

If phase scope includes named libraries/frameworks/APIs:
- Researcher must run Context7 (`resolve-library-id` + `query-docs`) before generic web search.
- RESEARCH.md must include Context7 evidence (library IDs + queried topics), or explicit `Context7 not applicable` reason.

```bash
# Phase section from roadmap (already loaded in PHASE_INFO)
echo "$PHASE_INFO" | jq -r '.section'
cat .planning/REQUIREMENTS.md 2>/dev/null
cat .planning/phases/${PHASE}-*/*-CONTEXT.md 2>/dev/null
# Decisions from state-snapshot (structured JSON)
node ./.claude/get-shit-done/bin/gsd-tools.js state-snapshot | jq '.decisions'
```

## Step 4: Spawn Parallel Researchers

```bash
CORE_RESEARCH_PATH=.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH-core.md
DEEP_RESEARCH_PATH=.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH-deep.md
FINAL_RESEARCH_PATH=.planning/phases/${PHASE}-{slug}/${PHASE}-RESEARCH.md
```

```
Task(
  prompt="First, read ./.claude/agents/gsd-phase-researcher.md for your role and instructions.\n\n<objective>\nResearch implementation approach for Phase {phase}: {name}\n</objective>\n\n<context>\nPhase description: {description}\nRequirements: {requirements}\nPrior decisions: {decisions}\nPhase context: {context_md}\n</context>\n\n<research_requirements>\n- Use Context7 first for in-scope libraries/frameworks/APIs.\n- Include Context7 evidence in RESEARCH output Sources: library IDs and queried topics.\n- If Context7 cannot be used for a technology, state explicit reason and fallback source.\n</research_requirements>\n\n<output>\nWrite to: " + CORE_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Research Phase {phase} - baseline"
)

Task(
  prompt="First, read ./.claude/agents/gsd-phase-research-deep.md for your role and instructions.\n\n<objective>\nRun exhaustive multi-pass deep research for Phase {phase}: {name}\n</objective>\n\n<context>\nPhase description: {description}\nRequirements: {requirements}\nPrior decisions: {decisions}\nPhase context: {context_md}\n</context>\n\n<output>\nWrite to: " + DEEP_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Research Phase {phase} - deep parallel"
)
```

## Step 5: Synthesize Parallel Outputs

```
Task(
  prompt="<objective>\nSynthesize baseline and deep reports into one canonical phase RESEARCH.md.\n</objective>\n\n<inputs>\n- baseline: " + CORE_RESEARCH_PATH + "\n- deep: " + DEEP_RESEARCH_PATH + "\n- context: {context_md}\n- requirements: {requirements}\n</inputs>\n\n<rules>\n- Keep all validated contracts, metrics, and failure modes.\n- Keep Context7 evidence and requirement mapping.\n- Remove duplication and resolve conflicts explicitly.\n- Mark missing info as explicit gaps.\n</rules>\n\n<output>\nWrite to: " + FINAL_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Synthesize Phase {phase} research"
)
```

## Step 6: Handle Return

- `## RESEARCH COMPLETE` -> Display summary, offer: Plan/Dig deeper/Review/Done
- `## CHECKPOINT REACHED` -> Present to user, spawn continuation
- `## RESEARCH INCONCLUSIVE` -> Show attempts, offer: Add context/Try different mode/Manual
- Quality gate: if synthesized output misses concrete contracts, failure modes, requirement mapping, or Context7 evidence for in-scope technologies, run one deeper parallel pass + synthesis before returning complete.

</process>




