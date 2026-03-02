# AI Memory System with Hooks

**Status**: Design complete, ready to implement
**Priority**: P2 (after health routing completion)
**Effort**: ~3 hours

---

## Objective

Create a multi-tier memory system for AI assistants (Claude, Gemini, Codex) that:
1. **Working Memory**: Session-scoped cache (fast, ephemeral)
2. **Short-Term Memory**: Task/day-scoped (persists hours-days)
3. **Long-Term Memory**: Project-scoped (persists forever)
4. **Hooks**: Auto-update on events (SessionEnd, TaskComplete, etc.)

---

## Architecture

```
┌────────────────────────────────────────────────────┐
│ WORKING MEMORY (Session Cache)                     │
│ Location: .memory/working/{session_id}.json        │
│ Scope: Single conversation session                 │
│ TTL: Until session ends                            │
│ Size: ~50KB (small, fast)                          │
│                                                     │
│ Contains:                                           │
│ - Current task context                             │
│ - Files recently read/modified                     │
│ - Recent commands executed                         │
│ - Active plan being followed                       │
│ - Session timestamp + metadata                     │
└────────────────────────────────────────────────────┘
          ↓ Promoted on SessionEnd hook
┌────────────────────────────────────────────────────┐
│ SHORT-TERM MEMORY (Task/Day Cache)                 │
│ Location: .memory/short-term/{date}.jsonl          │
│ Scope: Daily activity                              │
│ TTL: 7-30 days (configurable)                      │
│ Size: ~500KB per day                               │
│                                                     │
│ Contains:                                           │
│ - Completed tasks summary                          │
│ - Decisions made (with rationale)                  │
│ - Patterns discovered                              │
│ - Learnings from failures                          │
│ - Key insights                                     │
└────────────────────────────────────────────────────┘
          ↓ Synthesized on PhaseComplete hook
┌────────────────────────────────────────────────────┐
│ LONG-TERM MEMORY (Project Knowledge)               │
│ Location: .memory/long-term/                       │
│ Scope: Entire project lifetime                     │
│ TTL: Forever (versioned)                           │
│ Size: Unlimited                                    │
│                                                     │
│ Contains:                                           │
│ - Project architecture evolution                   │
│ - Architectural decisions (ADRs)                   │
│ - Recurring patterns/anti-patterns                 │
│ - Team preferences/conventions                     │
│ - Success/failure case studies                     │
└────────────────────────────────────────────────────┘
```

---

## Memory Schemas

### Working Memory Schema
```json
{
  "session_id": "session-uuid",
  "started_at": "2026-03-03T00:00:00Z",
  "updated_at": "2026-03-03T01:23:45Z",
  "context": {
    "current_task": "Complete health routing system",
    "active_plan": ".planning/phases/15-self-healing-dynamic-scripting/health-to-remediation-routing-plan.md",
    "phase": "15-self-healing",
    "branch": "master"
  },
  "recent_files": [
    {"path": "src/graph/orchestrate_healers.py", "action": "read", "timestamp": "..."},
    {"path": "scripts/daemons/health_monitor.py", "action": "modified", "timestamp": "..."}
  ],
  "recent_commands": [
    {"cmd": "git status", "timestamp": "...", "success": true},
    {"cmd": "pytest tests/daemons/", "timestamp": "...", "success": true}
  ],
  "insights": [
    "Health monitor detects issues but only auto-heals Sentry - gap identified",
    "Need 2 new remediators: dependency and neo4j_health"
  ],
  "next_steps": [
    "Create dependency_remediator.py",
    "Update health_monitor.py with routing triggers"
  ]
}
```

### Short-Term Memory Schema (JSONL)
```json
{"timestamp": "2026-03-03T00:00:00Z", "type": "task_completed", "task": "Health daemon system", "outcome": "success", "learnings": ["PreToolUse hooks can be 3000x faster with caching", "Daemon pattern scales well"]}
{"timestamp": "2026-03-03T01:00:00Z", "type": "decision", "decision": "Use daemon+cache instead of blocking hooks", "rationale": "99.97% performance gain, no conversation interruption", "alternatives_considered": ["Async hooks", "Lazy loading"]}
{"timestamp": "2026-03-03T02:00:00Z", "type": "pattern_discovered", "pattern": "Sentry integration works but Neo4j/deps don't auto-heal", "frequency": 1, "impact": "high"}
```

