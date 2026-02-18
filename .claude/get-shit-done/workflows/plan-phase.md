<purpose>
Create executable phase prompts (PLAN.md files) for a roadmap phase with integrated research and verification. Default flow: Research (if needed) -> Plan -> Verify -> Done. Orchestrates parallel research passes (`gsd-phase-researcher` + `gsd-phase-research-deep`), synthesis, gsd-planner, and gsd-plan-checker with a revision loop (max 3 iterations).
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.

@C:/Users/Hp/Documents/Shopify Scraping Script/.claude/get-shit-done/references/ui-brand.md
</required_reading>

<process>

## 1. Initialize

Load all context in one call (include file contents to avoid redundant reads):

```bash
INIT=$(node C:/Users/Hp/Documents/Shopify Scraping Script/.claude/get-shit-done/bin/gsd-tools.js init plan-phase "$PHASE" --include state,roadmap,requirements,context,research,verification,uat)
```

Parse JSON for: `researcher_model`, `planner_model`, `checker_model`, `research_enabled`, `plan_checker_enabled`, `commit_docs`, `phase_found`, `phase_dir`, `phase_number`, `phase_name`, `phase_slug`, `padded_phase`, `has_research`, `has_context`, `has_plans`, `plan_count`, `planning_exists`, `roadmap_exists`.

**File contents (from --include):** `state_content`, `roadmap_content`, `requirements_content`, `context_content`, `research_content`, `verification_content`, `uat_content`. These are null if files don't exist.

**If `planning_exists` is false:** Error â€” run `/gsd:new-project` first.

## 2. Parse and Normalize Arguments

Extract from $ARGUMENTS: phase number (integer or decimal like `2.1`), flags (`--research`, `--skip-research`, `--gaps`, `--skip-verify`).

**If no phase number:** Detect next unplanned phase from roadmap.

**If `phase_found` is false:** Validate phase exists in ROADMAP.md. If valid, create the directory using `phase_slug` and `padded_phase` from init:
```bash
mkdir -p ".planning/phases/${padded_phase}-${phase_slug}"
```

**Existing artifacts from init:** `has_research`, `has_plans`, `plan_count`.

## 3. Validate Phase

```bash
PHASE_INFO=$(node C:/Users/Hp/Documents/Shopify Scraping Script/.claude/get-shit-done/bin/gsd-tools.js roadmap get-phase "${PHASE}")
```

**If `found` is false:** Error with available phases. **If `found` is true:** Extract `phase_number`, `phase_name`, `goal` from JSON.

## 4. Load CONTEXT.md

Use `context_content` from init JSON (already loaded via `--include context`).

**CRITICAL:** Use `context_content` from INIT â€” pass to researcher, planner, checker, and revision agents.

If `context_content` is not null, display: `Using phase context from: ${PHASE_DIR}/*-CONTEXT.md`

## 4.5 Context Gate (Auto-trigger Discuss When Missing)

If `context_content` is null and not running `--gaps`:

1. Display:
   `No CONTEXT.md found for this phase. Triggering discuss-phase question flow first.`
2. Run discuss workflow inline:
   `@C:/Users/Hp/Documents/Shopify Scraping Script/.claude/get-shit-done/workflows/discuss-phase.md`
3. Complete the full context question flow and write `{phase}-CONTEXT.md`.
4. Re-run init to refresh includes:

```bash
INIT=$(node C:/Users/Hp/Documents/Shopify Scraping Script/.claude/get-shit-done/bin/gsd-tools.js init plan-phase "$PHASE" --include state,roadmap,requirements,context,research,verification,uat)
```

5. Re-parse `context_content` and continue only when context is present.

6. Validate that context came from explicit Q&A (not assumptions):
   - CONTEXT.md must include a `## Discussion Evidence` section
   - `questions_answered` must be present and >= 4
   - `user_answers_captured` must be `yes`

If discussion evidence is missing/incomplete, run discuss flow again and do not continue.

If context is still missing after discuss flow, stop and report blocker instead of planning blind.

## 5. Handle Research

**Skip if:** `--gaps` flag, `--skip-research` flag, or `research_enabled` is false (from init) without `--research` override.

