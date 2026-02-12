# Governance Validation Scripts

## Validate a task gate set

```bash
python scripts/governance/validate_governance.py --phase 07 --task 07.1-governance-baseline-dry-run
```

Checks:
1. Required governance artifacts exist.
2. Task report directory exists with exactly four required report files.
3. Required report fields are present and non-empty.
4. Blind-review timestamp ordering is valid.
5. Governance markers exist in canonical roadmap/state files.

