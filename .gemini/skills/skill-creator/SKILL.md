---
name: skill-creator
description: Creates, improves, evaluates, and troubleshoots Claude Code skills (SKILL.md files). Use when the user wants to build a new skill, write a SKILL.md from scratch, improve an existing skill, debug a skill that is not triggering or loading, resolve skill priority conflicts, or organize a multi-file skill with progressive disclosure. Make sure to use this skill whenever the user mentions building skills, writing a SKILL.md, creating reusable instructions, or wants to teach Claude how to do something automatically.
---

# Skill Creator

A skill for creating, iterating on, and optimizing Claude Code skills.

---

## The big picture

The best skills come from real pain points — instructions you find yourself repeating. Your job when using this skill is to figure out where the user is in the process and jump in:

- **"I want to make a skill for X"** → Help define, draft, test, iterate
- **"Here's my draft skill"** → Go straight to eval/iterate
- **"My skill won't trigger"** → Go straight to troubleshooting
- **"Just vibe with me"** → Be flexible; skip the formal loop if the user doesn't need it

Pay attention to technical familiarity cues. Terms like "YAML" and "frontmatter" are fine for developers; for non-technical users, explain them briefly. "Evaluation" and "benchmark" are borderline — use judgment.

---

## Skill anatomy

Every skill is a **directory** containing a `SKILL.md` file. The directory name must match the `name` field.

```
skill-name/
├── SKILL.md              ← required; SKILL all-caps, .md lowercase
└── Bundled resources (optional)
    ├── scripts/          ← executable code (tell Claude to RUN, not READ)
    ├── references/       ← docs loaded only when needed
    └── assets/           ← templates, icons, fonts
```

**Where skills live:**

| Location | Path | Who gets it | Priority |
|---|---|---|---|
| Enterprise | Managed settings | Entire org | **Highest** |
| Personal | `~/.claude/skills/` | You, all projects | 2nd |
| Project | `.claude/skills/` (repo root) | Anyone cloning | 3rd |
| Plugins | Installed plugins | Plugin users | Lowest |

Windows personal path: `C:/Users/<your-user>/.claude/skills/`

Priority matters: if a personal skill is being ignored, a higher-priority skill likely has the same name. Use specific names (`frontend-review` not `review`) to avoid conflicts.

---

## Frontmatter fields

```yaml
---
name: my-skill-name       # required — lowercase, hyphens only, max 64 chars
description: "..."        # required — max 1,024 chars; drives matching
allowed-tools: Read, Bash # optional — restricts tools when skill is active
model: sonnet             # optional — specifies which Claude model to use
---
```

Only `name` and `description` are required. Everything after the closing `---` is instruction content.

---

## Writing effective descriptions

The description is the most important field. Claude uses semantic matching — comparing the user's request against all available descriptions. If a skill isn't triggering, the description is almost always the cause.

A good description answers:
1. What does the skill do?
2. When should Claude use it?

**Formula:**
```
[Action verb] [what it does]. Use when [scenario 1], [scenario 2], or [scenario 3]. Make sure to use this skill whenever [broad trigger].
```

**Examples:**
```yaml
# Weak — too vague
description: Helps with code review.

# Strong — explicit triggers + undertrigger guard
description: Reviews pull requests for code quality, security issues, and team standards. Use when reviewing PRs, checking code changes, or when the user asks for feedback on a diff. Make sure to use this skill whenever the user mentions PR, pull request, or code review.
```

**Undertrigger note:** Claude currently tends not to use skills when they'd be useful. Make descriptions slightly "pushy" — end with "Make sure to use this skill whenever [broad trigger]."

All "when to use" information belongs in the description, not in the skill body (the body only loads after matching).

---

## Writing skill instructions

Below the frontmatter, write clear, actionable instructions in markdown. Use the imperative form. Explain *why* things matter rather than issuing heavy-handed commands — Claude is smart and responds better to reasoning than rigid MUSTs. If you find yourself writing ALWAYS or NEVER in all caps, try reframing with the reasoning behind it instead.

**Useful patterns:**

Define output formats clearly:
```markdown
## Report structure
Use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

Include examples:
```markdown
## Commit message format
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

---

## Progressive disclosure

Skills use a three-level loading system:
1. **Metadata** (name + description) — always in context
2. **SKILL.md body** — loaded when skill triggers; keep under 500 lines
3. **Bundled resources** — loaded only when needed; scripts execute without loading source

