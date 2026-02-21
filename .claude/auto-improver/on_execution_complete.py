#!/usr/bin/env python3
"""
Auto-Improvement Orchestrator (MVP)
Runs after every execution, analyzes failure, proposes improvements, applies if verified
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def main(metrics_file: str):
    """Main orchestration flow"""

    print("=== Auto-Improvement Engine (MVP) ===")
    print(f"Analyzing: {metrics_file}")

    # 1. Load metrics
    try:
        with open(metrics_file) as f:
            metrics = json.load(f)
    except Exception as e:
        print(f"❌ Error loading metrics: {e}")
        return

    if metrics["test_result"] == "PASS":
        print("✅ Execution passed - no improvements needed")
        # Still log success to build historical data
        log_success_to_metrics(metrics)
        return

    print(f"\n❌ Execution failed:")
    print(f"   Phase: {metrics['phase']}")
    print(f"   Plan: {metrics['plan']}")
    print(f"   Root cause: {metrics['root_cause']}")
    print(f"   Suggested fix: {metrics['suggested_fix']}")

    # 2. Detect pattern (graph-based in Phase 14, fallback to file-based)
    print("\n🔍 Detecting patterns in codebase knowledge graph...")

    try:
        # Try importing the graph-based detector first
        from .pattern_detector_graph import find_similar_failures
        patterns = find_similar_failures(metrics)
        
        if patterns:
            proposal = patterns[0]
        else:
            # Fallback to file-based subprocess if graph found nothing or not ready
            print("   (Graph sync pending, falling back to file-based detection)")
            raise ImportError("Fallback")
            
    except (ImportError, Exception):
        try:
            pattern_result = subprocess.run(
                ["python", ".claude/auto-improver/pattern_detector_file_based.py", metrics_file],
                capture_output=True,
                text=True,
                timeout=30
            )

            if pattern_result.returncode != 0:
                print(f"⚠️  Pattern detector failed: {pattern_result.stderr}")
                log_failure_to_learnings(metrics)
                return

            proposal = json.loads(pattern_result.stdout)
        except subprocess.TimeoutExpired:
            print("⚠️  Pattern detection timed out (file scan took >30s)")
            log_failure_to_learnings(metrics)
            return
        except Exception as e:
            print(f"⚠️  Pattern detection error: {e}")
            log_failure_to_learnings(metrics)
            return

    if not proposal.get("pattern_detected"):
        print(f"⚠️  No pattern detected: {proposal.get('reason', 'Unknown')}")
        print("   Logging to learnings for future analysis...")
        log_failure_to_learnings(metrics)
        return

    print(f"✅ Pattern found:")
    print(f"   Occurrences: {proposal['occurrences']}")
    print(f"   Confidence: {proposal['confidence']:.0%}")
    print(f"   Proposed fix: {proposal['proposed_fix']}")

    # 3. Generate improvement proposal
    print("\n📝 Generating improvement proposal...")
    improvement = generate_improvement(metrics, proposal)

    if not improvement:
        print("⚠️  Could not generate improvement - escalating")
        escalate_to_user(metrics, proposal, "Unable to generate concrete improvement")
        return

    print(f"   Target: {improvement['target_file']}")
    print(f"   Change type: {improvement['change_type']}")

    # 4. Verify with verifier agent (if available)
    print("\n🔎 Verifying improvement...")
    verification = verify_change(improvement)

    if verification["verdict"] == "APPROVE":
        print(f"✅ Verified (confidence: {verification.get('confidence', improvement['confidence']):.0%})")

        # 5. Auto-apply improvement
        print("\n🚀 Auto-applying improvement...")
        try:
            apply_improvement(improvement)
            print(f"✨ System upgraded successfully!")
            print(f"   Updated: {improvement['target_file']}")

            # Mark fix in metrics for future pattern detection
            update_metrics_with_fix(metrics_file, improvement)

        except Exception as e:
            print(f"❌ Failed to apply improvement: {e}")
            escalate_to_user(metrics, proposal, f"Apply failed: {e}")

    else:
        print(f"⚠️  Verification failed: {verification.get('reasoning', 'Unknown')}")
        print(f"   Recommended action: {verification.get('recommended_action', 'Manual review')}")

        # Escalate to user
        escalate_to_user(metrics, proposal, verification.get("reasoning", "Verification failed"))

def generate_improvement(metrics: dict, proposal: dict) -> dict:
    """Generate concrete file changes based on proposal"""

    root_cause = metrics["root_cause"]

    # Determine target file and change based on root cause type
    if root_cause.startswith("missing_dependency"):
        # Update gsd-executor agent with dependency handling
        target_file = ".claude/agents/gsd-executor.md"
        change_type = "append_section"

        missing_dep = root_cause.split(":")[1] if ":" in root_cause else "unknown"

        change_content = f"""

## Handling Missing Dependencies (Auto-learned {datetime.now().strftime('%Y-%m-%d')})

When execution fails with `ModuleNotFoundError: {missing_dep}`:

1. Add to requirements.txt: `{missing_dep}==<version>`
2. Install: `pip install {missing_dep}`
3. Re-run checkpoint: `.claude/checkpoints/checkpoint_4_execution.sh`