**If `has_research` is true (from init) AND no `--research` flag:** Use existing, skip to step 6.

**If RESEARCH.md missing OR `--research` flag:**

**MANDATORY:** keep `gsd-phase-researcher` and add parallel `gsd-phase-research-deep`, then synthesize both outputs into canonical `{phase}-RESEARCH.md`.
Do not continue to planner without the synthesized research artifact unless `--skip-research` or `--gaps`.

Display banner:
```text
GSD -> RESEARCHING PHASE {X}

* Spawning 2 parallel researchers...
  - Baseline implementation researcher (gsd-phase-researcher)
  - Deep exhaustive researcher (gsd-phase-research-deep)
* Then synthesizing to final {phase}-RESEARCH.md
```

### Spawn parallel researchers

```bash
PHASE_DESC=$(node ./.claude/get-shit-done/bin/gsd-tools.js roadmap get-phase "${PHASE}" | jq -r '.section')
# Use requirements_content from INIT (already loaded via --include requirements)
REQUIREMENTS=$(echo "$INIT" | jq -r '.requirements_content // empty' | grep -A100 "## Requirements" | head -50)
STATE_SNAP=$(node ./.claude/get-shit-done/bin/gsd-tools.js state-snapshot)
# Extract decisions from state-snapshot JSON: jq '.decisions[] | "\(.phase): \(.summary) - \(.rationale)"'
```

Common research context:

```markdown
<objective>
Research how to implement Phase {phase_number}: {phase_name}
Answer: "What do I need to know to PLAN this phase well?"
</objective>

<phase_context>
IMPORTANT: If CONTEXT.md exists below, it contains user decisions from /gsd:discuss-phase.
- **Decisions** = Locked -> research THESE deeply, no alternatives
- **Claude's Discretion** = Freedom areas -> research options, recommend
- **Deferred Ideas** = Out of scope -> ignore

{context_content}
</phase_context>

<additional_context>
**Phase description:** {phase_description}
**Requirements:** {requirements}
**Prior decisions:** {decisions}
</additional_context>
```

```bash
CORE_RESEARCH_PATH="{phase_dir}/{phase}-RESEARCH-core.md"
DEEP_RESEARCH_PATH="{phase_dir}/{phase}-RESEARCH-deep.md"
FINAL_RESEARCH_PATH="{phase_dir}/{phase}-RESEARCH.md"
```

```
Task(
  prompt="First, read ./.claude/agents/gsd-phase-researcher.md for your role and instructions.\n\n" + common_research_context + "\n<output>\nWrite to: " + CORE_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Research Phase {phase} - baseline"
)

Task(
  prompt="First, read ./.claude/agents/gsd-phase-research-deep.md for your role and instructions.\n\n" + common_research_context + "\n<output>\nWrite to: " + DEEP_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Research Phase {phase} - deep parallel"
)
```

### Synthesize both outputs into canonical RESEARCH.md

```
Task(
  prompt="<objective>\nMerge baseline and deep research into one canonical phase RESEARCH.md.\n</objective>\n\n<inputs>\n- baseline: " + CORE_RESEARCH_PATH + "\n- deep: " + DEEP_RESEARCH_PATH + "\n- context: {context_content}\n- requirements: {requirements}\n</inputs>\n\n<rules>\n- Preserve all valid concrete contracts from both files.\n- Keep Context7 evidence and requirement mapping.\n- Deduplicate overlap and resolve contradictions explicitly.\n- If data is missing, mark as explicit gap.\n- Final output must satisfy planner-consumable RESEARCH.md format.\n</rules>\n\n<output>\nWrite to: " + FINAL_RESEARCH_PATH + "\n</output>",
  subagent_type="general-purpose",
  model="{researcher_model}",
  description="Synthesize Phase {phase} research"
)
```

### Handle Research Return

- **`## RESEARCH COMPLETE`:** Display confirmation, continue to step 6
- **`## RESEARCH BLOCKED`:** Display blocker, offer: 1) Provide context, 2) Skip research, 3) Abort
- **Depth gate:** if synthesized output misses concrete contracts/failure modes/requirement mapping or Context7 evidence for in-scope technologies, run one additional deep pass + synthesis before step 6.

