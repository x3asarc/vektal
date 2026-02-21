# GSD Progressive Verification & Continuous Improvement System

**Status:** Enhancement specification for Phase 14 & 15 integration
**Created:** 2026-02-20
**Goal:** Self-improving system that learns from every execution and auto-upgrades itself

---

## Vision: Invisible Intelligence

**What you experience:**
```
You: "Update the enrichment pipeline to handle color variants better"
[work continues normally... tests pass, commit succeeds ✓]
```

**What happens invisibly in the background:**
1. Execution completes → checkpoint runs → metrics captured
2. Auto-improver analyzes → finds pattern in knowledge graph
3. Verifier agent validates → proposed change is coherent
4. System auto-updates → CLAUDE.md, agents, hooks improved
5. Next execution → already smarter, fewer failures

**Result:** System continuously optimizes itself toward zero failures.

---

## Core Architecture: Continuous Improvement Loop

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EXECUTION (You work normally)                            │
│    - Hooks fire on every edit/commit                        │
│    - Checkpoints validate at 4 stages                       │
│    - Metrics + episodes captured automatically              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. ANALYSIS (Knowledge graph queries, instant patterns)     │
│    - Query graph for similar failures (Phase 14)            │
│    - Find patterns across ALL history (<100ms)              │
│    - Generate improvement proposals                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. VERIFICATION (Verifier agent checks coherence)           │
│    - Syntax valid? Conflicts? Reasoning sound?              │
│    - Confidence ≥ 0.8? → Auto-apply                         │
│    - Confidence < 0.8? → Escalate to user                   │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. AUTO-UPGRADE (System improves itself)                    │
│    - Update .claude/learnings.md (append pattern)           │
│    - Update CLAUDE.md (promote if repeated ≥2 times)        │
│    - Update .claude/agents/*.md (improve prompts)           │
│    - Update .claude/settings.json (add hooks)               │
│    - Update .claude/skills/* (enhance/add skills)           │
└─────────────────────────────────────────────────────────────┘
                        ↓
                (Feeds back to Step 1, now smarter)
```

---

## Part 1: Progressive Verification Checkpoints

### The Four Checkpoints (Data Collection Layer)

| Checkpoint | Stage | Validates | Speed | Data Captured |
|-----------|-------|-----------|-------|---------------|
| **CP1** | Discussion | Requirements clear | ~2s | Vagueness score, decision count |
| **CP2** | Research | Dependencies found | ~5s | Coverage %, missing deps |
| **CP3** | Planning | Plan executable | ~3s | Complexity score, waves |
| **CP4** | Execution | Tests pass | ~30s | Pass/fail, duration, root cause |

**Key innovation:** Checkpoints don't just validate - they **collect intelligence** for the improvement loop.

---

### Checkpoint 4: Execution Validation (Most Critical)

**Script:** `.claude/checkpoints/checkpoint_4_execution.sh`

```bash
#!/usr/bin/env bash
# Checkpoint 4: Execution Validation + Intelligence Collection

set -euo pipefail

PHASE=$1
PLAN=$2
PLAN_FILE=".planning/phases/${PHASE}/${PLAN}-PLAN.md"
METRICS_FILE=".claude/metrics/${PHASE}/${PLAN}.json"

echo "=== Checkpoint 4: Execution Validation ==="

# 1. Extract and run test command
test_cmd=$(grep -oP 'pytest.*|npm.*test.*' "$PLAN_FILE" | head -1)

start_time=$(date +%s)
if eval "$test_cmd" > /tmp/test_output.txt 2>&1; then
  test_result="PASS"
  exit_code=0
else
  test_result="FAIL"
  exit_code=$?
fi
end_time=$(date +%s)
duration=$((end_time - start_time))

# 2. Parse test results
if echo "$test_cmd" | grep -q pytest; then
  passed=$(grep -oP '\d+(?= passed)' /tmp/test_output.txt || echo 0)
  failed=$(grep -oP '\d+(?= failed)' /tmp/test_output.txt || echo 0)
elif echo "$test_cmd" | grep -q npm; then
  passed=$(grep -oP '\d+(?= pass)' /tmp/test_output.txt || echo 0)
  failed=$(grep -oP '\d+(?= fail)' /tmp/test_output.txt || echo 0)
fi

# 3. Root cause extraction (intelligence for auto-improver)
root_cause="unknown"
suggested_fix=""
if [ "$test_result" == "FAIL" ]; then
  if grep -q "ModuleNotFoundError" /tmp/test_output.txt; then
    missing_module=$(grep -oP "ModuleNotFoundError: No module named '\K[^']+'" /tmp/test_output.txt | head -1)
    root_cause="missing_dependency:${missing_module}"
    suggested_fix="Add ${missing_module} to requirements.txt"
  elif grep -q "ImportError" /tmp/test_output.txt; then
    root_cause="import_error"
    suggested_fix="Check file structure and imports"
  elif grep -q "AssertionError" /tmp/test_output.txt; then
    root_cause="assertion_failed"
    suggested_fix="Logic error in implementation"
  elif grep -q "SyntaxError" /tmp/test_output.txt; then
    root_cause="syntax_error"
    suggested_fix="Code has syntax errors"
  fi
fi

# 4. Save metrics (input for auto-improver)
mkdir -p "$(dirname "$METRICS_FILE")"
cat > "$METRICS_FILE" <<EOF
{
  "phase": "$PHASE",
  "plan": "$PLAN",
  "timestamp": "$(date -Iseconds)",
  "duration_seconds": $duration,
  "test_result": "$test_result",
  "tests_passed": ${passed:-0},
  "tests_failed": ${failed:-0},
  "exit_code": $exit_code,
  "root_cause": "$root_cause",
  "suggested_fix": "$suggested_fix"
}
EOF

# 5. Trigger auto-improver (runs in background)
if [ "$test_result" == "FAIL" ]; then
  nohup python .claude/auto-improver/on_execution_complete.py "$METRICS_FILE" &
  echo "❌ FAIL: Tests failed ($failed failed, $passed passed)"
  echo "Root cause: $root_cause"
  echo "Auto-improver triggered in background..."
  exit 1
fi

echo "✅ PASS: All tests passed ($passed passed, 0 failed)"
echo "Duration: ${duration}s"
echo "Metrics saved: $METRICS_FILE"
exit 0
```

**Key features:**
- Root cause extraction (7 common patterns)
- Suggested fix generation
- Triggers auto-improver on failure
- All data saved for knowledge graph ingestion

---

### Checkpoints 1-3 (Lighter Validation)

**Checkpoint 1:** `.claude/checkpoints/checkpoint_1_discussion.sh`
- Validates: Required sections present, ≥3 decisions, success criteria defined
- Captures: Discussion vagueness score (for predictive analysis)

**Checkpoint 2:** `.claude/checkpoints/checkpoint_2_research.sh`
- Validates: Dependencies documented, research depth ≥2000 chars
- Captures: Coverage percentage, missing dependencies list

**Checkpoint 3:** `.claude/checkpoints/checkpoint_3_plan.sh`
- Validates: Required sections, test commands, dependency declarations
- Captures: Plan complexity score, wave structure

*(Full scripts in appendix - keeping main doc focused on improvement loop)*

---

## Part 2: Auto-Improvement Engine

### 2.1 Instant Pattern Detection (No Waiting)

**The Problem:** Traditional pattern detection waits for 3 failures (30+ minutes wasted)

**The Solution:** Query knowledge graph for similar failures **across all history**

**Script:** `.claude/auto-improver/pattern_detector.py`

```python
#!/usr/bin/env python3
"""
Pattern Detector - Finds similar failures instantly using knowledge graph
Phase 14 integration: Queries Neo4j for historical patterns
"""

from src.core.graphiti_client import get_graphiti_client
import json

def find_similar_failures(current_failure: dict) -> list:
    """
    Query knowledge graph for similar failures across ALL phases.
    Returns pattern if ≥3 similar failures found (instant, <100ms)
    """

    graph = get_graphiti_client()
    if not graph:
        return []

    # Extract root cause type (e.g., "missing_dependency:graphiti-core" → "missing_dependency")
    root_cause_type = current_failure["root_cause"].split(":")[0]

    # Query Neo4j for similar failures (Phase 13.2 episodes + Phase 14 nodes)
    similar = graph.query("""
        MATCH (e:Episode)
        WHERE e.episode_type = 'checkpoint_validation'
          AND e.status = 'FAIL'
          AND e.root_cause STARTS WITH $root_cause_type
        RETURN
          e.root_cause as root_cause,
          e.fix_applied as fix,
          e.fix_success as worked,
          count(e) as occurrences
        GROUP BY e.root_cause, e.fix_applied, e.fix_success
        ORDER BY occurrences DESC
        LIMIT 5
    """, root_cause_type=root_cause_type)

    # Check if pattern exists (≥3 similar failures)
    if similar and similar[0]["occurrences"] >= 3:
        return similar

    return []

def generate_improvement_proposal(current_failure: dict, pattern: list) -> dict:
    """Generate improvement proposal based on historical pattern"""

    if not pattern:
        return None

    most_common = pattern[0]

    # Check if a fix was applied and worked
    successful_fixes = [p for p in pattern if p["worked"] == True]

    if successful_fixes:
        best_fix = successful_fixes[0]
        confidence = min(0.95, best_fix["occurrences"] / 10)  # More occurrences = higher confidence
    else:
        best_fix = most_common
        confidence = 0.5  # No proven fix yet

    return {
        "pattern_detected": True,
        "occurrences": most_common["occurrences"],
        "root_cause": current_failure["root_cause"],
        "proposed_fix": best_fix["fix"] or current_failure["suggested_fix"],
        "confidence": confidence,
        "historical_success_rate": best_fix.get("worked", False),
        "reasoning": f"Found {most_common['occurrences']} similar failures in history. "
                     f"Proposed fix has {confidence:.0%} confidence."
    }

if __name__ == "__main__":
    import sys

    # Load current failure from metrics
    metrics_file = sys.argv[1]
    with open(metrics_file) as f:
        current_failure = json.load(f)

    # Find pattern
    pattern = find_similar_failures(current_failure)

    # Generate proposal
    proposal = generate_improvement_proposal(current_failure, pattern)

    if proposal:
        print(json.dumps(proposal, indent=2))
    else:
        print(json.dumps({"pattern_detected": False}, indent=2))
```

**Result:** Pattern detection in <100ms instead of 30+ minutes

---

### 2.2 Verifier Agent (Autonomous + Sensical)

**Purpose:** Validate that proposed changes are coherent before auto-applying

**Agent:** `.claude/agents/change-verifier.md`

```markdown
# Change Verifier Agent

You are a verification specialist. Your job is to validate proposed system improvements before they are auto-applied.

## Role

Review improvement proposals and determine if they are:
1. **Syntactically valid** - File paths exist, format is correct
2. **Non-conflicting** - Doesn't contradict existing patterns
3. **Coherent** - Reasoning is sound, fix matches root cause
4. **Safe** - Won't break existing functionality

## Input Format

```json
{
  "target_file": ".claude/agents/gsd-executor.md",
  "change_type": "append_section",
  "proposed_change": "## Handling Missing Dependencies\n\nWhen execution fails with ModuleNotFoundError:\n1. Check if dependency is in requirements.txt\n2. If missing, add with exact version from error\n3. Re-run checkpoint after adding",
  "reasoning": "Found 8 similar failures across all phases. All were missing dependencies in research phase.",
  "confidence": 0.85
}
```

## Verification Process

### 1. Syntax Check
- Does target file exist?
- Is the markdown/JSON/YAML format valid?
- Are file paths referenced correctly?

### 2. Conflict Detection
Query knowledge graph:
```cypher
MATCH (f:File {path: $target_file})-[:HAS_PATTERN]->(p:Pattern)
WHERE p.text CONTAINS $keyword
RETURN p.text
```

Check: Does proposed change contradict existing patterns?

### 3. Coherence Check
- Does the fix logically address the root cause?
- Is the reasoning sound (e.g., "missing dependency" → "add to requirements.txt")?
- Are the steps actionable and specific?

### 4. Safety Check
- Will this change affect other agents/skills/hooks?
- Could this break existing functionality?
- Is the scope limited and reversible?

## Output Format

```json
{
  "verdict": "APPROVE",
  "confidence": 0.85,
  "checks": {
    "syntax": "PASS",
    "conflicts": "PASS",
    "coherence": "PASS",
    "safety": "PASS"
  },
  "reasoning": "Change is syntactically valid, doesn't conflict with existing patterns, logically addresses the root cause (missing dependencies), and is safely scoped to one agent file."
}
```

Or if issues found:

```json
{
  "verdict": "REJECT",
  "confidence": 0.3,
  "checks": {
    "syntax": "PASS",
    "conflicts": "FAIL",
    "coherence": "PASS",
    "safety": "PASS"
  },
  "reasoning": "Proposed change conflicts with existing pattern in CLAUDE.md line 234: 'Never auto-add dependencies without user confirmation'. Escalate to user.",
  "recommended_action": "Ask user for approval before adding dependencies."
}
```

## Decision Thresholds

- **APPROVE** (auto-apply): All checks PASS, confidence ≥ 0.8
- **REVIEW** (escalate): Any check FAIL, or confidence < 0.8
- **REJECT** (block): Critical conflicts or safety issues

## Integration

Called by `.claude/auto-improver/on_execution_complete.py` after pattern detection.
```

---

### 2.3 Auto-Improvement Orchestrator

**Script:** `.claude/auto-improver/on_execution_complete.py`

```python
#!/usr/bin/env python3
"""
Auto-Improvement Orchestrator
Runs after every execution, analyzes failure, proposes improvements, applies if verified
"""

import json
import sys
import subprocess
from pathlib import Path

def main(metrics_file: str):
    """Main orchestration flow"""

    print("=== Auto-Improvement Engine ===")

    # 1. Load metrics
    with open(metrics_file) as f:
        metrics = json.load(f)

    if metrics["test_result"] == "PASS":
        print("✅ Execution passed - no improvements needed")
        return

    print(f"❌ Execution failed: {metrics['root_cause']}")

    # 2. Detect pattern (instant via knowledge graph)
    print("\n🔍 Detecting patterns in knowledge graph...")
    pattern_result = subprocess.run(
        ["python", ".claude/auto-improver/pattern_detector.py", metrics_file],
        capture_output=True,
        text=True
    )

    proposal = json.loads(pattern_result.stdout)

    if not proposal.get("pattern_detected"):
        print("⚠️  No pattern detected yet - logging to graph for future analysis")
        log_to_graph(metrics)
        return

    print(f"✅ Pattern found: {proposal['occurrences']} similar failures")
    print(f"   Confidence: {proposal['confidence']:.0%}")
    print(f"   Proposed fix: {proposal['proposed_fix']}")

    # 3. Generate improvement proposal
    print("\n📝 Generating improvement proposal...")
    improvement = generate_improvement(metrics, proposal)

    # 4. Verify with verifier agent
    print("\n🔎 Verifying with change-verifier agent...")
    verification = verify_change(improvement)

    if verification["verdict"] == "APPROVE":
        print(f"✅ Verified (confidence: {verification['confidence']:.0%})")

        # 5. Auto-apply improvement
        print("\n🚀 Auto-applying improvement...")
        apply_improvement(improvement)

        # 6. Log success to graph
        log_success_to_graph(metrics, improvement)

        print("\n✨ System upgraded successfully!")
        print(f"   Updated: {improvement['target_file']}")

    else:
        print(f"⚠️  Verification failed: {verification['reasoning']}")
        print(f"   Recommended action: {verification.get('recommended_action', 'Manual review')}")

        # Escalate to user
        escalate_to_user(improvement, verification)

def generate_improvement(metrics: dict, proposal: dict) -> dict:
    """Generate concrete file changes based on proposal"""

    root_cause = metrics["root_cause"]

    # Determine target file based on root cause type
    if root_cause.startswith("missing_dependency"):
        target_file = ".claude/agents/gsd-executor.md"
        change_type = "append_section"
        change_content = f"""
## Handling Missing Dependencies (Auto-learned pattern)

When execution fails with `ModuleNotFoundError`:
1. Check if dependency is in `requirements.txt`
2. If missing, add with exact version: `{root_cause.split(':')[1]}==<version>`
3. Run `pip install {root_cause.split(':')[1]}`
4. Re-run checkpoint_4_execution.sh

**Pattern:** Detected {proposal['occurrences']} similar failures across all phases.
**Success rate:** {proposal.get('historical_success_rate', 'Unknown')}
**Auto-learned:** {metrics['timestamp']}
"""

    elif root_cause == "import_error":
        target_file = ".claude/agents/gsd-planner.md"
        change_type = "append_section"
        change_content = """
## File Structure Validation (Auto-learned pattern)

When planning file creation, validate import paths:
1. Check that parent modules have `__init__.py`
2. Verify relative import syntax matches directory structure
3. Add imports to plan's verification checklist

**Auto-learned from import_error pattern**
"""

    else:
        # Generic learning - add to learnings.md
        target_file = ".claude/learnings.md"
        change_type = "append"
        change_content = f"""
### {metrics['timestamp']} | {metrics['phase']}-{metrics['plan']}
**Learning:** {proposal['proposed_fix']}
**Root cause:** {root_cause}
**Pattern strength:** {proposal['occurrences']} occurrences
**Status:** Auto-captured (pending promotion)
"""

    return {
        "target_file": target_file,
        "change_type": change_type,
        "proposed_change": change_content,
        "reasoning": proposal["reasoning"],
        "confidence": proposal["confidence"],
        "metadata": {
            "phase": metrics["phase"],
            "plan": metrics["plan"],
            "occurrences": proposal["occurrences"]
        }
    }

def verify_change(improvement: dict) -> dict:
    """Call verifier agent to validate proposal"""

    # Use Task tool to spawn verifier agent
    verification_prompt = f"""
Verify this proposed improvement:

Target file: {improvement['target_file']}
Change type: {improvement['change_type']}
Proposed change:
{improvement['proposed_change']}

Reasoning: {improvement['reasoning']}
Confidence: {improvement['confidence']}

Check: Syntax, Conflicts, Coherence, Safety
Output verdict: APPROVE or REJECT with reasoning
"""

    # Spawn verifier agent (runs in subprocess)
    result = subprocess.run(
        ["claude", "agent", "change-verifier", "--prompt", verification_prompt],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Parse verification result
    try:
        return json.loads(result.stdout)
    except:
        # Fallback if agent output isn't JSON
        if "APPROVE" in result.stdout:
            return {"verdict": "APPROVE", "confidence": 0.8}
        else:
            return {"verdict": "REJECT", "confidence": 0.3, "reasoning": "Agent verification unclear"}

def apply_improvement(improvement: dict):
    """Apply the verified improvement to target file"""

    target = Path(improvement["target_file"])

    if improvement["change_type"] == "append":
        # Append to file
        with open(target, "a") as f:
            f.write("\n" + improvement["proposed_change"])

    elif improvement["change_type"] == "append_section":
        # Append new section to end of file
        with open(target, "a") as f:
            f.write("\n\n---\n" + improvement["proposed_change"])

    print(f"✅ Applied change to {target}")

def log_success_to_graph(metrics: dict, improvement: dict):
    """Log successful improvement to Phase 13.2 graph"""

    from src.core.graphiti_client import get_graphiti_client
    from src.core.synthex_entities import create_episode_payload, EpisodeType

    graph = get_graphiti_client()
    if not graph:
        return

    episode = create_episode_payload(
        episode_type=EpisodeType.SELF_IMPROVEMENT,
        data={
            "phase": metrics["phase"],
            "root_cause": metrics["root_cause"],
            "improvement_applied": improvement["target_file"],
            "confidence": improvement["confidence"],
            "timestamp": metrics["timestamp"]
        }
    )

    # Use Phase 13.2 ingestion pipeline
    from src.tasks.graphiti_tasks import emit_episode
    emit_episode.delay(episode)

def escalate_to_user(improvement: dict, verification: dict):
    """Escalate rejected improvements to user for review"""

    escalation_file = ".claude/escalations/pending-improvements.json"
    Path(escalation_file).parent.mkdir(exist_ok=True)

    # Load existing escalations
    if Path(escalation_file).exists():
        with open(escalation_file) as f:
            escalations = json.load(f)
    else:
        escalations = []

    # Add new escalation
    escalations.append({
        "timestamp": improvement["metadata"]["phase"],
        "improvement": improvement,
        "verification": verification,
        "status": "pending"
    })

    # Save
    with open(escalation_file, "w") as f:
        json.dump(escalations, indent=2, fp=f)

    print(f"\n⚠️  Escalated to: {escalation_file}")
    print("   User can review and manually apply if desired")

def log_to_graph(metrics: dict):
    """Log failure to graph even if no pattern detected yet"""

    from src.core.graphiti_client import get_graphiti_client
    from src.core.synthex_entities import create_episode_payload, EpisodeType

    graph = get_graphiti_client()
    if not graph:
        return

    episode = create_episode_payload(
        episode_type=EpisodeType.CHECKPOINT_VALIDATION,
        data={
            "phase": metrics["phase"],
            "plan": metrics["plan"],
            "status": "FAIL",
            "root_cause": metrics["root_cause"],
            "timestamp": metrics["timestamp"],
            "fix_applied": None,
            "fix_success": None
        }
    )

    from src.tasks.graphiti_tasks import emit_episode
    emit_episode.delay(episode)

if __name__ == "__main__":
    metrics_file = sys.argv[1]
    main(metrics_file)
```

**Key features:**
- Instant pattern detection via knowledge graph
- Verifier agent validation
- Auto-applies improvements when verified
- Escalates uncertain changes to user
- Logs all actions to graph for future learning

---

## Part 3: Claude Code Automation Integration

### Codebase Profile (Analysis Results)

- **Backend:** Python 3.12, Flask, SQLAlchemy, Celery, PostgreSQL, Redis, Neo4j 5.26, Graphiti-core
- **Frontend:** Next.js 16, React 19, TypeScript 5.9, Playwright E2E
- **AI/ML:** OpenAI, sentence-transformers, open-clip-torch
- **Testing:** pytest (112 tests), Playwright (29 E2E tests), Vitest
- **Planning:** 286 markdown docs, 7 governance roles
- **CI/CD:** 6 GitHub Actions workflows
- **Existing automation:** 12 GSD agents, 2 hooks, 2 skills

---

### 🔌 MCP Server Recommendations (Official Ecosystem)

#### 1. **context7** (CRITICAL - Install First)

**Why:** You use OpenAI, Flask-SQLAlchemy, Next.js, Neo4j, PostgreSQL - instant doc lookup prevents hallucinations

**Install:**
```bash
claude mcp add context7
```

**Use cases in this project:**
- Phase 14 implementation: Query Neo4j Cypher docs
- Phase 15 implementation: Query Flask-SQLAlchemy patterns
- Daily development: OpenAI API best practices, React 19 patterns

**Integration with auto-improver:**
```python
# When verifier agent needs to check syntax
context7_result = query_context7("Neo4j Cypher CREATE syntax")
# Ensures proposed Cypher queries are valid before auto-applying
```

---

#### 2. **PostgreSQL MCP** (HIGH PRIORITY)

**Why:** 259 Python files doing SQLAlchemy queries - direct DB inspection speeds debugging

**Install:**
```bash
claude mcp add postgres
# Configure with your docker-compose PostgreSQL credentials
```

**Use cases:**
- Debug enrichment failures: "Show last 10 enrichment_runs"
- Inspect graph episodes: "Query assistant_verification_events where status=FAIL"
- Schema validation: "Show all tables with 'assistant_' prefix"

**Integration with auto-improver:**
```python
# When checkpoint fails with DB error, auto-query DB state
if "IntegrityError" in root_cause:
    db_state = postgres_mcp.query("SELECT * FROM ... LIMIT 5")
    # Use actual DB state to propose better fix
```

---

#### 3. **GitHub MCP** (CI/CD Integration)

**Why:** 6 GitHub Actions workflows - manage from CLI

**Install:**
```bash
claude mcp add github
# Requires: gh CLI installed and authenticated
```

**Use cases:**
- Monitor CI failures: "Show failed workflow runs for risk-policy-gate"
- Create issues: "Create issue for checkpoint failure pattern"
- PR management: "List PRs with failing tests"

---

### 🎯 Skills Recommendations (Official + Custom)

#### 1. **verify-phase** (CUSTOM - Core to this system)

**Purpose:** Run all 4 progressive verification checkpoints

**Create:** `.claude/skills/verify-phase/SKILL.md`

```yaml
---
name: verify-phase
description: Run progressive verification checkpoints for a GSD phase
disable-model-invocation: true  # User-only (triggers bash scripts)
---

# Progressive Phase Verification

Run all 4 checkpoints for a phase and trigger auto-improvement if failures detected.

## Usage

/verify-phase <phase-id>

## Example

/verify-phase 14

## What it does

1. Runs checkpoint_1_discussion.sh
2. Runs checkpoint_2_research.sh
3. Runs checkpoint_3_plan.sh
4. Runs checkpoint_4_execution.sh (for all plans in phase)
5. Captures metrics in .claude/metrics/<phase>/
6. Triggers auto-improver if any checkpoint fails
7. Updates knowledge graph with results

## Output

- ✅/❌ status for each checkpoint
- Root cause analysis for failures
- Auto-improvement status (applied/escalated)
- Metrics saved to .claude/metrics/
```

**Script:** `.claude/skills/verify-phase/verify.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

PHASE=$1
PHASE_DIR=".planning/phases/${PHASE}-*"

echo "=== Progressive Verification: Phase $PHASE ==="

# Find phase directory
phase_path=$(ls -d $PHASE_DIR 2>/dev/null | head -1)
if [ -z "$phase_path" ]; then
  echo "❌ Phase directory not found: $PHASE_DIR"
  exit 1
fi

# Run checkpoints in order
checkpoints=(
  "1:discussion"
  "2:research"
  "3:plan"
)

failed_checkpoint=""
for cp in "${checkpoints[@]}"; do
  num="${cp%%:*}"
  name="${cp##*:}"

  echo ""
  echo "Running checkpoint $num ($name)..."

  if .claude/checkpoints/checkpoint_${num}_${name}.sh "$PHASE"; then
    echo "✅ CP$num ($name): PASS"
  else
    echo "❌ CP$num ($name): FAIL"
    failed_checkpoint="$num:$name"
    break  # Stop at first failure
  fi
done

# If earlier checkpoints failed, don't run execution
if [ -n "$failed_checkpoint" ]; then
  echo ""
  echo "=== Verification Summary ==="
  echo "❌ Failed at checkpoint $failed_checkpoint"
  echo "Skipping execution checkpoint (earlier stage must pass first)"
  exit 1
fi

# Run checkpoint 4 for all plans in phase
echo ""
echo "Running checkpoint 4 (execution) for all plans..."

plan_files=("$phase_path"/*-PLAN.md)
total_plans=${#plan_files[@]}
passed_plans=0
failed_plans=0

for plan_file in "${plan_files[@]}"; do
  plan_id=$(basename "$plan_file" | sed 's/-PLAN.md//')

  echo ""
  echo "Checkpoint 4: $plan_id"

  if .claude/checkpoints/checkpoint_4_execution.sh "$PHASE" "$plan_id"; then
    ((passed_plans++))
  else
    ((failed_plans++))
  fi
done

# Summary
echo ""
echo "=== Verification Summary ==="
echo "Phase: $PHASE"
echo "Total plans: $total_plans"
echo "Passed: $passed_plans"
echo "Failed: $failed_plans"

if [ $failed_plans -eq 0 ]; then
  echo "✅ All checkpoints passed!"
  exit 0
else
  echo "❌ Some checkpoints failed - auto-improver triggered"
  exit 1
fi
```

---

#### 2. **query-graph** (CUSTOM - Phase 14 Integration)

**Purpose:** Query knowledge graph for code relationships

**Create:** `.claude/skills/query-graph/SKILL.md`

```yaml
---
name: query-graph
description: Query the codebase knowledge graph for relationships and patterns
---

# Knowledge Graph Query Interface

Query the Phase 14 knowledge graph for code relationships, planning context, and patterns.

## Usage

/query-graph <template> <args>

## Templates (Fast, <100ms)

**imports** <file> - What does this file import?
/query-graph imports src/core/cache.py

**imported-by** <file> - What imports this file?
/query-graph imported-by src/tasks/enrichment.py

**similar** <file> - Find semantically similar files (vector search)
/query-graph similar src/assistant/governance/verification_oracle.py

**planning** <file> - What planning doc implemented this file?
/query-graph planning src/core/graphiti_client.py

**impact** <file> - What would break if this file changed?
/query-graph impact src/core/cache.py

**phase-code** <phase> - What code implements this phase?
/query-graph phase-code 13.2

**failures** <file> - What failures occurred in this file?
/query-graph failures src/tasks/enrichment.py

## Custom Queries (Slower, 500ms-2s)

**custom** "<natural language>"
/query-graph custom "What files handle Vision API calls?"

## Output

- List of files with relationships
- Similarity scores (for vector search)
- Planning doc context
- Failure history (if applicable)
```

**Implementation:** `.claude/skills/query-graph/query.py`

```python
#!/usr/bin/env python3
"""Knowledge Graph Query Interface - Phase 14 Integration"""

import sys
from src.core.graphiti_client import get_graphiti_client

QUERY_TEMPLATES = {
    "imports": """
        MATCH (f:File {path: $file_path})-[:IMPORTS]->(imported:File)
        RETURN imported.path, imported.purpose
        ORDER BY imported.path
    """,

    "imported-by": """
        MATCH (f:File {path: $file_path})<-[:IMPORTS]-(importer:File)
        RETURN importer.path, importer.purpose
        ORDER BY importer.path
    """,

    "similar": """
        MATCH (f:File {path: $file_path})
        CALL db.index.vector.queryNodes('file_embeddings', 5, f.embedding)
        YIELD node, score
        WHERE score > 0.7 AND node.path != $file_path
        RETURN node.path, node.purpose, score
        ORDER BY score DESC
    """,

    "planning": """
        MATCH (f:File {path: $file_path})-[:IMPLEMENTS]->(plan:PlanningDoc)
        RETURN plan.path, plan.phase_number, plan.goal
    """,

    "impact": """
        MATCH (f:File {path: $file_path})<-[:IMPORTS*1..3]-(dependent:File)
        RETURN dependent.path, length(path) as depth
        ORDER BY depth, dependent.path
    """,

    "phase-code": """
        MATCH (plan:PlanningDoc {phase_number: $phase})<-[:IMPLEMENTS]-(f:File)
        RETURN f.path, f.purpose
        ORDER BY f.path
    """,

    "failures": """
        MATCH (e:Episode {episode_type: 'checkpoint_validation'})
        WHERE e.file_path = $file_path AND e.status = 'FAIL'
        RETURN e.root_cause, e.timestamp, e.fix_applied
        ORDER BY e.timestamp DESC
        LIMIT 10
    """
}

def main():
    if len(sys.argv) < 3:
        print("Usage: query-graph <template> <args>")
        sys.exit(1)

    template = sys.argv[1]
    args = " ".join(sys.argv[2:])

    graph = get_graphiti_client()
    if not graph:
        print("❌ Knowledge graph unavailable")
        sys.exit(1)

    # Execute template query
    if template in QUERY_TEMPLATES:
        query = QUERY_TEMPLATES[template]

        # Determine parameter name from template
        if template in ["imports", "imported-by", "similar", "planning", "impact", "failures"]:
            param_name = "file_path"
            param_value = args
        elif template == "phase-code":
            param_name = "phase"
            param_value = args

        results = graph.query(query, **{param_name: param_value})

        # Format output
        if results:
            print(f"\n=== {template.upper()}: {args} ===\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result}")
        else:
            print(f"No results found for: {args}")

    elif template == "custom":
        # Natural language query (Phase 14 LLM → Cypher translation)
        print(f"Custom query: {args}")
        print("(LLM → Cypher translation - Phase 14 feature)")
        # TODO: Implement LLM-to-Cypher in Phase 14

    else:
        print(f"Unknown template: {template}")
        print("Available: imports, imported-by, similar, planning, impact, phase-code, failures, custom")

if __name__ == "__main__":
    main()
```

---

#### 3. **commit** (INSTALL from official plugins)

**Why:** Automated commit workflow with governance integration

**Install:**
```bash
claude plugin install commit-commands
```

**Use after auto-improvements:**
```bash
# After system auto-upgrades itself
/commit -m "Auto-improvement: Add missing dependency pattern to gsd-executor"
```

**Integration with auto-improver:**
```python
# After successful auto-apply, create commit
if improvement_applied:
    subprocess.run([
        "claude", "skill", "commit",
        "-m", f"Auto-improvement: {improvement['target_file']}"
    ])
```

---

### ⚡ Hooks Recommendations

#### 1. **PostToolUse: Auto-Update Graph on File Edit** (CRITICAL)

**Purpose:** Every file edit updates knowledge graph immediately

**Config:** `.claude/settings.json`

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "filter": {
          "tool": "Edit",
          "pathPattern": "src/**/*.py"
        },
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/post-edit-graph-update.py {{file_path}}"
          }
        ]
      },
      {
        "filter": {
          "tool": "Edit",
          "pathPattern": ".planning/**/*.md"
        },
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/post-edit-planning-update.py {{file_path}}"
          }
        ]
      }
    ]
  }
}
```

**Script:** `.claude/hooks/post-edit-graph-update.py`

```python
#!/usr/bin/env python3
"""Update knowledge graph when file is edited (Phase 14 integration)"""

