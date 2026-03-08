---
name: test-fixing
description: Use when tests are failing. Detects the root cause of test failures, distinguishes flaky from real failures, and proposes the minimal fix — to the code or the test — with evidence.
---

# Test-Fixing

## Core Principle

**Failing tests are information. Read them before touching anything.**

Never delete a test to make it pass. Never mark a test as skip without a comment explaining when it will be un-skipped.

## Process

### Step 1: Collect All Failures

Run the full test suite first. Collect all failure messages before attempting any fix.

```bash
python -m pytest tests/ -x --tb=short -q 2>&1
```

List failures:
```
FAIL tests/test_foo.py::test_bar — AssertionError: expected 3, got 4
FAIL tests/test_baz.py::test_qux — KeyError: 'user_id'
```

### Step 2: Categorize Each Failure

For each failing test, classify:

| Category | Meaning | Action |
|---|---|---|
| `CODE_BUG` | Test is correct, implementation is wrong | Fix the code |
| `TEST_BUG` | Test has wrong expectation or stale fixture | Fix the test |
| `FLAKY` | Passes sometimes, fails sometimes (timing/state) | Fix isolation |
| `MISSING_FIXTURE` | Test needs data/setup that doesn't exist | Add fixture |
| `SCOPE_CREEP` | Test tests something that changed intentionally | Update test + comment why |

### Step 3: Diagnose Root Cause

For each `CODE_BUG`:
- Run the single test with verbose output
- Read the full stack trace (not just the last line)
- Use root-cause-tracing if the error is deep in the call chain
- Find the exact line that produces the wrong value

For each `TEST_BUG`:
- Verify the test expectation against the current spec
- Only update the test if the spec explicitly changed

### Step 4: Minimal Fix

Write the **smallest possible change** that makes the test pass:
- No refactoring during test-fixing (separate concern)
- No adding features to fix a test
- No changing test expectations without spec evidence

### Step 5: Verify

```bash
# Run fixed test first
python -m pytest tests/path/to/test.py::test_name -v

# Then full suite — no new failures introduced
python -m pytest tests/ -x --tb=short -q
```

### Step 6: Output

```
TEST-FIX REPORT:
  Total failures: [N]
  Fixed: [N] (CODE_BUG: N, TEST_BUG: N, MISSING_FIXTURE: N)
  Deferred: [N] (reason: [flaky/scope/needs spec clarification])

Changes made:
  [file:line] — [what changed and why]

Remaining failures:
  [test name] — [why deferred]
```

## Rules

- Never delete a test
- Never `pytest.mark.skip` without a `# TODO: re-enable when [condition]` comment
- Never change test expectations without citing the spec change that justifies it
- If fixing one test breaks another — stop, report, ask
