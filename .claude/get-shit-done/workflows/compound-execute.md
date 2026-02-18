<purpose>
Run one command for phase delivery with Compound Engineering OS governance:
bootstrap reports -> optional discuss -> plan -> execute -> optional verify -> governance validation.
</purpose>

<required_reading>
Read all files referenced by invoking execution_context before starting.

@./.claude/get-shit-done/workflows/discuss-phase.md
@./.claude/get-shit-done/workflows/plan-phase.md
@./.claude/get-shit-done/workflows/execute-phase.md
@./.claude/get-shit-done/workflows/verify-work.md
@solutionsos/compound-engineering-os-policy.md
@ops/governance/roles/README.md
@ops/governance/roles/phase-manager.md
@ops/governance/roles/builder.md
@ops/governance/roles/reviewer.md
@ops/governance/roles/structure-guardian.md
@ops/governance/roles/integrity-warden.md
@ops/governance/roles/context-curator.md
@scripts/governance/validate_governance.py
@reports/templates/self-check.template.md
@reports/templates/review.template.md
@reports/templates/structure-audit.template.md
@reports/templates/integrity-audit.template.md
</required_reading>

<process>
## 1) Parse Arguments and Initialize

Parse from `$ARGUMENTS`:
- phase number (required)
- `--plan <NN>` optional
- `--task <phase.n-slug>` optional
- `--skip-discuss` optional
- `--skip-verify` optional

Load base context:
```bash
INIT=$(node ./.claude/get-shit-done/bin/gsd-tools.js init phase-op "${PHASE}")
PLAN_INDEX=$(node ./.claude/get-shit-done/bin/gsd-tools.js phase-plan-index "${PHASE}")
```

If no phase provided, fail with usage hint.
If phase missing from roadmap/disk, fail and stop.

Resolve defaults:
- `PLAN_ID`: if `--plan` provided use it, else use first incomplete from `PLAN_INDEX.incomplete`; if none, use first plan in `PLAN_INDEX.plans`.
- `TASK_ID`: if `--task` provided use it, else `{PHASE}.{PLAN}-compound-execute`.

## 2) Bootstrap Governance Report Set

Use report directory:
`reports/{PHASE_PADDED}/{TASK_ID}/`

Ensure exactly four report files exist:
- `self-check.md`
- `review.md`
- `structure-audit.md`
- `integrity-audit.md`

If missing, copy from templates in `reports/templates/`.

Hydrate required header fields so validation can run:
- `Task: \`{TASK_ID}\``
- `Owner: <role>`
- `Status: \`RED\`` initially
- For `review.md`, set:
  - `pass_1_timestamp` (now)
  - `plan_context_opened_at` (now + 1 minute)
  - `pass_2_timestamp` (now + 2 minutes)
Keep ordering valid: `pass_1 < plan_context_opened_at <= pass_2`.

## 3) Execute Phase Workflows in One Run

### 3a) Discuss (optional)
If `--skip-discuss` not provided:
- Execute discuss-phase workflow for `{PHASE}` from `@./.claude/get-shit-done/workflows/discuss-phase.md`.

### 3b) Plan
- Execute plan-phase workflow for `{PHASE}` from `@./.claude/get-shit-done/workflows/plan-phase.md`.

### 3c) Execute
- Execute execute-phase workflow for `{PHASE}` from `@./.claude/get-shit-done/workflows/execute-phase.md` (includes mandatory Plan Verification Gate before wave execution).

### 3d) Verify (optional)
If `--skip-verify` not provided:
- Execute verify-work workflow for `{PHASE}` from `@./.claude/get-shit-done/workflows/verify-work.md`.

## 4) Finalize Gate Reports

After workflow execution:
- Update `self-check.md` with actual completion/test notes and set status `GREEN` if clean.
- Update `review.md` findings and merge recommendation using blocking policy:
  - block on `Critical` and `High`
  - block on `Medium` when category is `Security` or `Dependency`
- Update `structure-audit.md` with moved-file log (`N/A` if none).
- Update `integrity-audit.md` with dependency/secret evidence (`N/A` when non-applicable).
- Apply role behavior from `ops/governance/roles/*.md` when writing gate outcomes.

If any blocking condition remains, leave status `RED`, stop, and report required fixes.

## 5) Run Governance Validation

```bash
python scripts/governance/validate_governance.py --phase "${PHASE_PADDED}" --task "${TASK_ID}" --mode full-loop --plan-id "${PLAN_ID}"
```

If validation fails: stop, print failed checks, do not mark phase/gates complete.

## 6) Sync Canonical State

Update `.planning/STATE.md` governance gate snapshot for the active task with evidence links under `reports/{PHASE_PADDED}/{TASK_ID}/`.
Do additive updates only (no destructive history rewrites).

## 7) Completion Output

Report:
- phase
- task id
- report directory
- validation result
- next command:
  - `gsd:compound-execute {PHASE}` for continuation
  - or `gsd:verify-work {PHASE}` if verify was skipped
</process>
