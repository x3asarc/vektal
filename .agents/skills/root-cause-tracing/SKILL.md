---
name: root-cause-tracing
description: Use when errors occur deep in execution and you need to trace back through the call chain to find the original trigger. Never fix where the error appears — fix at the source.
---

# Root Cause Tracing

## Core Principle

**Trace backward through the call chain until finding the original trigger, then fix at source.**

Bugs often manifest deep in the call stack — a `git init` in the wrong directory, a file created in the wrong location. The instinct is to fix it where the error appears. That instinct is wrong.

**NEVER fix just where the error appears. Trace back to find the original trigger.**

## Process

1. **Observe the error** — read the full stack trace, not just the last line
2. **Identify the immediate cause** — what direct call produced this failure?
3. **Ask: what called this?** — trace one level up
4. **Keep tracing upward** — repeat until you reach the original decision point
5. **Fix at the original trigger** — not at the symptom layer

## Stack Trace Tips

```
Error in: component.render()
  <- called by: page.mount()
  <- called by: router.navigate()
  <- ORIGINAL TRIGGER: invalid path passed to router
```

Fix the path validation in `router.navigate()` — not `component.render()`.

## When to Use

- Error manifests far from where the bad data was created
- The same error appears in multiple places (symptom: data corruption upstream)
- Quick fixes keep recurring (symptom: patching symptoms, not cause)
- Call chain is 3+ levels deep and the immediate cause "shouldn't have happened"

## Debug Instrumentation

When the call chain isn't obvious, add temporary instrumentation at each level:

```python
import traceback
print("TRACE:", traceback.format_stack()[-5:])
```

Add this at the error site, then walk backward removing it once the source is found.

## Output Format

```
ROOT CAUSE FOUND:
  Immediate error:  [where it crashed]
  Proximate cause:  [what called the crashing function with bad data]
  Original trigger: [where the invalid state was first created]
  Fix location:     [exact file:line to patch]
  Confidence:       [HIGH | MEDIUM | LOW]
```