import sys
from datetime import datetime
from src.core.graphiti_client import get_graphiti_client
from src.core.synthex_entities import create_episode_payload, EpisodeType

file_path = sys.argv[1]

graph = get_graphiti_client()
if not graph:
    print("⚠️  Graph unavailable - skipping update")
    sys.exit(0)

# Update file node in knowledge graph (Phase 14)
graph.update_node(f"File:{file_path}", properties={
    "last_modified": datetime.now().isoformat(),
    "modified_by": "claude"
})

# Emit code_modification episode (Phase 13.2)
episode = create_episode_payload(
    episode_type=EpisodeType.CODE_MODIFICATION,
    data={
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "trigger": "post_edit_hook"
    }
)

# Async ingestion via Celery
from src.tasks.graphiti_tasks import emit_episode
emit_episode.delay(episode)

print(f"✅ Graph updated: {file_path}")
```

---

#### 2. **PreToolUse: Run Governance Gate Before Commit** (HIGH PRIORITY)

**Purpose:** Block commits that fail governance (integrates with existing gates)

**Config:** Add to `.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "filter": {
          "tool": "Bash",
          "commandPattern": "git commit.*"
        },
        "hooks": [
          {
            "type": "command",
            "command": "python scripts/governance/risk_tier_gate.py --from-git-diff",
            "blockOnFailure": true
          }
        ]
      }
    ]
  }
}
```

**Integration:** This already exists in your project! Just needs hook configuration.

---

#### 3. **SessionStart: Check for Pending Improvements** (NEW)

**Purpose:** Notify user of escalated improvements at session start

**Config:** Add to `.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node .claude/hooks/gsd-check-update.js"
          },
          {
            "type": "command",
            "command": "python .claude/hooks/check-pending-improvements.py"
          }
        ]
      }
    ]
  }
}
```

**Script:** `.claude/hooks/check-pending-improvements.py`

```python
#!/usr/bin/env python3
"""Check for pending auto-improvements that need user review"""

