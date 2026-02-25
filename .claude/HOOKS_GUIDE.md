# Claude Code Hooks Guide

## Active Hooks

### 1. PreToolUse Runtime Guard (BLOCKING)
**Triggers:** Before every `Bash` tool command
**Script:** `scripts/governance/ensure_neo4j_runtime.py`
**Blocks:** YES - Prevents tool execution if Neo4j runtime cannot be restored

#### What It Does:
1. Ensures `neo4j` and `graphiti_core` are importable from the project runtime
2. If missing, installs pinned package specs from `requirements.txt` into the project venv
3. Fails fast if runtime cannot be repaired

### 2. PreToolUse Commit Gate (BLOCKING)
**Triggers:** Before every `git commit` command
**Script:** `scripts/governance/risk_tier_gate_enforce.py`
**Blocks:** YES - Prevents commit if checks fail

#### What It Does:
1. **Classifies your changes** by risk tier (Critical → High → Standard → Low)
2. **Runs required checks** based on tier:

| Tier | Paths | Required Checks |
|------|-------|----------------|
| **Critical** | Governance, auth, models, docker configs | All tests + integration + governance + secrets + canary |
| **High** | API routes, task routing, requirements.txt | All tests + governance + secrets |
| **Standard** | Business logic, resolution, enrichment, frontend | Unit tests + secrets |
| **Low** | Docs, scripts, tests, markdown | Secrets only |

3. **Blocks commit** if any required check fails

#### Example Output:
```
============================================================
Risk Tier Gate Enforcer
============================================================

Step 1: Classifying changed files...

Risk Tier: STANDARD
Required Checks: risk-policy-gate, backend-unit-tests, secret-lint

Matched Files:
  standard src/core/embeddings.py
  standard src/core/summary_generator.py
  low      tests/unit/test_embeddings.py

============================================================
Step 2: Running required checks...

[OK] Risk policy gate (classification)
Running: Backend unit tests (fast mode)...
[OK] Backend unit tests (fast mode) passed
Running: Secret lint...
[OK] Secret lint passed

============================================================
[OK] All checks passed - commit allowed
============================================================
```

#### If Checks Fail:
```
============================================================
[FAIL] Some checks failed - commit blocked
Fix the issues above before committing
============================================================
```

Your commit will NOT happen. Fix the issues and try again.

### 3. SessionStart Hooks (NON-BLOCKING)
**Triggers:** When you start a new Claude Code session

- `node .claude/hooks/gsd-check-update.js` - Checks for GSD updates
- `python .claude/hooks/check-pending-improvements.py` - Shows pending improvements

These are informational only and don't block anything.

### 4. PostToolUse Hook (DISABLED)
**Status:** Disabled due to Windows compatibility issues
**Previous Purpose:** Auto-checkpoint after pytest runs

This was causing "write hook error" messages and has been removed.

## Bypassing the Hook (Emergency Only)

If you need to commit urgently and the hook is blocking:

**Option 1: Skip hooks (NOT RECOMMENDED)**
```bash
git commit --no-verify -m "emergency fix"
```

**Option 2: Fix the actual issue**
- Run `python -m pytest tests/unit/ -x` to see test failures
- Fix the failing tests
- Commit normally

**Option 3: Temporarily disable**
Edit `.claude/settings.json` and set:
```json
"PreToolUse": []
```

## Configuration

All hook settings are in `.claude/settings.json`

Risk tier rules are in `risk-policy.json` at the project root.

## Testing the Hook

Test the enforcer manually:
```bash
python scripts/governance/risk_tier_gate_enforce.py
```

This shows what would happen if you committed your current staged changes.
