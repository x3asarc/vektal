# Progressive Verification MVP - Quick Start Guide

**Status:** Ready to use NOW (before Phase 14)
**Created:** 2026-02-20

---

## What You Just Got

✅ **4 Checkpoint Scripts** - Validate discussion, research, planning, execution
✅ **Auto-Improvement Engine** - Detects patterns and auto-fixes failures
✅ **Verifier Agent** - Validates changes before auto-applying
✅ **verify-phase Skill** - Run all checkpoints with one command
✅ **Hooks** - SessionStart (pending improvements), PreToolUse (governance gate)

---

## Test It RIGHT NOW (5 minutes)

### 1. Test Checkpoint 4 on Existing Phase

```bash
# Run checkpoint on Phase 13.2, Plan 01
.claude/checkpoints/checkpoint_4_execution.sh 13.2 13.2-01

# Check metrics were captured
cat .claude/metrics/13.2/13.2-01.json
```

**Expected:** Either ✅ PASS (tests passed) or ❌ FAIL (metrics + root cause captured)

---

### 2. Run Full Verification on Phase 13.2

```bash
# Run all 4 checkpoints
bash .claude/skills/verify-phase/verify.sh 13.2

# Or if you have the skill registered:
/verify-phase 13.2
```

**Expected:** See all checkpoints run in sequence, metrics saved

---

### 3. Trigger Auto-Improver (Simulate Failure)

```bash
# Create a fake failure metrics file
mkdir -p .claude/metrics/test
cat > .claude/metrics/test/test-01.json <<EOF
{
  "phase": "test",
  "plan": "test-01",
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": 45,
  "test_result": "FAIL",
  "tests_passed": 0,
  "tests_failed": 3,
  "exit_code": 1,
  "root_cause": "missing_dependency:sentry-sdk",
  "suggested_fix": "Add sentry-sdk to requirements.txt",
  "test_command": "pytest tests/"
}
EOF

# Trigger auto-improver manually
python .claude/auto-improver/on_execution_complete.py .claude/metrics/test/test-01.json
```

**Expected:**
- "No pattern detected" (first occurrence)
- Entry added to `.claude/learnings.md`

---

### 4. Create Pattern (3+ Similar Failures)

```bash
# Add 2 more similar failures
for i in 02 03; do
  cat > .claude/metrics/test/test-${i}.json <<EOF
{
  "phase": "test",
  "plan": "test-${i}",
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": 45,
  "test_result": "FAIL",
  "tests_passed": 0,
  "tests_failed": 3,
  "exit_code": 1,
  "root_cause": "missing_dependency:sentry-sdk",
  "suggested_fix": "Add sentry-sdk to requirements.txt",
  "test_command": "pytest tests/"
}
EOF
done

# Now create 4th failure - should trigger pattern detection!
cat > .claude/metrics/test/test-04.json <<EOF
{
  "phase": "test",
  "plan": "test-04",
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": 45,
  "test_result": "FAIL",
  "tests_passed": 0,
  "tests_failed": 3,
  "exit_code": 1,
  "root_cause": "missing_dependency:sentry-sdk",
  "suggested_fix": "Add sentry-sdk to requirements.txt",
  "test_command": "pytest tests/"
}
EOF

# Trigger auto-improver
python .claude/auto-improver/on_execution_complete.py .claude/metrics/test/test-04.json
```

**Expected:**
- "Pattern found: 4 similar failures"
- "Confidence: 40%"
- Auto-improvement applied to `.claude/agents/gsd-executor.md` or escalated
- Check: `tail .claude/agents/gsd-executor.md` or `cat .claude/escalations/pending-improvements.json`

---

### 5. Check SessionStart Hook

```bash
# Restart Claude Code session or manually run:
python .claude/hooks/check-pending-improvements.py
```

**Expected:** If any improvements escalated, you'll see a summary

---

## Real Usage (Production)

### On Every Phase Execution

```bash
# After completing a phase, run verification
/verify-phase 14

# This will:
# 1. Validate discussion/research/planning
# 2. Run tests for all plans
# 3. Capture metrics
# 4. Auto-improve if failures found
# 5. Build historical data for patterns
```

### Monitoring