### Long-Term Memory Structure
```
.memory/long-term/
├── architecture/
│   ├── decisions/
│   │   ├── 001-daemon-based-health-monitoring.md
│   │   ├── 002-three-tier-classification.md
│   │   └── ADR-template.md
│   ├── diagrams/
│   │   ├── health-to-remediation-flow.mmd
│   │   └── overall-architecture.mmd
│   └── evolution/
│       ├── phase-14-knowledge-graph.md
│       └── phase-15-self-healing.md
├── patterns/
│   ├── success/
│   │   ├── fast-cache-based-hooks.md
│   │   ├── universal-remediator-pattern.md
│   │   └── three-tier-classification.md
│   └── anti-patterns/
│       ├── blocking-pretooluse-hooks.md
│       └── missing-verification-loops.md
├── preferences/
│   ├── code-style.md
│   ├── testing-approach.md
│   └── documentation-standards.md
└── index.json
```

---

## Hook System

### Hook Types

#### 1. SessionStart Hook
**Trigger**: AI session begins
**Action**:
- Load working memory from last session (if <24h old)
- Load today's short-term memory
- Load relevant long-term context
- Display context summary to AI

**Implementation**: `.claude/hooks/session-start-memory.py`

```python
"""Load memory context at session start."""
import json
from pathlib import Path
from datetime import datetime, timedelta

MEMORY_DIR = Path(__file__).resolve().parents[2] / ".memory"

def load_working_memory():
    """Load most recent session's working memory if fresh."""
    working_dir = MEMORY_DIR / "working"
    if not working_dir.exists():
        return None

    # Find most recent session
    sessions = sorted(working_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not sessions:
        return None

    latest = sessions[0]
    age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600

    # Only load if <24h old
    if age_hours < 24:
        return json.loads(latest.read_text())
    return None

def load_short_term_memory():
    """Load today's short-term memory."""
    today = datetime.now().strftime("%Y-%m-%d")
    stm_file = MEMORY_DIR / "short-term" / f"{today}.jsonl"

    if not stm_file.exists():
        return []

    entries = []
    for line in stm_file.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries

def main():
    working = load_working_memory()
    short_term = load_short_term_memory()

    if working:
        print(f"[Memory] Restored session context: {working['context']['current_task']}")
        if working.get('next_steps'):
            print(f"[Memory] Suggested next steps:")
            for step in working['next_steps']:
                print(f"  - {step}")

    if short_term:
        print(f"[Memory] Today's activity: {len(short_term)} events")

if __name__ == "__main__":
    main()
```

#### 2. SessionEnd Hook
**Trigger**: AI session ends (gracefully)
**Action**:
- Save working memory to `.memory/working/{session_id}.json`
- Extract key insights and append to short-term memory
- Suggest next steps for next session

**Implementation**: `.claude/hooks/session-end-memory.py`

```python
"""Save session context at session end."""
import json
from pathlib import Path
from datetime import datetime
import uuid

MEMORY_DIR = Path(__file__).resolve().parents[2] / ".memory"

def save_working_memory(context):
    """Save current session working memory."""
    working_dir = MEMORY_DIR / "working"
    working_dir.mkdir(parents=True, exist_ok=True)

    session_id = str(uuid.uuid4())[:8]
    session_file = working_dir / f"session-{session_id}.json"

    memory = {
        "session_id": session_id,
        "started_at": context.get("started_at", datetime.now().isoformat()),
        "ended_at": datetime.now().isoformat(),
        "context": context.get("context", {}),
        "recent_files": context.get("recent_files", []),
        "insights": context.get("insights", []),
        "next_steps": context.get("next_steps", [])
    }

    session_file.write_text(json.dumps(memory, indent=2))
    print(f"[Memory] Session saved: {session_id}")

def append_short_term_memory(insights):
    """Append session insights to daily short-term memory."""
    today = datetime.now().strftime("%Y-%m-%d")
    stm_dir = MEMORY_DIR / "short-term"
    stm_dir.mkdir(parents=True, exist_ok=True)
    stm_file = stm_dir / f"{today}.jsonl"

    with stm_file.open("a") as f:
        for insight in insights:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "session_insight",
                "content": insight
            }
            f.write(json.dumps(entry) + "\n")

# Hook integration would collect context from environment
```

