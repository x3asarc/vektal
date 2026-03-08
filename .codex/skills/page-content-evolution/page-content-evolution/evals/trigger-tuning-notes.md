# Trigger Tuning Notes

## Objective

Improve trigger precision for `page-content-evolution` against nearby skills:
- `frontend-design`
- `taste-to-token-extractor`
- `frontend-deploy-debugger`
- `deployment-validator`
- `firecrawl`

## Description strategy update

Changes applied:
- Emphasized `existing pages`, `actions/controls/content blocks`, and `action-model improvements`.
- Added explicit language for "page feels too basic" and "without random feature bloat".
- Reduced overlap with pure visual redesign prompts.

## Eval set

20-query trigger set created:
- Source: `evals/trigger-evals.json`
- Positives: 10
- Negatives: 10 (near-miss heavy)

## Manual expected classification

- Should trigger for page functionality/IA/content-action audits.
- Should not trigger for pure visual redesign, deployment debugging, URL health validation, generic scraping, or skill authoring tasks.

## Limitation

Automated description-loop tooling (`scripts.run_loop`) is not present in this local `skill-creator` install, so this iteration used a manual optimization pass with explicit near-miss eval design.