```bash
# Check metrics captured
ls -la .claude/metrics/

# Check learnings accumulated
tail -20 .claude/learnings.md

# Check pending improvements
cat .claude/escalations/pending-improvements.json

# Check auto-improver log
tail -f /tmp/auto-improver.log
```

---

## What Happens Over Time

### Week 1: Building Baseline

- Checkpoints run, metrics captured
- Failures logged to learnings.md
- No patterns yet (need ≥3 similar failures)

### Week 2-3: Patterns Emerge

- 3+ similar failures detected
- Auto-improvements proposed
- Some auto-applied (confidence ≥0.6)
- Some escalated (confidence <0.6)

### Month 1: System Learning

- Common patterns auto-fixed
- Failure rate declining
- Agents/skills improving automatically
- learnings.md promoted to CLAUDE.md

### Month 3: Self-Optimizing

- Rarely fails on same issue twice
- Auto-improvements apply ≥80% of time
- System continuously getting smarter

---

## Install MCP Servers (Recommended)

### 1. context7 (CRITICAL - Do First)

```bash
claude mcp add context7
```

**Why:** Live docs for Flask, Neo4j, Next.js, OpenAI - prevents hallucinations

**Use:** Auto-activated when Claude needs library docs

---

### 2. Sentry (HIGH PRIORITY)

```bash
claude mcp add sentry
# Follow prompts to add Sentry DSN
```

**Why:** Error tracking for Celery tasks, auto-improver failures, CI issues

**Use:**
```
You: "Show Sentry errors from last hour"
You: "Why did auto-improver fail on Phase 14?"
```

---

### 3. PostgreSQL (MEDIUM)

```bash
claude mcp add postgres
# Configure with docker-compose PostgreSQL credentials
```

**Why:** Direct DB inspection for debugging

**Use:**
```
You: "Show last 10 enrichment_runs"
You: "Query assistant_verification_events where status=FAIL"
```

---

## File Structure Created

```
.claude/
├── checkpoints/
│   ├── checkpoint_1_discussion.sh     ✅ Created
│   ├── checkpoint_2_research.sh       ✅ Created
│   ├── checkpoint_3_plan.sh           ✅ Created
│   └── checkpoint_4_execution.sh      ✅ Created
├── auto-improver/
│   ├── on_execution_complete.py       ✅ Created
│   ├── pattern_detector_file_based.py ✅ Created
│   └── README.md                      ✅ Created
├── agents/
│   └── change-verifier.md             ✅ Created
├── skills/
│   └── verify-phase/
│       ├── SKILL.md                   ✅ Created
│       └── verify.sh                  ✅ Created
├── hooks/
│   └── check-pending-improvements.py  ✅ Created
├── metrics/                           📁 Auto-created
├── escalations/                       📁 Auto-created
├── settings.json                      ✅ Updated
└── PROGRESSIVE_VERIFICATION_QUICKSTART.md  ✅ This file
```

---

## Next Steps

### After MVP Works (Week 2-3)

Update Phase 14 context with learnings:

1. How many patterns detected?
2. What was the success rate of auto-improvements?
3. Which root causes were most common?
4. How long did file-based pattern detection take?

Then plan Phase 14 with real data to inform:
- Knowledge graph schema design
- Vector embedding strategy
- Graph query optimization priorities

### After Phase 14 Complete

Upgrade to graph-based pattern detection:
- Replace `pattern_detector_file_based.py`
- Add PostToolUse hook (graph updates)
- Add query-graph skill
- <100ms pattern detection!

---

## Troubleshooting

### "Checkpoint script not found"

```bash
# Make sure scripts are executable
chmod +x .claude/checkpoints/*.sh
chmod +x .claude/skills/verify-phase/verify.sh
```

### "No such file or directory: python"

```bash
# Use python3 explicitly
# Edit on_execution_complete.py line 1:
#!/usr/bin/env python3
```

### "Pattern detector failed"

```bash
# Run manually to see error:
python .claude/auto-improver/pattern_detector_file_based.py \
  .claude/metrics/test/test-01.json
```

---

## Questions?

- Full specification: `.planning/enhancements/GSD_PROGRESSIVE_VERIFICATION.md`
- Auto-improver docs: `.claude/auto-improver/README.md`
- Checkpoint docs: See individual script comments

---

**Ready to start?** Run the 5-minute test above, then use `/verify-phase` on your next phase execution!
