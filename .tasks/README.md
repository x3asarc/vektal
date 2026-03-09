# Task Tracking System

Agents use `src/memory/task_manager.py` to provide visual oversight of their work.

## How It Works

1. **Agent spawns** → immediately creates meta-task "Plan work breakdown"
2. **Agent plans** → completes meta-task, creates specific tasks (t1, t2, t3...)
3. **Agent executes** → updates each task to in_progress → completed as it works

## Files

- `active.json` - Current task state (all tasks with status)
- Auto-created by agents, persists across sessions

## User Experience

Instead of waiting blindly, users see:
```
[completed] Plan work breakdown
[completed] Check Aura backend health
[in_progress] Verify Neo4j connection  ← Agent is here
[pending] Generate health report
```

## Implementation

See `.claude/agents/protocols/task-tracking-protocol.md` for full protocol.
