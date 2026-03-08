---
name: verify-phase
description: Use when user wants to Run progressive verification checkpoints for a GSD phase
disable-model-invocation: true
---

# Progressive Phase Verification

Run all 4 progressive verification checkpoints for a phase and trigger auto-improvement if failures detected.

## Usage

```
/verify-phase <phase-id>
```

## Examples

```bash
# Verify Phase 14
/verify-phase 14

# Verify Phase 13.2
/verify-phase 13.2
```

## What it does

1. **Checkpoint 1**: Validates discussion is complete
   - Checks for required sections (domain, decisions, specifics)
   - Verifies ≥3 decisions documented
   - Checks success criteria defined

2. **Checkpoint 2**: Validates research depth
   - Checks research file ≥2000 characters
   - Counts dependencies mentioned
   - Verifies standard patterns referenced

3. **Checkpoint 3**: Validates plan structure
   - Checks all plans have required sections
   - Verifies test commands specified
   - Validates dependencies declared

4. **Checkpoint 4**: Validates execution
   - Runs tests for all plans in phase
   - Captures metrics (duration, pass/fail, root cause)
   - Triggers auto-improver on failures

## Output

- ✅/❌ status for each checkpoint
- Root cause analysis for failures
- Auto-improvement status (applied/escalated/pending)
- Metrics saved to `.claude/metrics/<phase>/`

## Files Created

- `.claude/metrics/<phase>/<plan>.json` - Execution metrics
- `.claude/learnings.md` - Updated with patterns
- `.claude/escalations/pending-improvements.json` - If manual review needed
- Target agent/skill files - If auto-improvements applied

## Requirements

- Phase directory must exist in `.planning/phases/<phase>*/`
- Plan files must have test commands
- Python 3 must be available for auto-improver

## See Also

- `.claude/checkpoints/` - Individual checkpoint scripts
- `.claude/auto-improver/` - Auto-improvement engine
- `/query-graph` - Query knowledge graph (Phase 14+)