import json
from pathlib import Path

escalation_file = Path(".claude/escalations/pending-improvements.json")

if not escalation_file.exists():
    print("✅ No pending improvements")
    exit(0)

with open(escalation_file) as f:
    escalations = json.load(f)

pending = [e for e in escalations if e["status"] == "pending"]

if pending:
    print(f"\n⚠️  {len(pending)} pending improvement(s) need review:")
    print(f"   See: {escalation_file}")
    print(f"   Review and apply manually or run: /approve-improvements")
else:
    print("✅ No pending improvements")
```

---

### 🤖 Subagent Recommendations

#### 1. **change-verifier** (CUSTOM - Already defined above)

**Purpose:** Verify proposed improvements before auto-applying

**Location:** `.claude/agents/change-verifier.md`

**Trigger:** Called by `on_execution_complete.py` after pattern detection

---

#### 2. **pattern-analyzer** (CUSTOM - Nightly batch analysis)

**Purpose:** Aggregate all metrics nightly and propose system-wide optimizations

**Create:** `.claude/agents/pattern-analyzer.md`

```markdown
# Pattern Analyzer Agent

Run nightly analysis of all checkpoint metrics to find system-wide optimization opportunities.

## Trigger

- Nightly (12:00 AM via cron)
- On-demand: /analyze-patterns