For complex skills, move detailed content to reference files and tell Claude when to load each one:

```markdown
## Supporting files
- Read `references/architecture-guide.md` only when asked about system design.
- Run `scripts/validate-env.sh` before starting any task to check dependencies.
```

**Scripts:** Tell Claude to **run** them, not **read** them. Only the output consumes context — the source stays out of the window. Ideal for environment validation, data transforms, and deterministic operations.

**Domain organization** for multi-variant skills:
```
cloud-deploy/
├── SKILL.md (workflow + selection logic)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

Claude reads only the relevant reference file. For large reference files (>300 lines), include a table of contents.

---

## Skills vs. other Claude Code features

| Feature | Loads when | Best for |
|---|---|---|
| **Skills** | Request matches description | Task-specific expertise |
| **CLAUDE.md** | Every conversation | Always-on project standards |
| **Subagents** | Delegated to explicitly | Isolated execution contexts |
| **Hooks** | Events (file save, tool call) | Automated side effects |
| **MCP servers** | Configured integrations | External tools and APIs |

Check the user's CLAUDE.md — content that only applies sometimes belongs in a skill, not CLAUDE.md.

**Subagents don't inherit skills automatically.** Built-in agents (Explorer, Plan, Verify) can't use skills at all. Only custom agents in `.claude/agents/` can, and only when explicitly listed:

```yaml
---
name: frontend-reviewer
tools: Bash, Glob, Grep, Read, Skill
skills: accessibility-audit, performance-check
---
```

Skills are loaded when the subagent starts, not on demand like in the main conversation.

---

## Sharing skills

- **Team:** Commit `.claude/skills/` to Git. Everyone gets skills on `git pull`.
- **Cross-project:** Distribute via plugin with a `skills/` directory in the plugin.
- **Org-wide:** Enterprise managed settings with `strictKnownMarketplaces` to control approved sources.

---

## The creation workflow

### 1. Capture intent

Start by understanding what the user wants. If the current conversation already contains a workflow to capture, extract it from the history first — tools used, steps taken, corrections made. Then confirm:

1. What should this skill enable Claude to do?
2. When should it trigger? (What phrases/contexts?)
3. What's the expected output format?
4. Do we need test cases? Skills with verifiable outputs (file transforms, code generation, fixed workflows) benefit from them. Subjective skills (writing style, creative work) often don't.

### 2. Interview and research

Ask about edge cases, input/output formats, example files, success criteria, dependencies. Check available MCPs if research would help. Come prepared to reduce burden on the user.

### 3. Write the draft SKILL.md

Write a complete draft based on the interview. Then look at it with fresh eyes and improve it before showing the user.

### 4. Test cases

Come up with 2–3 realistic test prompts — the kind a real user would actually say. Share them: *"Here are a few test cases I'd like to try. Do these look right?"*

Save to `evals/evals.json`:
```json
{
  "skill_name": "example-skill",
  "evals": [
    {"id": 1, "prompt": "User's task prompt", "expected_output": "Description of expected result", "files": []}
  ]
}
```

See `references/schemas.md` for the full schema including the `assertions` field.

### 5. Run evaluations

**In Claude Code (subagents available):**

For each test case, spawn two subagents in the same turn — one with the skill, one without (baseline). Launch everything at once so it all finishes around the same time.

- New skill → baseline is no skill at all
- Improving existing skill → baseline is the old version (snapshot it first: `cp -r <skill-path> <workspace>/skill-snapshot/`)

Organize results: `<skill-name>-workspace/iteration-1/<eval-name>/with_skill/outputs/`

While runs are in progress, draft assertions and explain them to the user. Good assertions are objectively verifiable and have descriptive names. For things that can be checked programmatically, write a script rather than eyeballing it.

Once runs finish:
1. Grade each run (see `agents/grader.md`)
2. Aggregate benchmark: `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>`
3. Do an analyst pass (see `agents/analyzer.md`) — look for non-discriminating assertions, high-variance evals, time/token tradeoffs
4. Launch the viewer:
```bash
nohup python <skill-creator-path>/eval-viewer/generate_review.py \
  <workspace>/iteration-N \
  --skill-name "my-skill" \
  --benchmark <workspace>/iteration-N/benchmark.json \
  > /dev/null 2>&1 &
