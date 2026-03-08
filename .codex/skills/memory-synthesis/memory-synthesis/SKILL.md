---
name: memory-synthesis
description: Manages session memory synthesis, generates codebase overviews, and syncs between Letta memory blocks and repo .memory/ system. Use when ending a session, requesting a memory update, generating a project overview, or when the user says "synthesize", "update memory", "end session", or "save context".
---

# Memory Synthesis Skill

This skill handles the memory lifecycle operations for maintaining persistent context across sessions.

---

## When to Use

- User says "synthesize session" or "end session"
- User requests "update memory" or "save context"
- User asks for a "memory overview" or "project overview"
- User wants to sync memory between systems

---

## Operations

### 1. Session Synthesis (End-of-Session)

**Trigger:** User says "synthesize session" or similar

**Process:**
1. Extract insights from conversation:
   - Decisions made (with rationale)
   - Patterns discovered
   - Failures encountered and solutions
   - Files modified (with actions)
   - Pending tasks (next steps)

2. Write to `.memory/short-term/{date}.jsonl`:
   ```json
   {"timestamp": "...", "type": "session_end", "insights": [...], "decisions": [...], "files_modified": [...]}
   ```

3. Promote recurring patterns to `.memory/long-term/patterns/`:
   - If pattern appears 3+ times → create markdown doc
   - Title: `pattern-{slug}.md`

4. Update Letta memory blocks:
   - `current/session.md` → session summary
   - `current/next-steps.md` → pending actions

5. Save working memory:
   - `.memory/working/session-{id}.json`

**Output:** Summary of what was synthesized

### 2. Overview Generation

**Trigger:** User asks for "memory overview" or "project overview"

**Process:**
1. Scan `.memory/` directory structure
2. Read `.memory/long-term/index.json`
3. Read recent short-term files
4. Build hierarchical tree with links
5. Write to `docs/MEMORY_OVERVIEW.md`

**Template:**
```markdown
# Memory Overview

## High-Level Summary
[Project status, current phase, focus]

## Memory Tiers

### Working Memory (Session Cache)
- Location: `.memory/working/`
- Active Sessions: [list recent]

### Short-Term Memory (Daily Activity)
- Location: `.memory/short-term/`
- Recent Days: [links]

### Long-Term Memory (Project Knowledge)
- Architecture Decisions: [links]
- Patterns: [links]
- Evolution: [links]

## Quick Links
[Key planning and state files]
```

### 3. Letta Memory Sync

**Trigger:** User says "sync memory" or automatic at session boundaries

**Process:**
1. Read `.memory/working/latest.json`
2. Update Letta memory blocks:
   - `current/session.md` ← working memory context
   - `current/next-steps.md` ← working memory next_steps
3. Read Letta `project/memory/` blocks
4. Update `.memory/long-term/` with any new patterns/decisions

---

## Scripts

### `scripts/session-synthesize.py`

Extracts insights from the current session context.

**Usage:**
```bash
python scripts/memory/session-synthesize.py --session-id {id}
```

**Output:** JSON with extracted insights, decisions, patterns

### `scripts/generate_overview.py`

Generates `docs/MEMORY_OVERVIEW.md` from memory files.

**Usage:**
```bash
python scripts/memory/generate_overview.py
```

### `scripts/sync_letta_memory.py`

Bidirectional sync between Letta blocks and `.memory/`

**Usage:**
```bash
python scripts/memory/sync_letta_memory.py --direction letta-to-repo
python scripts/memory/sync_letta_memory.py --direction repo-to-letta
```

---

## Integration Points

- **SessionStart hook:** Loads context (automatic)
- **SessionEnd hook:** Triggers synthesis (via this skill)
- **Letta memory blocks:** `system/current/` and `system/project/memory/`
- **Repo memory:** `.memory/` 3-tier system

---

## Example Usage

**User:** "synthesize session"

**Response:**
```
## Session Synthesized

**Insights Extracted:**
- Decision: Use daemon-based health monitoring for 99.97% performance gain
- Pattern: PreToolUse hooks with caching are 3000x faster than blocking
- Files modified: 12 (scripts/memory/, src/memory/)

**Memory Updated:**
- Short-term: `.memory/short-term/2026-03-06.jsonl` (+1 entry)
- Working: `.memory/working/session-{id}.json`
- Letta: `current/session.md`, `current/next-steps.md`

**Pattern Promotion:**
- "daemon-based-hooks.md" created in `.memory/long-term/patterns/success/`

**Next Steps:**
1. Test session start restoration
2. Update CLAUDE.md with memory docs
```