## Process

1. Load ALL metrics from .claude/metrics/*/*.json
2. Query knowledge graph for ALL episodes (Phase 13.2 + 14)
3. Analyze patterns:
   - Which checkpoint fails most often?
   - Which phases have highest failure rates?
   - Which root causes are most common?
   - Are failure rates decreasing over time?
4. Generate improvement proposals:
   - Update CLAUDE.md with common anti-patterns
   - Promote learnings.md entries to CLAUDE.md (if occurred ≥2 times)
   - Propose new hooks/skills based on patterns
   - Suggest agent prompt improvements
5. Pass to verifier agent for validation
6. Auto-apply or escalate

## Output

- Nightly report: .claude/reports/pattern-analysis-YYYY-MM-DD.md
- Auto-applied improvements logged to graph
- Escalations added to pending-improvements.json

## Example Insights

After analyzing 100 checkpoints:
- Research checkpoint fails 18% of the time (highest)
- Most common root cause: missing_dependency (32 occurrences)
- Proposed improvement: Update gsd-phase-researcher.md to include dependency validation checklist
- Confidence: 0.92 → AUTO-APPLIED
```

---

#### 3. **graph-optimizer** (CUSTOM - Phase 15 integration)

**Purpose:** Optimize knowledge graph queries and embeddings for performance

**Create:** `.claude/agents/graph-optimizer.md`

```markdown
# Graph Optimizer Agent

Analyze knowledge graph query performance and optimize for Phase 14/15 workloads.

## Trigger

- Weekly (Sunday 2:00 AM)
- After major graph schema changes

## Process

1. Analyze query logs:
   - Which queries are slowest?
   - Which queries run most frequently?
   - Are there missing indexes?
2. Optimize:
   - Create Neo4j indexes for slow queries
   - Refactor complex Cypher queries
   - Update vector index parameters
3. Benchmark:
   - Run before/after performance tests
   - Verify P95 latency improves
4. Apply if verified

## Output

- Performance report: .claude/reports/graph-optimization-YYYY-MM-DD.md
- Applied optimizations logged to graph
```

---

## Part 4: Integration Architecture (How Everything Works Together)

### The Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ YOU: "Update enrichment pipeline to handle color variants"      │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ EXECUTION LAYER (Hooks + Checkpoints + Skills)                  │
│                                                                  │
│ 1. Edit file → PostToolUse hook fires                           │
│    → .claude/hooks/post-edit-graph-update.py                    │
│    → Updates Phase 14 knowledge graph (File node)               │
│    → Emits Phase 13.2 episode (code_modification)               │
│                                                                  │
│ 2. Commit → PreToolUse hook fires                               │
│    → scripts/governance/risk_tier_gate.py (blocks if RED)       │
│    → Progressive verification checkpoints run                   │
│                                                                  │
│ 3. Checkpoint 4 (execution) runs                                │
│    → checkpoint_4_execution.sh                                  │
│    → Tests run, metrics captured                                │
│    → If FAIL: Triggers auto-improver                            │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS LAYER (Knowledge Graph + Pattern Detection)            │
│                                                                  │
│ 4. Auto-improver analyzes failure                               │
│    → .claude/auto-improver/on_execution_complete.py             │
│    → Calls pattern_detector.py                                  │
│                                                                  │
│ 5. Pattern detector queries graph (INSTANT)                     │
│    → Cypher query: Find similar failures across ALL history     │
│    → Returns: 8 similar "missing_dependency" failures           │
│    → Confidence: 0.85 (8 occurrences / 10 = high)               │
│                                                                  │
│ 6. Generate improvement proposal                                │
│    → Target: .claude/agents/gsd-executor.md                     │
│    → Change: Add "Missing Dependencies" section                 │
│    → Reasoning: Pattern detected (8 occurrences)                │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ VERIFICATION LAYER (Verifier Agent)                             │
│                                                                  │
│ 7. Spawn verifier agent                                         │
│    → .claude/agents/change-verifier.md                          │
│    → Checks: Syntax? Conflicts? Coherence? Safety?              │
│                                                                  │
│ 8. Verifier queries graph for conflicts                         │
│    → "Does CLAUDE.md have contradicting patterns?"              │
│    → "Will this break other agents?"                            │
│    → Result: No conflicts, change is safe                       │
│                                                                  │
│ 9. Verdict: APPROVE (confidence 0.85)                           │
│    → All checks PASS                                            │
│    → Confidence ≥ 0.8 threshold                                 │
│    → Auto-apply approved                                        │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ AUTO-UPGRADE LAYER (System Improves Itself)                     │
│                                                                  │
│ 10. Apply improvement                                           │
│     → Edit .claude/agents/gsd-executor.md                       │
│     → Append new section: "Handling Missing Dependencies"       │
│     → File saved                                                │
│                                                                  │
│ 11. Log success to graph                                        │
│     → Episode: SELF_IMPROVEMENT                                 │
│     → Metadata: target_file, confidence, timestamp              │
│     → Stored in Phase 13.2 graph                                │
│                                                                  │
│ 12. Update learnings.md                                         │
│     → Append: "Auto-learned missing dependency pattern"         │
│     → Mark for promotion to CLAUDE.md if repeats               │
│                                                                  │
│ 13. Commit improvement (optional)                               │
│     → /commit -m "Auto: Add missing dependency pattern"         │
└─────────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────────┐
│ FEEDBACK LOOP (System is now smarter)                           │
│                                                                  │
│ Next time "missing_dependency" failure occurs:                  │
│   → gsd-executor.md now has handling instructions               │
│   → Pattern confidence increases (9 occurrences)                │
│   → Auto-fix more likely to succeed                             │
│   → Failure rate decreases over time                            │
│                                                                  │
│ After 30 days:                                                  │
│   → Nightly pattern-analyzer runs                               │
│   → Finds "missing_dependency" occurred 45 times                │
│   → Proposes promotion to CLAUDE.md (core pattern)              │
│   → Verifier approves → auto-promoted                           │
│   → Now ALL agents benefit from this learning                   │
└─────────────────────────────────────────────────────────────────┘
```

---

### File Locations (Complete Manifest)

```
.claude/
├── checkpoints/
│   ├── checkpoint_1_discussion.sh          # Validates discussion
│   ├── checkpoint_2_research.sh            # Validates research
│   ├── checkpoint_3_plan.sh                # Validates planning
│   └── checkpoint_4_execution.sh           # Validates execution + captures metrics
│
├── auto-improver/
│   ├── on_execution_complete.py            # Orchestrator (runs after every execution)
│   ├── pattern_detector.py                 # Graph-based pattern detection
│   ├── config_updater.py                   # File edit utilities
│   └── README.md                           # Auto-improver documentation
│
├── agents/
│   ├── change-verifier.md                  # Verifies improvements before auto-apply
│   ├── pattern-analyzer.md                 # Nightly batch analysis
│   ├── graph-optimizer.md                  # Graph performance optimization
│   └── [existing 12 GSD agents...]
│
├── skills/
│   ├── verify-phase/
│   │   ├── SKILL.md                        # Progressive verification runner
│   │   └── verify.sh                       # Executes all 4 checkpoints
│   ├── query-graph/
│   │   ├── SKILL.md                        # Knowledge graph queries
│   │   └── query.py                        # Template + custom queries
│   └── [existing 2 skills...]
│
├── hooks/
│   ├── post-edit-graph-update.py           # Update graph on file edit
│   ├── post-edit-planning-update.py        # Update graph on planning doc edit
│   ├── check-pending-improvements.py       # SessionStart hook
│   └── [existing 2 hooks...]
│
├── metrics/
│   └── <phase>/
│       └── <plan>.json                     # Checkpoint execution metrics
│
├── escalations/
│   └── pending-improvements.json           # Improvements needing user review
│
├── reports/
│   ├── pattern-analysis-YYYY-MM-DD.md      # Nightly analysis reports
│   └── graph-optimization-YYYY-MM-DD.md    # Graph performance reports
│
├── learnings.md                             # ✅ Already exists - auto-appends
└── settings.json                            # Hook configurations

src/core/
└── synthex_entities.py                      # Add: EpisodeType.SELF_IMPROVEMENT
                                             #      EpisodeType.CODE_MODIFICATION

scripts/governance/
├── risk_tier_gate.py                        # ✅ Already exists - used in PreToolUse hook
└── [other governance scripts...]
```

---

## Part 5: Phase 14 & 15 Integration Requirements

### Phase 14: Knowledge Graph Additions

#### 14-01: Schema Extensions

**Add new node types:**

```cypher
// Checkpoint node
CREATE (cp:Checkpoint {
  id: "14-CP4-01",
  phase: "14",
  plan: "14-01",
  type: "execution",
  status: "PASS",
  timestamp: datetime(),
  duration_seconds: 45,
  root_cause: null
})

// Metric node
CREATE (m:Metric {
  id: "14-01-metrics",
  tests_passed: 12,
  tests_failed: 0,
  exit_code: 0
})

// Self-improvement node
CREATE (si:SelfImprovement {
  id: "SI-001",
  target_file: ".claude/agents/gsd-executor.md",
  change_type: "append_section",
  confidence: 0.85,
  verified: true,
  applied: true,
  timestamp: datetime()
})

// Relationships
MATCH (plan:Plan {id: "14-01"}), (cp:Checkpoint {id: "14-CP4-01"})
CREATE (plan)-[:VALIDATED_BY]->(cp)

MATCH (cp:Checkpoint), (m:Metric)
CREATE (cp)-[:PRODUCED]->(m)

MATCH (cp:Checkpoint {status: "FAIL"}), (si:SelfImprovement)
CREATE (cp)-[:TRIGGERED]->(si)
```

#### 14-02: Vector Embeddings Enhancement

**Include checkpoint history in file embeddings:**

```python
# When generating file embeddings for gsd-executor.md
file_embedding_context = f"""
File: .claude/agents/gsd-executor.md
Purpose: Execute GSD plans with atomic commits
Last modified: 2026-02-20
Checkpoint success rate: 87% (45 PASS / 52 total)
Common failures: missing_dependency (8), import_error (3)
Auto-improvements: 2 applied, 1 pending
Related files: gsd-planner.md, gsd-verifier.md
"""

embedding = sentence_transformer.encode(file_embedding_context)
graph.update_node("File:gsd-executor.md", embedding=embedding)
```

#### 14-05: Git Hook Enhancement

**Extend existing hook to run checkpoints:**

```javascript
// .claude/hooks/git-pre-commit.js (existing - enhance)
const { execSync } = require('child_process');

// Get changed files
const changed = execSync('git diff --cached --name-only').toString().trim().split('\n');

// 1. Run progressive verification if phase files changed
const phaseChanges = changed.filter(f => f.startsWith('.planning/phases/'));
if (phaseChanges.length > 0) {
  const phaseMatch = phaseChanges[0].match(/phases\/([^/]+)/);
  if (phaseMatch) {
    console.log(`Running progressive verification for ${phaseMatch[1]}...`);
    try {
      execSync(`.claude/skills/verify-phase/verify.sh ${phaseMatch[1]}`, { stdio: 'inherit' });
    } catch (e) {
      console.error('❌ Progressive verification failed - commit blocked');
      process.exit(1);
    }
  }
}

// 2. Update knowledge graph with commit
execSync('python .claude/hooks/update-graph-on-commit.py', { stdio: 'inherit' });

// 3. Run existing governance gates (already in place)
// ... existing code ...
```

#### 14-08: Query Templates for Auto-Improvement

**Add checkpoint-specific queries:**

```python
# Add to Phase 14 query templates

QUERY_TEMPLATES = {
    # ... existing templates ...

    "checkpoint_history": """
        MATCH (plan:Plan {id: $plan_id})-[:VALIDATED_BY]->(cp:Checkpoint)
        RETURN cp.type, cp.status, cp.timestamp, cp.root_cause
        ORDER BY cp.timestamp DESC
    """,

    "similar_failures": """
        MATCH (cp:Checkpoint {status: 'FAIL'})
        WHERE cp.root_cause STARTS WITH $root_cause_type
        MATCH (cp)-[:TRIGGERED]->(si:SelfImprovement {applied: true})
        RETURN
          cp.root_cause,
          si.target_file,
          si.confidence,
          count(cp) as occurrences
        GROUP BY cp.root_cause, si.target_file, si.confidence
        ORDER BY occurrences DESC
    """,

    "auto_improvements": """
        MATCH (si:SelfImprovement)
        WHERE si.timestamp > datetime() - duration({days: 30})
        RETURN
          si.target_file,
          si.applied,
          si.confidence,
          count(si) as improvements
        GROUP BY si.target_file, si.applied, si.confidence
        ORDER BY improvements DESC
    """
}
```

---

### Phase 15: Self-Healing Integration

#### 15-01: Autonomous Refactoring with Checkpoints

**Integrate checkpoint validation into refactoring:**

```python
# Phase 15: Autonomous refactoring now uses checkpoints

class AutonomousRefactorer:
    def apply_refactoring(self, proposal):
        """Apply refactoring with checkpoint validation"""

        # 1. Apply change
        self.edit_files(proposal["files"])

        # 2. Run checkpoint 4 (execution validation)
        checkpoint_result = subprocess.run(
            [".claude/checkpoints/checkpoint_4_execution.sh",
             proposal["phase"], proposal["plan"]],
            capture_output=True
        )

        # 3. If checkpoint fails, trigger auto-improver
        if checkpoint_result.returncode != 0:
            # Auto-improver will analyze and propose fix
            # This creates a feedback loop: refactoring → checkpoint → improvement
            pass

        # 4. Log to graph
        self.log_refactoring_outcome(proposal, checkpoint_result)
```

#### 15-02: Performance Optimization with Metrics

**Use checkpoint duration metrics to optimize:**

```python
# Phase 15: Identify slow checkpoints and optimize

def optimize_slow_checkpoints():
    """Find and optimize slow-running checkpoints"""

    # Query all checkpoint durations
    slow_checkpoints = graph.query("""
        MATCH (cp:Checkpoint)-[:PRODUCED]->(m:Metric)
        WHERE cp.duration_seconds > 30
        MATCH (cp)-[:VALIDATED]-(plan:Plan)-[:IMPLEMENTS]->(file:File)
        RETURN
          file.path,
          avg(cp.duration_seconds) as avg_duration,
          count(cp) as executions
        ORDER BY avg_duration DESC
        LIMIT 10
    """)

    for slow in slow_checkpoints:
        # Propose optimization
        if "integration" in slow["file.path"]:
            proposal = {
                "target": slow["file.path"],
                "optimization": "Add database mocks to reduce test time",
                "expected_improvement": "50% faster",
                "confidence": 0.8
            }

            # Send to verifier, apply if approved
            if verify_and_apply(proposal):
                print(f"✅ Optimized: {slow['file.path']}")
```

#### 15-03: Predictive Checkpoint Failure

**Predict failures before execution:**

```python
# Phase 15: Predict which checkpoints will fail

from sklearn.ensemble import RandomForestClassifier

class CheckpointFailurePredictor:
    def __init__(self):
        self.model = self.load_trained_model()

    def predict_failure_risk(self, phase, plan):
        """Predict checkpoint failure risk before execution"""

        # 1. Extract features from discussion/research/plan
        features = self.extract_features(phase, plan)

        # 2. Query historical checkpoint data
        historical = graph.query("""
            MATCH (p:Phase {id: $phase})-[:HAS_PLAN]->(plan:Plan)
            MATCH (plan)-[:VALIDATED_BY]->(cp:Checkpoint)
            RETURN
              cp.type,
              cp.status,
              plan.complexity_score,
              plan.dependency_count
        """, phase=phase)

        # 3. Predict
        failure_probability = self.model.predict_proba(features)[0][1]

        # 4. If high risk, propose preemptive improvements
        if failure_probability > 0.6:
            return {
                "risk_score": failure_probability,
                "likely_failure_checkpoint": self.predict_failure_stage(features),
                "suggested_improvements": self.generate_preemptive_fixes(features)
            }

        return {"risk_score": failure_probability}
```

---

## Part 6: Success Metrics & Timeline

### Week 1: Foundation

**Deliverables:**
- [ ] All 4 checkpoint scripts created and tested
- [ ] Auto-improver orchestrator working (on_execution_complete.py)
- [ ] Pattern detector querying knowledge graph
- [ ] Verifier agent validating proposals
- [ ] PostToolUse hook updating graph on edits

**Success Criteria:**
- ✅ Checkpoint 4 captures metrics on execution
- ✅ At least 1 pattern detected from graph query
- ✅ At least 1 improvement verified and applied

---

### Week 2-3: Integration

**Deliverables:**
- [ ] All hooks configured and firing correctly
- [ ] verify-phase skill working end-to-end
- [ ] query-graph skill integrated with Phase 14
- [ ] MCP servers installed (context7, postgres)
- [ ] Nightly pattern-analyzer agent running

**Success Criteria:**
- ✅ 20+ checkpoints executed with metrics captured
- ✅ 3+ auto-improvements applied successfully
- ✅ Knowledge graph has checkpoint + self-improvement nodes
- ✅ User reports: "System auto-improved itself without me noticing"

---

### Month 1: Optimization

**Deliverables:**
- [ ] 100+ checkpoint executions logged
- [ ] Pattern detection accuracy ≥70%
- [ ] Auto-apply success rate ≥60%
- [ ] learnings.md promoted to CLAUDE.md (≥2 occurrences)
- [ ] Failure rate trending downward

**Success Criteria:**
- ✅ Checkpoint failure rate <15% (down from baseline ~25%)
- ✅ Auto-improvements apply without user intervention ≥80% of time
- ✅ Knowledge graph used for pattern detection in <100ms
- ✅ User experience: "Invisible intelligence" working

---

### Month 3: Maturity

**Deliverables:**
- [ ] 500+ checkpoint executions
- [ ] Failure rate <10%
- [ ] Auto-fix success rate ≥80%
- [ ] Predictive analysis accuracy ≥85%
- [ ] Self-healing resolves 95% of transient failures

**Success Criteria:**
- ✅ System rarely fails on same issue twice
- ✅ New patterns auto-learned and applied within 24 hours
- ✅ CLAUDE.md, agents, skills continuously improving
- ✅ User describes system as "gets smarter every day"

---

## Part 7: Getting Started

### Immediate Next Steps (This Week)

1. **Create checkpoint 4 script** (highest value)
   ```bash
   mkdir -p .claude/checkpoints
   # Copy checkpoint_4_execution.sh from this doc
   chmod +x .claude/checkpoints/checkpoint_4_execution.sh
   ```

2. **Test on existing phase**
   ```bash
   .claude/checkpoints/checkpoint_4_execution.sh 13.2 13.2-01
   # Verify metrics captured in .claude/metrics/13.2/13.2-01.json
   ```

3. **Install context7 MCP** (immediate value for development)
   ```bash
   claude mcp add context7
   ```

4. **Create verifier agent**
   ```bash
   # Copy change-verifier.md to .claude/agents/
   ```

5. **Add PostToolUse hook** (graph updates on edit)
   ```bash
   # Add to .claude/settings.json
   # Create .claude/hooks/post-edit-graph-update.py
   ```

---

### Phase 14 Planning Prep

**Before starting Phase 14 planning:**
- [ ] Checkpoints 1-4 working
- [ ] Auto-improver MVP functional
- [ ] At least 5 auto-improvements applied
- [ ] Knowledge graph queries returning results

**Phase 14 will add:**
- Full codebase indexing (all 259 Python files)
- Vector embeddings for semantic search
- Planning doc linkage
- Git commit tracking

---

### Phase 15 Planning Prep

**Before starting Phase 15 planning:**
- [ ] Phase 14 knowledge graph complete
- [ ] 100+ checkpoints executed with patterns
- [ ] Auto-improvement loop proven (≥20 successful auto-applies)
- [ ] Failure rate declining trend visible

**Phase 15 will add:**
- Autonomous refactoring execution
- Performance optimization agents
- Predictive failure analysis
- A/B testing framework

---

## Appendix A: Full Checkpoint Scripts

### Checkpoint 1: Discussion Validation

```bash
#!/usr/bin/env bash
# Checkpoint 1: Discussion Validation

set -euo pipefail

PHASE=$1
DISCUSSION_FILE=".planning/phases/${PHASE}/${PHASE}-DISCUSSION-STATE.md"

echo "=== Checkpoint 1: Discussion Validation ==="

if [ ! -f "$DISCUSSION_FILE" ]; then
  echo "❌ FAIL: Discussion file missing: $DISCUSSION_FILE"
  exit 1
fi

# Check required sections
required_sections=("domain" "decisions" "specifics")
for section in "${required_sections[@]}"; do
  if ! grep -q "<$section>" "$DISCUSSION_FILE"; then
    echo "❌ FAIL: Missing <$section> section"
    exit 1
  fi
done

# Check decisions documented (at least 3)
decision_count=$(grep -c "^### " "$DISCUSSION_FILE" || true)
if [ "$decision_count" -lt 3 ]; then
  echo "❌ FAIL: Only $decision_count decisions (need ≥3)"
  exit 1
fi

# Check success criteria defined
if ! grep -q "Success Criteria" "$DISCUSSION_FILE"; then
  echo "❌ FAIL: No success criteria defined"
  exit 1
fi

# Calculate vagueness score (for predictive analysis)
word_count=$(wc -w < "$DISCUSSION_FILE")
vague_words=$(grep -oi '\(maybe\|perhaps\|possibly\|probably\|TBD\|TODO\)' "$DISCUSSION_FILE" | wc -l || echo 0)
vagueness_score=$(awk "BEGIN {print $vague_words / $word_count}")

echo "✅ PASS: Discussion complete and validated"
echo "Decisions: $decision_count"
echo "Vagueness score: $vagueness_score (lower is better)"
exit 0
```

### Checkpoint 2: Research Validation

```bash
#!/usr/bin/env bash
# Checkpoint 2: Research Validation

set -euo pipefail

PHASE=$1
RESEARCH_FILE=".planning/phases/${PHASE}/${PHASE}-RESEARCH.md"

echo "=== Checkpoint 2: Research Validation ==="

if [ ! -f "$RESEARCH_FILE" ]; then
  echo "❌ FAIL: Research file missing: $RESEARCH_FILE"
  exit 1
fi

# Verify research depth (character count)
char_count=$(wc -c < "$RESEARCH_FILE")
if [ "$char_count" -lt 2000 ]; then
  echo "❌ FAIL: Research too shallow ($char_count chars, need ≥2000)"
  exit 1
fi

# Extract dependencies mentioned
dependencies=$(grep -oP '`[a-z0-9_-]+`' "$RESEARCH_FILE" | sort -u | wc -l)

# Check for standard patterns
if ! grep -q -E "(standard|recommended|industry)" "$RESEARCH_FILE"; then
  echo "⚠️  WARNING: No standard patterns referenced"
fi

echo "✅ PASS: Research complete and validated"
echo "Depth: $char_count characters"
echo "Dependencies mentioned: $dependencies"
exit 0
```

### Checkpoint 3: Plan Validation

```bash
#!/usr/bin/env bash
# Checkpoint 3: Plan Validation

set -euo pipefail

PHASE=$1
PLAN_DIR=".planning/phases/${PHASE}-*"

echo "=== Checkpoint 3: Plan Validation ==="

# Find all plan files
plan_files=($PLAN_DIR/*-PLAN.md)
if [ ${#plan_files[@]} -eq 0 ]; then
  echo "❌ FAIL: No plan files found in $PLAN_DIR"
  exit 1
fi

total_plans=${#plan_files[@]}
echo "Found $total_plans plan(s)"

# Check each plan structure
for plan_file in "${plan_files[@]}"; do
  echo "Checking: $(basename "$plan_file")"

  required=("Goal" "Files" "Tests" "Steps")
  for section in "${required[@]}"; do
    if ! grep -q "## $section" "$plan_file"; then
      echo "❌ FAIL: Missing ## $section in $(basename "$plan_file")"
      exit 1
    fi
  done

  # Check test command specified
  if ! grep -q "pytest\|npm.*test" "$plan_file"; then
    echo "❌ FAIL: No test command in $(basename "$plan_file")"
    exit 1
  fi
done

echo "✅ PASS: All plans validated"
echo "Plans: $total_plans"
exit 0
```

---

## Appendix B: Episode Type Extensions

**Add to:** `src/core/synthex_entities.py`

```python
class EpisodeType(str, Enum):
    # ... existing episode types ...

    # Progressive Verification types
    CHECKPOINT_VALIDATION = "checkpoint_validation"
    SELF_IMPROVEMENT = "self_improvement"
    CODE_MODIFICATION = "code_modification"
    PATTERN_DETECTED = "pattern_detected"
    AUTO_FIX_APPLIED = "auto_fix_applied"
```

---

## Summary: What You Get

### Immediate Benefits (Week 1)
- ✅ Checkpoint validation catches failures early
- ✅ Metrics capture enables pattern analysis
- ✅ Root cause extraction speeds debugging

### Short-term Benefits (Month 1)
- ✅ Auto-improvements applied without manual intervention
- ✅ Knowledge graph provides instant pattern detection
- ✅ Failure rates decline as system learns

### Long-term Benefits (Month 3+)
- ✅ System rarely fails on same issue twice
- ✅ CLAUDE.md, agents, skills continuously evolve
- ✅ "Invisible intelligence" - you just work, system improves itself
- ✅ Approaching zero-failure state

---

**Ready to implement?** Start with checkpoint_4_execution.sh and build from there!
