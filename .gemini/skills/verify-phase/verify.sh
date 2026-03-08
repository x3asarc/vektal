#!/usr/bin/env bash
# Progressive Phase Verification - MVP
# Runs all 4 checkpoints for a phase

set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Usage: verify-phase <phase-id>"
  echo "Example: verify-phase 14"
  exit 1
fi

PHASE=$1
PHASE_DIR=$(ls -d .planning/phases/${PHASE}* 2>/dev/null | head -1)

echo "=== Progressive Verification: Phase $PHASE ==="
echo ""

# Check phase directory exists
if [ -z "$PHASE_DIR" ] || [ ! -d "$PHASE_DIR" ]; then
  echo "❌ Phase directory not found: .planning/phases/${PHASE}*"
  exit 1
fi

echo "Phase directory: $PHASE_DIR"
echo ""

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

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Checkpoint $num: ${name^} Validation"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""

  if .claude/checkpoints/checkpoint_${num}_${name}.sh "$PHASE"; then
    echo ""
    echo "✅ CP$num ($name): PASS"
  else
    echo ""
    echo "❌ CP$num ($name): FAIL"
    failed_checkpoint="$num:$name"
    break  # Stop at first failure
  fi
  echo ""
done

# If earlier checkpoints failed, don't run execution
if [ -n "$failed_checkpoint" ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "Verification Summary"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "❌ Failed at checkpoint $failed_checkpoint"
  echo "Skipping execution checkpoint (earlier stage must pass first)"
  echo ""
  exit 1
fi

# Run checkpoint 4 for all plans in phase
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Checkpoint 4: Execution Validation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

plan_files=("$PHASE_DIR"/*-PLAN.md)
total_plans=0
passed_plans=0
failed_plans=0

for plan_file in "${plan_files[@]}"; do
  if [ -f "$plan_file" ]; then
    ((total_plans++))
  fi
done

if [ $total_plans -eq 0 ]; then
  echo "⚠️  No plan files found in $PHASE_DIR"
  exit 0
fi

echo "Found $total_plans plan(s) to validate"
echo ""

for plan_file in "${plan_files[@]}"; do
  if [ ! -f "$plan_file" ]; then
    continue
  fi

  plan_id=$(basename "$plan_file" | sed 's/-PLAN.md//')

  echo "────────────────────────────────────────────────"
  echo "Plan: $plan_id"
  echo "────────────────────────────────────────────────"
  echo ""

  if .claude/checkpoints/checkpoint_4_execution.sh "$PHASE" "$plan_id"; then
    ((passed_plans++))
    echo ""
  else
    ((failed_plans++))
    echo ""
    echo "⚠️  Check .claude/metrics/$PHASE/$plan_id.json for details"
    echo "⚠️  Auto-improver may be running in background..."
    echo ""
  fi
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Verification Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Phase: $PHASE"
echo "Total plans: $total_plans"
echo "Passed: $passed_plans"
echo "Failed: $failed_plans"
echo ""

if [ $failed_plans -eq 0 ]; then
  echo "✅ All checkpoints passed!"
  echo ""
  exit 0
else
  echo "❌ Some checkpoints failed"
  echo ""
  echo "Next steps:"
  echo "  1. Check metrics: ls -la .claude/metrics/$PHASE/"
  echo "  2. Check learnings: tail .claude/learnings.md"
  echo "  3. Check escalations: cat .claude/escalations/pending-improvements.json"
  echo "  4. Wait for auto-improver to finish (check /tmp/auto-improver.log)"
  echo ""
  exit 1
fi
