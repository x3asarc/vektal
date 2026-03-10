# Task Tracking Protocol (All Worker Agents)

**Applies to:** engineering-lead, design-lead, forensic-lead, infrastructure-lead, project-lead

## Purpose

Provide visual oversight of agent work-in-progress. Users should see what each agent is doing, not just wait for completion.

---

## Protocol: Simple Text Progress

**Output clear progress messages as regular text in your responses.**

### Format:
```markdown
📋 [Work Description] Plan:
  1. First task
  2. Second task
  3. Third task

⏳ [1/3] First task... ✅ Done (details)
⏳ [2/3] Second task... ✅ Done (details)
⏳ [3/3] Third task... ⚠️  Issue found (details)

✅ Complete! Summary here.
```

### Example:
```markdown
📋 Aura Health Check Plan:
  1. Check Neo4j connectivity
  2. Check health daemon status
  3. Review active Sentry issues

⏳ [1/3] Checking Neo4j connectivity... ✅ Connected (neo4j+s://5953bf18.databases.neo4j.io, 694ms)
⏳ [2/3] Checking health daemon... ⚠️  Daemon not configured
⏳ [3/3] Reviewing Sentry issues... ✅ Found 7 unresolved issues

✅ Complete! Overall status: GREEN with warnings
```

### Implementation

**Option A: Text-only (Recommended)**
Just output progress messages as text in your response. No tools, no files.

**Option B: Text + File tracking (Optional)**
Use `src.memory.task_manager` for audit trail, but ALSO output text progress:

```python
from src.memory.task_manager import create_task, update_task

# Create tasks (files only - user won't see this)
t1, _ = create_task("Check Neo4j", "Test connectivity", "Checking")
t2, _ = create_task("Check daemon", "Verify status", "Checking")

# Output progress as TEXT (user WILL see this)
# Just write it directly in your response - no special tools needed
```

Then in your text response:
```
📋 Health Check Plan:
  1. Check Neo4j connectivity
  2. Check health daemon

⏳ [1/2] Checking Neo4j... ✅ Connected
⏳ [2/2] Checking daemon... ⚠️  Not running

✅ Complete!
```

---

## Task Granularity Guidelines

**Too granular (avoid):**
- "Read file X"
- "Write line 42"
- "Call function Y"

**Just right:**
- "Query Aura for system health metrics"
- "Implement Commander pre-flight validation"
- "Run test suite and verify results"

**Too high-level (avoid):**
- "Do the work"
- "Complete the task"
- "Finish implementation"

---

## When NOT to Create Tasks

- **Commander** - Orchestration only, doesn't execute domain work
- **Watson** - Analysis/review only, no implementation
- **Bundle** - Configuration only, no execution
- **Validator** - Review only, single responsibility
- **task-observer** - Observation only, writes proposals but doesn't implement

---

## Enforcement

This protocol is **REQUIRED** for all worker agents. If you skip task tracking:
- User has no visibility into your progress
- You may be interrupted/stopped because user thinks you're stuck
- ImprovementProposal will be filed for "agent didn't use task tracking"

---

## Benefits

1. **User confidence** - They see progress, not just waiting
2. **Debugging** - If agent fails, last task shows where it got stuck
3. **Interruption recovery** - Can resume from last completed task
4. **Estimation** - Task completion rate helps estimate remaining time
5. **Transparency** - User understands what you're doing and why
