#!/bin/bash
# Auto-triggered checkpoint after test execution
# Runs in background, non-blocking

set -euo pipefail

# Silent execution - redirect output to log
LOG_FILE=".claude/checkpoints/auto-checkpoint.log"
exec >> "$LOG_FILE" 2>&1

echo "=== Auto-Checkpoint Triggered: $(date -Iseconds) ==="

# Detect active phase/plan from STATE.md
detect_active_phase() {
    if [[ ! -f ".planning/STATE.md" ]]; then
        echo "No STATE.md found, skipping checkpoint"
        return 1
    fi

    # Extract current phase from "Phase: X of Y" line
    phase=$(grep -E "^Phase: [0-9]+" ".planning/STATE.md" | head -1 | sed -E 's/Phase: ([0-9.]+).*/\1/')

    if [[ -z "$phase" ]]; then
        echo "Could not detect phase from STATE.md"
        return 1
    fi

    echo "Detected phase: $phase"
    echo "$phase"
}

# Detect active plan from git branch or recent commits
detect_active_plan() {
    local phase=$1

    # Try git branch first (e.g., phase-14-01-implementation)
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [[ "$branch" =~ phase-[0-9.]+-([0-9.]+)- ]]; then
        plan="${phase}-${BASH_REMATCH[1]}"
        echo "Detected plan from branch: $plan"
        echo "$plan"
        return 0
    fi

    # Try recent commit message (e.g., "feat(14-01): Add feature")
    commit_msg=$(git log -1 --pretty=%s 2>/dev/null || echo "")
    if [[ "$commit_msg" =~ ([0-9.]+)-([0-9]+): ]]; then
        plan="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}"
        echo "Detected plan from commit: $plan"
        echo "$plan"
        return 0
    fi

    # Fallback: check for PLAN.md files modified recently
    recent_plan=$(git diff --name-only HEAD~1..HEAD 2>/dev/null | grep -E "\.planning/phases/.*PLAN\.md" | head -1 || echo "")
    if [[ -n "$recent_plan" ]]; then
        plan=$(basename "$(dirname "$recent_plan")" | grep -oE '[0-9.]+-[0-9]+')
        if [[ -n "$plan" ]]; then
            echo "Detected plan from recent changes: $plan"
            echo "$plan"
            return 0
        fi
    fi

    echo "Could not detect active plan"
    return 1
}

# Main execution
main() {
    # Detect phase
    phase=$(detect_active_phase) || {
        echo "Skipping checkpoint: phase detection failed"
        exit 0
    }

    # Detect plan
    plan=$(detect_active_plan "$phase") || {
        echo "Skipping checkpoint: plan detection failed"
        exit 0
    }

    echo "Running checkpoint for: Phase $phase, Plan $plan"

    # Run checkpoint 4
    bash "$(dirname "$0")/checkpoint_4_execution.sh" "$phase" "$plan" || {
        echo "Checkpoint execution failed (may be expected if no tests defined yet)"
        exit 0
    }

    # Check if tests failed by examining the metrics file
    metrics_file=".claude/metrics/${phase}/${plan}.json"
    if [[ -f "$metrics_file" ]]; then
        test_result=$(grep -oP '"test_result":\s*"\K[^"]+' "$metrics_file" || echo "UNKNOWN")

        if [[ "$test_result" == "FAIL" ]]; then
            echo "Tests failed, triggering auto-improver..."
            export PYTHONIOENCODING=utf-8
            python .claude/auto-improver/on_execution_complete.py "$metrics_file" || {
                echo "Auto-improver failed, but continuing..."
            }
        else
            echo "Tests passed, no auto-improvement needed"
        fi
    fi

    echo "Auto-checkpoint complete: $(date -Iseconds)"
}

# Run in background if not already backgrounded
if [[ "${CHECKPOINT_BACKGROUND:-}" != "1" ]]; then
    export CHECKPOINT_BACKGROUND=1
    "$0" "$@" &
    disown
    exit 0
fi

main "$@"
