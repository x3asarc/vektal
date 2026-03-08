---
name: review-implementing
description: Use before implementing any plan or spec. Evaluate implementation plans against requirements, surface gaps, ambiguities, or risks before a single line of code is written.
---

# Review-Implementing

## Core Principle

**Read the spec. Read the plan. Find where they diverge before implementing.**

The cheapest bugs are the ones caught in review. A 10-minute plan review prevents a 2-hour debugging session.

## When to Use

- You have a spec/requirements doc + an implementation plan
- Before starting any non-trivial task (3+ steps)
- When a lead hands off work to a sub-agent
- After brainstorming produces a design doc

## Process

### Step 1: Load Both Documents

Read the spec (requirements, design doc, PLAN.md, or task description) AND the implementation plan in full before forming any opinion.

### Step 2: Alignment Check

For each requirement in the spec, find the corresponding step in the plan:

```
REQ-01: [requirement text]
  → Plan step: [which step addresses this]
  → Gap? [YES/NO — if yes, describe]
```

Flag any requirement with no corresponding plan step as a **gap**.

### Step 3: Risk Surface

For each plan step, ask:
- Does this step have a clear success criterion?
- Are there hidden dependencies not mentioned?
- Could this break something outside the stated scope?
- Is the order correct? (Does step N depend on step N-1 being done first?)

### Step 4: Ambiguity Scan

Mark every ambiguous instruction with `[AMBIGUOUS]`:

```
Step 4: "Update the config" [AMBIGUOUS — which config? what values?]
```

### Step 5: Output

```
REVIEW RESULT: [GO / HOLD / REWORK]

Gaps (requirements with no plan step):
- [list or NONE]

Risks:
- [list or NONE]

Ambiguities:
- [list or NONE]

Recommendation:
- GO: plan is complete, aligned, unambiguous — proceed to implementation
- HOLD: clarify [specific question] before starting
- REWORK: plan missing steps for [specific requirements]
```

## Rules

- Never start implementing while this skill is active — review first, implement after
- A HOLD verdict must include exactly ONE question to resolve (not a list)
- A REWORK verdict must include the specific missing plan steps, not just "add more detail"