### Refresh INIT after synthesis

```bash
INIT=$(node ./.claude/get-shit-done/bin/gsd-tools.js init plan-phase "$PHASE" --include state,roadmap,requirements,context,research,verification,uat)
```

## 6. Check Existing Plans

```bash
ls "${PHASE_DIR}"/*-PLAN.md 2>/dev/null
```

**If exists:** Offer: 1) Add more plans, 2) View existing, 3) Replan from scratch.

## 7. Use Context Files from INIT

All file contents are already loaded via `--include` in step 1 (`@` syntax doesn't work across Task() boundaries):

```bash
# Extract from INIT JSON (no need to re-read files)
STATE_CONTENT=$(echo "$INIT" | jq -r '.state_content // empty')
ROADMAP_CONTENT=$(echo "$INIT" | jq -r '.roadmap_content // empty')
REQUIREMENTS_CONTENT=$(echo "$INIT" | jq -r '.requirements_content // empty')
RESEARCH_CONTENT=$(echo "$INIT" | jq -r '.research_content // empty')
VERIFICATION_CONTENT=$(echo "$INIT" | jq -r '.verification_content // empty')
UAT_CONTENT=$(echo "$INIT" | jq -r '.uat_content // empty')
CONTEXT_CONTENT=$(echo "$INIT" | jq -r '.context_content // empty')
```

## 8. Spawn gsd-planner Agent

Display banner:
```
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
 GSD â–º PLANNING PHASE {X}
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

â—† Spawning planner...
```

Planner prompt:

```markdown
<planning_context>
**Phase:** {phase_number}
**Mode:** {standard | gap_closure}

**Project State:** {state_content}
**Roadmap:** {roadmap_content}
**Requirements:** {requirements_content}

**Phase Context:**
IMPORTANT: If context exists below, it contains USER DECISIONS from /gsd:discuss-phase.
- **Decisions** = LOCKED â€” honor exactly, do not revisit
- **Claude's Discretion** = Freedom â€” make implementation choices
- **Deferred Ideas** = Out of scope â€” do NOT include

{context_content}

**Research:** {research_content}
**Gap Closure (if --gaps):** {verification_content} {uat_content}
</planning_context>

<downstream_consumer>
Output consumed by /gsd:execute-phase. Plans need:
- Frontmatter (wave, depends_on, files_modified, autonomous)
- Tasks in XML format
- Verification criteria
- must_haves for goal-backward verification
</downstream_consumer>

<quality_gate>
- [ ] PLAN.md files created in phase directory
- [ ] Each plan has valid frontmatter
- [ ] Tasks are specific and actionable
- [ ] Dependencies correctly identified
- [ ] Waves assigned for parallel execution
- [ ] must_haves derived from phase goal
</quality_gate>
```

```
Task(
  prompt="First, read C:/Users/Hp/Documents/Shopify Scraping Script/.claude/agents/gsd-planner.md for your role and instructions.\n\n" + filled_prompt,
  subagent_type="general-purpose",
  model="{planner_model}",
  description="Plan Phase {phase}"
)
```

## 9. Handle Planner Return

- **`## PLANNING COMPLETE`:** Display plan count. If `--skip-verify` or `plan_checker_enabled` is false (from init): skip to step 13. Otherwise: step 10.
- **`## CHECKPOINT REACHED`:** Present to user, get response, spawn continuation (step 12)
- **`## PLANNING INCONCLUSIVE`:** Show attempts, offer: Add context / Retry / Manual

## 10. Spawn gsd-plan-checker Agent

Display banner:
```
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
 GSD â–º VERIFYING PLANS
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

â—† Spawning plan checker...
```

```bash
PLANS_CONTENT=$(cat "${PHASE_DIR}"/*-PLAN.md 2>/dev/null)
```

Checker prompt:

```markdown
<verification_context>
**Phase:** {phase_number}
**Phase Goal:** {goal from ROADMAP}

**Plans to verify:** {plans_content}
**Requirements:** {requirements_content}

**Phase Context:**
IMPORTANT: Plans MUST honor user decisions. Flag as issue if plans contradict.
- **Decisions** = LOCKED â€” plans must implement exactly
- **Claude's Discretion** = Freedom areas â€” plans can choose approach
- **Deferred Ideas** = Out of scope â€” plans must NOT include

{context_content}
</verification_context>

<expected_output>
- ## VERIFICATION PASSED â€” all checks pass
- ## ISSUES FOUND â€” structured issue list
</expected_output>
```

```
Task(
  prompt=checker_prompt,
  subagent_type="gsd-plan-checker",
  model="{checker_model}",
  description="Verify Phase {phase} plans"
)
```

## 11. Handle Checker Return

- **`## VERIFICATION PASSED`:** Display confirmation, proceed to step 13.
- **`## ISSUES FOUND`:** Display issues, check iteration count, proceed to step 12.

## 12. Revision Loop (Max 3 Iterations)

Track `iteration_count` (starts at 1 after initial plan + check).

**If iteration_count < 3:**

Display: `Sending back to planner for revision... (iteration {N}/3)`

```bash
PLANS_CONTENT=$(cat "${PHASE_DIR}"/*-PLAN.md 2>/dev/null)
```

Revision prompt:

```markdown
<revision_context>
**Phase:** {phase_number}
**Mode:** revision

**Existing plans:** {plans_content}
**Checker issues:** {structured_issues_from_checker}

**Phase Context:**
Revisions MUST still honor user decisions.
{context_content}
</revision_context>

<instructions>
Make targeted updates to address checker issues.
Do NOT replan from scratch unless issues are fundamental.
Return what changed.
</instructions>
```

```
Task(
  prompt="First, read C:/Users/Hp/Documents/Shopify Scraping Script/.claude/agents/gsd-planner.md for your role and instructions.\n\n" + revision_prompt,
  subagent_type="general-purpose",
  model="{planner_model}",
  description="Revise Phase {phase} plans"
)
```

After planner returns -> spawn checker again (step 10), increment iteration_count.

**If iteration_count >= 3:**

Display: `Max iterations reached. {N} issues remain:` + issue list

Offer: 1) Force proceed, 2) Provide guidance and retry, 3) Abandon