#### 3. TaskComplete Hook
**Trigger**: Task marked as completed (via TaskUpdate or commit)
**Action**:
- Extract learnings from task
- Append to short-term memory
- Update long-term patterns if recurring

**Implementation**: `.claude/hooks/task-complete-memory.py`

```python
"""Extract learnings when task completes."""
import json
from pathlib import Path
from datetime import datetime

def extract_task_learnings(task_context):
    """Extract learnings from completed task."""
    learnings = {
        "timestamp": datetime.now().isoformat(),
        "type": "task_completed",
        "task": task_context.get("task_name"),
        "outcome": task_context.get("outcome", "success"),
        "duration_minutes": task_context.get("duration"),
        "files_modified": task_context.get("files_modified", []),
        "tests_added": task_context.get("tests_added", 0),
        "learnings": task_context.get("learnings", []),
        "challenges": task_context.get("challenges", [])
    }

    # Append to today's short-term memory
    today = datetime.now().strftime("%Y-%m-%d")
    stm_file = Path(".memory/short-term") / f"{today}.jsonl"
    stm_file.parent.mkdir(parents=True, exist_ok=True)

    with stm_file.open("a") as f:
        f.write(json.dumps(learnings) + "\n")

    print(f"[Memory] Task learnings saved: {task_context.get('task_name')}")
```

#### 4. PhaseComplete Hook
**Trigger**: Phase marked as complete in roadmap
**Action**:
- Synthesize short-term memories into long-term architecture docs
- Create ADR (Architecture Decision Record) if applicable
- Update pattern library

**Implementation**: `.claude/hooks/phase-complete-memory.py`

```python
"""Synthesize phase learnings into long-term memory."""
import json
from pathlib import Path
from datetime import datetime

def synthesize_phase_memories(phase_name, start_date, end_date):
    """Synthesize all short-term memories from phase into long-term docs."""

    # Collect all short-term memories from phase duration
    stm_dir = Path(".memory/short-term")
    memories = []

    # Parse all daily files in date range
    for stm_file in stm_dir.glob("*.jsonl"):
        date_str = stm_file.stem
        # Filter by date range...
        for line in stm_file.read_text().splitlines():
            if line.strip():
                memories.append(json.loads(line))

    # Categorize by type
    decisions = [m for m in memories if m.get("type") == "decision"]
    patterns = [m for m in memories if m.get("type") == "pattern_discovered"]
    learnings = [m for m in memories if m.get("type") in ["task_completed", "session_insight"]]

    # Create architecture evolution document
    ltm_dir = Path(".memory/long-term/architecture/evolution")
    ltm_dir.mkdir(parents=True, exist_ok=True)

    doc_path = ltm_dir / f"{phase_name}.md"

    # Generate markdown doc from memories
    # (Implementation would format memories into structured doc)

    print(f"[Memory] Phase synthesis complete: {phase_name}")
```

---

## Memory Operations

### 1. Write to Working Memory
```python
from memory_manager import WorkingMemory

memory = WorkingMemory()
memory.update_context("current_task", "Implement dependency remediator")
memory.add_insight("Remediators need pip install + import verification")
memory.add_next_step("Create dependency_remediator.py")
memory.track_file("src/graph/remediators/dependency_remediator.py", "created")
```

### 2. Query Short-Term Memory
```python
from memory_manager import ShortTermMemory

stm = ShortTermMemory()
recent_decisions = stm.query(type="decision", last_n_days=7)
patterns = stm.query(type="pattern_discovered", impact="high")
```

