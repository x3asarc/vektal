# Auto-Improvement Engine (MVP)

Progressive Verification auto-improvement system. Analyzes checkpoint failures and auto-applies fixes when patterns are detected.

## Architecture

```
Checkpoint fails
  → on_execution_complete.py (orchestrator)
    → pattern_detector_file_based.py (find similar failures)
      → Proposal generated
        → Verifier agent validates
          → Auto-apply if approved
          → Escalate if rejected
```

## Files

### `on_execution_complete.py`
Main orchestrator. Runs after every checkpoint_4_execution.sh failure.

**Triggers:** Automatically (background) when checkpoint 4 fails
**What it does:**
1. Loads failure metrics
2. Calls pattern detector
3. Generates improvement proposal
4. Calls verifier agent
5. Auto-applies or escalates

### `pattern_detector_file_based.py`
Scans `.claude/metrics/` for similar historical failures.

**MVP Mode:** File-based (5-10s)
**Phase 14:** Upgrade to graph-based (<100ms)

**Pattern threshold:** ≥3 similar failures = pattern detected

### Outputs

**Success:**
- Updates target file (agent/skill/learnings.md)
- Appends metrics with fix for future pattern detection
- Logs to `.claude/learnings.md`

**Escalation:**
- Saves to `.claude/escalations/pending-improvements.json`
- User reviews on next SessionStart

## Usage

### Automatic (Recommended)

Checkpoint failures automatically trigger auto-improver:

```bash
.claude/checkpoints/checkpoint_4_execution.sh 14 14-01
# If fails, auto-improver runs in background automatically
```

### Manual

```bash
python .claude/auto-improver/on_execution_complete.py .claude/metrics/14/14-01.json
```

## Upgrade Path

### Phase 14: Graph-Based Pattern Detection

Replace `pattern_detector_file_based.py` with `pattern_detector_graph_based.py`:

```python
# Query knowledge graph instead of file scanning
similar = graph.query("""
    MATCH (cp:Checkpoint {status: 'FAIL'})
    WHERE cp.root_cause STARTS WITH $root_cause_type
    RETURN cp, count(cp) as occurrences
    ORDER BY occurrences DESC
""")
```

**Result:** <100ms pattern detection (vs 5-10s file-based)

### Phase 15: Autonomous Refactoring

Add predictive analysis and self-healing:

```python
# Predict failures BEFORE execution
prediction = predict_failure_risk(discussion, research, plan)
if prediction["risk_score"] > 0.6:
    apply_preemptive_fixes(prediction["suggestions"])
```

## Configuration

### Confidence Thresholds

**MVP Mode:** ≥0.6 confidence for auto-apply
**Phase 14+:** ≥0.8 confidence for auto-apply

Adjust in `on_execution_complete.py`:

```python
if all(checks.values()) and confidence >= 0.6:  # Lower for MVP
    return {"verdict": "APPROVE", ...}
```

### Target Files

Auto-improver updates these files based on root cause:

- `missing_dependency` → `.claude/agents/gsd-executor.md`
- `import_error` → `.claude/agents/gsd-planner.md`
- Generic patterns → `.claude/learnings.md`

Customize in `generate_improvement()` function.

## Monitoring

### Check auto-improver logs:

```bash
tail -f /tmp/auto-improver.log
```

### Check pending improvements:

```bash
cat .claude/escalations/pending-improvements.json
```

### Check applied improvements:

```bash
git log --grep="Auto-improvement"
```

## Troubleshooting

### Auto-improver not triggering

1. Check checkpoint_4_execution.sh created metrics file:
   ```bash
   ls .claude/metrics/14/
   ```

2. Check auto-improver script exists:
   ```bash
   ls .claude/auto-improver/on_execution_complete.py
   ```

3. Check background process running:
   ```bash
   ps aux | grep on_execution_complete
   ```

### Pattern detection failing

1. Check historical metrics exist:
   ```bash
   find .claude/metrics -name "*.json" | wc -l
   # Need ≥3 similar failures for pattern
   ```

2. Run pattern detector manually:
   ```bash
   python .claude/auto-improver/pattern_detector_file_based.py \
     .claude/metrics/14/14-01.json
   ```

### Improvements not applying

1. Check verifier verdict:
   - Look at escalations file
   - Check confidence threshold

2. Check file permissions:
   ```bash
   ls -la .claude/agents/
   # Files should be writable
   ```

## See Also

- `.claude/checkpoints/` - Checkpoint scripts
- `.claude/skills/verify-phase/` - Run all checkpoints
- `.planning/enhancements/GSD_PROGRESSIVE_VERIFICATION.md` - Full specification
