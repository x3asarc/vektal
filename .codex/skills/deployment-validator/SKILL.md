---
disable-model-invocation: true
name: deployment-validator
description: Use when user wants to Validate that a frontend is truly reachable and healthy on localhost and public URL using repeatable evidence. Use after `frontend-deploy-debugger` on every loop iteration. If validation fails, send comprehensive analysis and remediation guidance back to `frontend-design`; if validation passes, stop the pipeline and call no further skills.
---

# Deployment Validator

Provide objective pass/fail evidence and control the iteration loop.

---

## Pipeline position

- Previous skill: `frontend-deploy-debugger`
- Current skill: `deployment-validator`
- Next skill on FAIL: `frontend-design`
- Next skill on PASS: none (stop)

---

## Required input handoff

Accept from `frontend-deploy-debugger` when available:

- `local_url`
- `public_url`
- `expected_service`
- `debug_summary`
- `iteration`

If any field is missing, infer from repo/runtime and mark unknown values as `N/A`.

---

## What this skill does

1. Run mandatory deployment gates.
2. Capture command-level evidence.
3. Return strict verdict:
- `PASS`: no more tools are called.
- `FAIL`: send comprehensive feedback to `frontend-design` for next iteration.

---

## Required output format

```markdown
# Deployment Validation Report

## Target
- Local URL:
- Public URL:
- Expected service:
- Iteration:

## Gate Results
1. Local HTTP gate: PASS | FAIL
2. Container/process health gate: PASS | FAIL
3. Public HTTP gate: PASS | FAIL
4. Static assets/basic app shell gate: PASS | FAIL

## Evidence
- Commands run:
- Status codes:
- Key response snippets:
- Logs/errors:

## Verdict
- Overall: PASS | FAIL
- Blocking failures:
- Next fix target:
```

---

## Validation workflow

### Step 1: Define targets

Collect:

- local URL and expected port
- public URL/domain
- expected marker or endpoint for success

### Step 2: Run mandatory gates

Mandatory checks:

- local URL returns expected status code
- service/container process is healthy
- public URL returns expected status code
- response includes expected app marker

If any mandatory gate fails, overall is `FAIL`.

### Step 3: Optional deeper checks

Optional when useful:

- Playwright browser smoke run
- external fetch verification

Optional tooling failures must not hide mandatory gate results.

---

## Loop-control handoff

### On PASS

Return:

```json
{
  "overall": "PASS",
  "next_skill": null,
  "pipeline_action": "stop",
  "reason": "All mandatory gates passed."
}
```

Do not call any further tools.

### On FAIL

Return:

```json
{
  "overall": "FAIL",
  "next_skill": "frontend-design",
  "pipeline_action": "iterate",
  "iteration": "<n+1>",
  "failing_gates": ["local_http", "public_http"],
  "regressions_detected": ["brief item"],
  "analysis": "Root-cause analysis grounded in evidence.",
  "remediation_tips": [
    "Actionable design/code fix 1",
    "Actionable design/code fix 2",
    "Actionable design/code fix 3"
  ],
  "evidence_summary": "Concise command/status/log summary for frontend-design context."
}
```

Guidance quality requirement on FAIL:

- remediation tips must be specific, not generic
- include what changed, what broke, and what should be preserved
- include regression warnings when a previously passing gate now fails
- continue loop iterations until verdict is `PASS` or an external blocker requires user input