### 3. Update Long-Term Memory
```python
from memory_manager import LongTermMemory

ltm = LongTermMemory()
ltm.create_adr(
    title="Daemon-Based Health Monitoring",
    decision="Use background daemon + cache instead of blocking hooks",
    rationale="99.97% performance improvement",
    alternatives=["Async hooks", "Lazy loading"],
    consequences="Requires daemon management but eliminates UX lag"
)
```

---

## Cache-Like Working Memory

Working memory acts as a **session cache**:

1. **Fast reads**: In-memory during session, ~1ms access
2. **Auto-expire**: Cleared after 24h of inactivity
3. **Lazy load**: Only loads on SessionStart if recent
4. **Context preservation**: Maintains task context across interruptions

**Use cases**:
- "Continue where I left off"
- "What was I working on yesterday?"
- "What files did I modify this session?"
- "What insights have I discovered today?"

---

## Integration with Existing Systems

### 1. Hook Configuration (.claude/settings.json)
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/session-start-memory.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/session-end-memory.py"
          }
        ]
      }
    ]
  }
}
```

### 2. Task System Integration
When `TaskUpdate(status="completed")` is called:
- Trigger `task-complete-memory.py` hook
- Extract task context from TaskGet
- Save learnings to short-term memory

### 3. GSD Integration
When phase completes via `/gsd:execute-phase`:
- Trigger `phase-complete-memory.py` hook
- Synthesize all phase activities
- Generate architecture evolution doc

---

## Directory Structure

```
.memory/
├── working/
│   ├── session-abc123.json
│   ├── session-def456.json
│   └── README.md
├── short-term/
│   ├── 2026-03-01.jsonl
│   ├── 2026-03-02.jsonl
│   ├── 2026-03-03.jsonl
│   └── README.md
├── long-term/
│   ├── architecture/
│   │   ├── decisions/
│   │   ├── diagrams/
│   │   └── evolution/
│   ├── patterns/
│   │   ├── success/
│   │   └── anti-patterns/
│   ├── preferences/
│   └── index.json
└── README.md
```

---

## Implementation Roadmap

### Phase 1: Core Memory Manager (1 hour)
- Create `src/memory/memory_manager.py`
- Implement WorkingMemory, ShortTermMemory, LongTermMemory classes
- Schema validation
- File I/O operations

### Phase 2: Hooks (1 hour)
- SessionStart hook: `.claude/hooks/session-start-memory.py`
- SessionEnd hook: `.claude/hooks/session-end-memory.py`
- TaskComplete hook: `.claude/hooks/task-complete-memory.py`
- Update settings.json

### Phase 3: Integration (1 hour)
- Integrate with Task system
- Integrate with GSD phases
- Create CLI commands: `/memory show`, `/memory query`, `/memory clear`

### Phase 4: Testing & Documentation
- Unit tests for memory manager
- Integration tests for hooks
- Update CLAUDE.md with memory usage
- Example queries and workflows

---

## Success Criteria

1. ✅ Working memory persists across session restarts (<24h)
2. ✅ Short-term memory captures daily activity (JSONL format)
3. ✅ Long-term memory accumulates architectural knowledge
4. ✅ Hooks auto-trigger on SessionStart, SessionEnd, TaskComplete
5. ✅ Memory queries work: "What did I work on yesterday?"
6. ✅ Cache-like performance: Working memory <1ms reads
7. ✅ Auto-cleanup: Working memory expires after 24h

---

## Future Enhancements

1. **Semantic search**: Query memories with natural language
2. **Knowledge graph integration**: Link memories to code entities
3. **Pattern mining**: Auto-detect recurring patterns from short-term memory
4. **Similarity detection**: "Have I solved this before?"
5. **Multi-agent memory sharing**: Gemini can see Claude's learnings
6. **Memory compression**: Summarize old short-term memories into long-term
7. **Conflict resolution**: Handle concurrent sessions writing to same memory

---

## Notes

- Working memory is **session-specific** - each AI conversation gets own cache
- Short-term memory is **daily** - all activity in one day goes to one file
- Long-term memory is **project-wide** - shared across all AI assistants
- Hooks are **best-effort** - if they fail, don't block the session
- Memory is **additive** - never delete, only append/archive

---

**Ready to implement when you are!**

Start with Phase 1 (core memory manager) to get the foundation working.
