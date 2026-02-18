# FAILURE_JOURNEY

Purpose: capture dead ends and hard lessons so future tasks do not repeat them.

## Entry Format
1. Date and task id.
2. Tried X.
3. Failed Y.
4. Doing Z.
5. Preventive rule added.

## Entries

### 2026-02-12 | 07.1-governance-baseline-dry-run
1. Tried X: enforce full governance baseline in one pass without task-scoped evidence templates.
2. Failed Y: report schema ambiguity caused inconsistent evidence fields.
3. Doing Z: standardized four report templates and strict `N/A` policy for non-applicable fields.
4. Preventive rule added: no task closes without exact four reports and non-empty required fields.
5. Anti-drift handling: if report schema drifts from templates, stop closure and re-bootstrap from `reports/templates/`.
6. Anti-stubborn handling: after two failed closure attempts on the same task, trigger scope reset and checkpoint re-plan.
