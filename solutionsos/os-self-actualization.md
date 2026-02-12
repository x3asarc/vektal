# OS Self-Actualization Playbook

## Purpose
Define how this repository's governance OS improves itself over time without losing delivery speed.

## Operating Intent
1. Keep `.planning/ROADMAP.md` and `.planning/STATE.md` as canonical truth.
2. Keep execution evidence complete and auditable.
3. Convert recurring friction into explicit system upgrades, not one-off fixes.

## Maturity Model

### Level 0: Ad-Hoc
- Behavior: work executes, but quality controls are inconsistent.
- Signal: missing report fields, inconsistent task closure.

### Level 1: Controlled
- Behavior: required reports and gates exist for each task.
- Signal: gate board remains `GREEN` with traceable evidence links.

### Level 2: Adaptive
- Behavior: issues found in reviews become codified standards and checks.
- Signal: repeated issue classes trend down across tasks.

### Level 3: Self-Actualizing
- Behavior: governance actively predicts likely failure modes before execution.
- Signal: pre-flight checks catch most structural/integrity issues before implementation.

## Self-Actualization Loop

### 1) Pre-Execution Calibration
- Inputs: `.planning/STATE.md`, `.planning/ROADMAP.md`, open plan/task.
- Action: identify highest-risk failure classes for the upcoming task.
- Output: explicit guardrails for this task.

### 2) In-Flight Evidence Discipline
- Inputs: task execution artifacts and commit history.
- Action: enforce four-report completion with non-empty required fields.
- Output: valid evidence set for merge decisions.

### 3) Post-Execution Learning Capture
- Inputs: review findings and integrity exceptions.
- Action: classify findings into:
  - rule gap
  - process gap
  - tooling gap
- Output: backlog item with owner, trigger, and verification evidence.

## Evidence Requirements
- Every completed task must have:
  - `self-check.md`
  - `review.md`
  - `structure-audit.md`
  - `integrity-audit.md`
- Review findings must include severity and actionable remediation.
- Integrity checks must explicitly record `N/A` when non-applicable.

## Backlog (Prioritized)

1. Governance Drift Scanner
- Type: tooling gap
- Trigger: state/roadmap mismatch or stale gate evidence paths
- Owner: execution agent
- Evidence: scanner output attached in `reports/meta/`
- Target: detect canonical file drift before phase execution starts

2. Review Finding Taxonomy
- Type: process gap
- Trigger: recurring "manual blind-ordering proof" or similar low-severity repeats
- Owner: reviewer role
- Evidence: monthly tally of finding categories with trend
- Target: reduce repeated low-value review noise and increase signal quality

3. Checkpoint Escalation Matrix
- Type: rule gap
- Trigger: human checkpoints that stall execution
- Owner: planning agent
- Evidence: checkpoint response time and closure reason tracking
- Target: deterministic action paths for approve/rework/defer

4. Quick-Task Governance Bridge
- Type: process gap
- Trigger: quick tasks touching governance artifacts
- Owner: quick-task executor
- Evidence: quick task table row + summary one-liner linked in STATE
- Target: ensure quick tasks stay auditable and discoverable in canonical state

## Execution Notes for Current Milestone
- Current phase context: Phase 7 execution active.
- Immediate usage: apply this loop to upcoming frontend integration work and any governance-sensitive quick tasks.
- Success indicator: fewer unresolved blockers and cleaner checkpoint handoffs.