**Pattern detected:** {proposal['occurrences']} similar failures
**Confidence:** {proposal['confidence']:.0%}
**Auto-learned from:** Phase {metrics['phase']}, Plan {metrics['plan']}

---
"""

    elif root_cause == "import_error":
        target_file = ".claude/agents/gsd-planner.md"
        change_type = "append_section"
        change_content = f"""

## File Structure Validation (Auto-learned {datetime.now().strftime('%Y-%m-%d')})

When planning new files, validate import paths:

1. Ensure parent modules have `__init__.py`
2. Verify relative import syntax matches directory structure
3. Add import verification to plan checklist

**Pattern detected:** Import errors from file structure issues
**Auto-learned from:** Phase {metrics['phase']}, Plan {metrics['plan']}

---
"""

    else:
        # Generic learning - add to learnings.md
        target_file = ".claude/learnings.md"
        change_type = "append"
        change_content = f"""

### {datetime.now().strftime('%Y-%m-%d')} | {metrics['phase']}-{metrics['plan']} (Auto-learned)
**Learning:** {proposal['proposed_fix']}
**Root cause:** {root_cause}
**Pattern strength:** {proposal['occurrences']} occurrences
**Confidence:** {proposal['confidence']:.0%}
**Status:** Auto-captured (pending promotion if pattern repeats)

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
            "occurrences": proposal["occurrences"],
            "timestamp": datetime.now().isoformat()
        }
    }

def verify_change(improvement: dict) -> dict:
    """
    Simple verification (MVP)
    Phase 14 will add verifier agent with graph queries
    """

    target = Path(improvement["target_file"])

    # Basic checks
    checks = {
        "file_exists": target.exists(),
        "syntax_valid": True,  # Assume markdown is valid for MVP
        "no_conflicts": True   # File-based can't detect conflicts (Phase 14 will)
    }

    # Low confidence if file doesn't exist (creating new file)
    confidence = improvement["confidence"]
    if not checks["file_exists"]:
        confidence *= 0.7  # Reduce confidence for new files

    # Approve if all basic checks pass and confidence ≥ 0.6 (lower threshold for MVP)
    if all(checks.values()) and confidence >= 0.6:
        return {
            "verdict": "APPROVE",
            "confidence": confidence,
            "checks": checks,
            "reasoning": "Basic validation passed (MVP mode - full verification in Phase 14)"
        }
    else:
        return {
            "verdict": "REJECT",
            "confidence": confidence,
            "checks": checks,
            "reasoning": f"Checks failed or confidence too low ({confidence:.0%})",
            "recommended_action": "Manual review required"
        }

def apply_improvement(improvement: dict):
    """Apply the verified improvement to target file"""

    target = Path(improvement["target_file"])

    if improvement["change_type"] == "append":
        # Append to file (create if doesn't exist)
        with open(target, "a", encoding="utf-8") as f:
            f.write(improvement["proposed_change"])

    elif improvement["change_type"] == "append_section":
        # Append new section to end of file
        with open(target, "a", encoding="utf-8") as f:
            f.write(improvement["proposed_change"])

def update_metrics_with_fix(metrics_file: str, improvement: dict):
    """Update metrics file with applied fix for future pattern detection"""

    try:
        with open(metrics_file, "r") as f:
            metrics = json.load(f)

        metrics["fix_applied"] = improvement["proposed_change"][:200]  # First 200 chars
        metrics["fix_success"] = None  # Unknown until next execution
        metrics["improvement_metadata"] = improvement["metadata"]

        with open(metrics_file, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not update metrics with fix: {e}")

def log_failure_to_learnings(metrics: dict):
    """Log failure to learnings.md when no pattern detected yet"""

    learnings_file = Path(".claude/learnings.md")

    entry = f"""
### {datetime.now().strftime('%Y-%m-%d')} | {metrics['phase']}-{metrics['plan']}
**Learning:** Execution failed - {metrics['suggested_fix']}
**Root cause:** {metrics['root_cause']}
**Status:** First occurrence (watch for pattern)

"""

    with open(learnings_file, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"   Logged to: {learnings_file}")

def log_success_to_metrics(metrics: dict):
    """Log successful execution for historical data"""
    # Success already captured in metrics file by checkpoint
    # This is a placeholder for future analytics
    pass

def escalate_to_user(metrics: dict, proposal: dict, reason: str):
    """Escalate rejected improvements to user for review"""

    escalation_file = Path(".claude/escalations/pending-improvements.json")
    escalation_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing escalations
    if escalation_file.exists():
        with open(escalation_file) as f:
            escalations = json.load(f)
    else:
        escalations = []

    # Add new escalation
    escalations.append({
        "timestamp": datetime.now().isoformat(),
        "phase": metrics["phase"],
        "plan": metrics["plan"],
        "root_cause": metrics["root_cause"],
        "proposed_fix": proposal.get("proposed_fix"),
        "confidence": proposal.get("confidence"),
        "reason": reason,
        "status": "pending"
    })

    # Save
    with open(escalation_file, "w") as f:
        json.dump(escalations, f, indent=2)

    print(f"\n⚠️  Escalated to: {escalation_file}")
    print("   Review and manually apply if appropriate")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: on_execution_complete.py <metrics_file.json>")
        sys.exit(1)

    metrics_file = sys.argv[1]
    main(metrics_file)
