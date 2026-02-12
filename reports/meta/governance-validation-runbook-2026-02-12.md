# Governance Validation Runbook (2026-02-12)

## Purpose
Define the repeatable checks to verify and validate the governance baseline implementation.

## 1) Fast gate validation (single command)
```bash
python scripts/governance/validate_governance.py --phase 07 --task 07.1-governance-baseline-dry-run
```

What it validates:
1. Required governance artifacts exist.
2. Exact four report files exist for the task.
3. Required report fields are present and non-empty.
4. Blind-review timestamp ordering is valid.
5. Governance sections exist in `.planning/ROADMAP.md` and `.planning/STATE.md`.

Expected outcome:
- `Governance validation passed.`

## 2) Evidence integrity checks
```bash
ls reports/07/07.1-governance-baseline-dry-run
```

Expected files only:
1. `self-check.md`
2. `review.md`
3. `structure-audit.md`
4. `integrity-audit.md`

## 3) Canonical state checks
```bash
rg -n "Governance Baseline v1|Phase 7 Governance Task Board" .planning/ROADMAP.md
rg -n "Governance Gate Snapshot|StructureGuardian Audit Trail|Bypass Log" .planning/STATE.md
```

Expected:
1. Governance baseline section present in roadmap.
2. Gate snapshot + audit trail + bypass log present in state.

## 4) Blind-review protocol checks
In `reports/07/07.1-governance-baseline-dry-run/review.md`, verify:
1. `pass_1_timestamp`
2. `plan_context_opened_at`
3. `pass_2_timestamp`
4. Ordering rule: `pass_1_timestamp < plan_context_opened_at <= pass_2_timestamp`

## 5) Current recorded result
Run timestamp: 2026-02-12  
Result: `PASS` for all validator checks.

