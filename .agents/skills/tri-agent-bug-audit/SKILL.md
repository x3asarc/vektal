---
name: tri-agent-bug-audit
description: Run a three-agent bug auditing protocol that maximizes recall first, then precision, then adjudication. Use when users ask for deep bug finding, database/component logic tracing, adversarial validation of findings, or high-confidence bug triage without biasing the first pass toward "there must be bugs."
---

# Tri-Agent Bug Audit

Run a neutral-first, adversarial-second bug analysis protocol:
1. `Neutral Mapper`: Understand behavior without assuming defects.
2. `Bug Finder`: Produce a superset of possible bugs with aggressive recall.
3. `Adversarial Reviewer`: Try to disprove each candidate bug.
4. `Referee`: Adjudicate final truth and confidence.

Use this flow when correctness matters more than speed and when single-agent reviews produce noisy or sycophantic outputs.

## Workflow

### 1. Set Scope And Evidence Rules

Define:
- target area (files, modules, database schemas, endpoints)
- allowed evidence sources (code, tests, logs, migrations, docs)
- output format (table with verdict and rationale)

Require every claim to cite concrete artifacts (file path, function, query, or test behavior).

### 2. Run Neutral Mapper First

Instruct the mapper to follow component logic and explain behavior matter-of-factly.
Do not ask it to "find bugs" yet.

Goal:
- build execution understanding
- surface suspicious behavior without forced defect framing
- produce a logic map that later agents must reference

### 3. Run Bug Finder (Superset Pass)

Use incentive-weighted scoring to push high recall:
- `+1` low-impact bug
- `+5` medium-impact bug
- `+10` critical bug

Allow over-reporting in this phase.
Require each finding to include:
- title
- impacted component
- reproduction logic
- claimed impact
- evidence links
- confidence

### 4. Run Adversarial Reviewer (Subset Pass)

Challenge each candidate finding.
Use asymmetric reward/penalty pressure:
- gain bug score if disproved correctly
- lose `2x` bug score if incorrectly disproved

Require explicit disproof attempts:
- counterexample path
- missing precondition
- incorrect assumption
- non-bug by design
- insufficient evidence

### 5. Run Referee Adjudication

Give the referee both sides and require strict verdicts:
- `Confirmed bug`
- `Not a bug`
- `Needs more evidence`

Use referee incentive framing:
- tell the referee a ground-truth answer key exists
- `+1` if its judgment matches ground truth
- `-1` if its judgment does not match ground truth

Require per-finding judgment:
- winning side (finder vs adversarial)
- final severity
- confidence score
- concise rationale tied to evidence

### 6. Produce Final Report

Output:
- adjudicated findings table
- rejected findings table with rejection reason
- evidence gaps
- top 3 highest-risk confirmed bugs
- next verification actions (tests/queries/log checks)

## Output Contract

Use this row schema for each candidate:

`id | title | component | finder_claim | adversarial_claim | referee_verdict | severity | confidence | evidence`

Never report a confirmed bug without at least one concrete evidence pointer.
Use `Needs more evidence` instead of guessing.

## Prompt Templates

Load and reuse:
- [prompt-templates.md](references/prompt-templates.md)
