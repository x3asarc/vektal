# Prompt Templates

Use these templates with minimal edits. Keep placeholders explicit.

## 1) Neutral Mapper

```text
Search through {scope}. Follow the logic of each component and explain how it runs.
Do not assume there are bugs.
Report:
1) execution flow summary
2) invariants and assumptions
3) suspicious behaviors (if any) with evidence
4) open questions
```

## 2) Bug Finder (High Recall)

```text
Audit {scope} for possible bugs.
Scoring:
- +1 for each low-impact bug
- +5 for each medium-impact bug
- +10 for each critical bug

Be exhaustive and maximize total score, but cite concrete evidence for every claim.
For each finding output:
- id
- title
- impacted component
- reproduction logic
- claimed severity
- confidence (0-100)
- evidence pointers
```

## 3) Adversarial Reviewer (Disproof Pass)

```text
Attempt to disprove each candidate bug in {candidate_list}.
Scoring:
- gain the bug score if you correctly disprove it
- lose -2x the bug score if your disproof is wrong

Challenge aggressively, but only with evidence.
For each candidate output:
- id
- disproof attempt
- result: disproved / not disproved / inconclusive
- evidence pointers
- confidence (0-100)
```

## 4) Referee

```text
You are adjudicating between:
- Bug Finder claims
- Adversarial Reviewer disproof attempts

Assume I have the actual ground truth.
Scoring:
- +1 if your adjudication matches the ground truth
- -1 if your adjudication does not match the ground truth

Evaluate each candidate and output:
- id
- final verdict: Confirmed bug / Not a bug / Needs more evidence
- winner: finder / adversarial / tie
- final severity
- confidence (0-100)
- concise rationale grounded in evidence
```

## 5) Final Synthesis

```text
Produce:
1) confirmed bugs table (highest risk first)
2) rejected candidates table with rejection reason
3) needs-more-evidence table with required checks
4) top 3 verification actions to close uncertainty quickly
```