## 13. Present Final Status

Route to `<offer_next>`.

</process>

<offer_next>
Output this markdown directly (not as a code block):

â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
 GSD â–º PHASE {X} PLANNED âœ“
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”

**Phase {X}: {Name}** â€” {N} plan(s) in {M} wave(s)

| Wave | Plans | What it builds |
|------|-------|----------------|
| 1    | 01, 02 | [objectives] |
| 2    | 03     | [objective]  |

Research: {Completed | Used existing | Skipped}
Verification: {Passed | Passed with override | Skipped}

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

## â–¶ Next Up

**Execute Phase {X}** â€” run all {N} plans

/gsd:execute-phase {X}

<sub>/clear first â†’ fresh context window</sub>

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

**Also available:**
- cat .planning/phases/{phase-dir}/*-PLAN.md â€” review plans
- /gsd:plan-phase {X} --research â€” re-research first

â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
</offer_next>

<success_criteria>
- [ ] .planning/ directory validated
- [ ] Phase validated against roadmap
- [ ] Phase directory created if needed
- [ ] CONTEXT.md loaded early (step 4) and passed to ALL agents
- [ ] If CONTEXT.md missing, discuss-phase question flow auto-runs before research/planning
- [ ] CONTEXT.md includes explicit discussion evidence (`questions_answered >= 4`)
- [ ] Research completed (unless --skip-research or --gaps or exists)
- [ ] gsd-phase-researcher and gsd-phase-research-deep spawned in parallel with CONTEXT.md
- [ ] Parallel outputs synthesized into canonical `{phase}-RESEARCH.md`
- [ ] RESEARCH.md contains Context7 evidence for in-scope libraries/APIs (or explicit not-applicable rationale)
- [ ] Existing plans checked
- [ ] gsd-planner spawned with CONTEXT.md + RESEARCH.md
- [ ] Plans created (PLANNING COMPLETE or CHECKPOINT handled)
- [ ] gsd-plan-checker spawned with CONTEXT.md
- [ ] Verification passed OR user override OR max iterations with user decision
- [ ] User sees status between agent spawns
- [ ] User knows next steps
</success_criteria>