```
For iteration 2+, add `--previous-workspace <workspace>/iteration-N-1`.

Tell the user: *"I've opened the results in your browser. The Outputs tab lets you review each test case and leave feedback. When you're done, come back and let me know."*

**IMPORTANT: Always generate the eval viewer BEFORE making corrections yourself. Get results in front of the human first.**

**In Claude.ai (no subagents):**

Run test cases inline — read SKILL.md, follow its instructions, complete the task yourself. Skip baselines and quantitative benchmarking. Present results in conversation, ask for feedback inline. If you can't open a browser, skip the viewer; show outputs directly.

**In Cowork:**

Same as Claude Code but use `--static <output_path>` instead of starting a server (no display). "Submit All Reviews" downloads `feedback.json`. Add "Create evals JSON and run eval-viewer/generate_review.py so human can review test cases" to your TodoList.

### 6. Iterate

Read feedback. Empty feedback means the user thought it was fine. Focus improvements on cases with complaints.

How to think about improvements:
- **Generalize** — you're creating something used many times, not just for these test cases. Avoid overfitting. Try different metaphors or patterns for stubborn issues.
- **Keep it lean** — remove things that aren't pulling their weight. Read transcripts, not just final outputs.
- **Explain the why** — LLMs respond better to reasoning than rigid commands.
- **Bundle repeated work** — if test runs all independently wrote the same helper script, put it in `scripts/` once.

Rerun all test cases into `iteration-N+1/`, launch viewer with `--previous-workspace`, wait for feedback, repeat until:
- The user says they're happy
- Feedback is all empty
- You're not making meaningful progress

---

## Description optimization

After the skill content is finalized, offer to optimize the description for triggering accuracy.

### Generate eval queries

Create 20 queries — a mix of should-trigger and should-not-trigger:
```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

Queries must be realistic and specific — include file paths, job context, casual phrasing, typos, varying lengths. The most valuable negatives are near-misses that share keywords but actually need something different. Avoid obviously irrelevant negatives (they don't test anything useful).

### Review with user

Present the eval set using the HTML template at `assets/eval_review.html`. Replace `__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, `__SKILL_DESCRIPTION_PLACEHOLDER__`. Open it and let the user edit/approve before running.

### Run the optimization loop

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model ID from your system prompt so the triggering test matches what the user actually experiences. The script splits evals 60/40 train/test, evaluates the current description (3 runs each for reliability), proposes improvements with extended thinking, and selects the best description by test score to avoid overfitting.

Apply `best_description` from the JSON output to the skill's frontmatter. Show before/after and report scores.

*Note: Description optimization requires the `claude` CLI tool (`claude -p`). Skip it on Claude.ai.*

---

## Packaging

If the `present_files` tool is available, package and present the skill to the user:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

**When updating an existing skill:**
- Preserve the original `name` field and directory name exactly (output `research-helper.skill`, not `research-helper-v2`)
- Copy to a writable location before editing: `cp -r <skill-path> /tmp/skill-name/`
- Package from the copy; direct writes may fail due to permissions

---

## Troubleshooting

First step always: run the agent skills validator (`uv` install recommended). It catches structural issues before you debug anything else.

| Symptom | Cause | Fix |
|---|---|---|
| Skill doesn't trigger | Description doesn't overlap semantically | Add trigger phrases matching how users actually speak; run `claude --debug` |
| Skill doesn't appear | Wrong structure | Directory name must match `name`; file must be exactly `SKILL.md` (SKILL all-caps, .md lowercase) |
| Wrong skill used | Descriptions too similar | Make descriptions more distinct from each other |
| Personal skill ignored | Higher-priority skill has same name | Rename yours to be more specific |
| Plugin skills missing | Cache issue | Clear cache, restart Claude Code, reinstall |
| Runtime error | Deps / permissions / paths | Install dependencies; `chmod +x` scripts; use forward slashes everywhere including Windows |

After any change, restart Claude Code for it to take effect.

---

## Reference files

- `agents/grader.md` — How to evaluate assertions against outputs
- `agents/comparator.md` — Blind A/B comparison between two outputs
- `agents/analyzer.md` — How to analyze why one version beat another
- `references/schemas.md` — JSON structures for evals.json, grading.json, benchmark.json

---

## Core loop (summary)

1. Understand what the skill is about
2. Draft or edit the skill
3. Run test cases (with-skill and baseline)
4. Generate eval viewer — get human feedback **before** making corrections yourself
5. Improve and repeat until satisfied
6. Optimize the description
7. Package and return the `.skill` file

Good luck!
