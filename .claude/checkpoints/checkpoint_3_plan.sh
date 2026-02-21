#!/usr/bin/env bash
# Checkpoint 3: Plan Validation
# Part of Progressive Verification MVP

set -euo pipefail

PHASE=$1
PLAN_DIR=$(ls -d .planning/phases/${PHASE}* 2>/dev/null | head -1)

echo "=== Checkpoint 3: Plan Validation ==="

if [ -z "$PLAN_DIR" ] || [ ! -d "$PLAN_DIR" ]; then
  echo "❌ FAIL: Phase directory not found: ${PHASE}*"
  exit 1
fi

echo "Phase directory: $PLAN_DIR"

# Find all plan files
plan_files=("$PLAN_DIR"/*-PLAN.md)
if [ ! -e "${plan_files[0]}" ]; then
  echo "❌ FAIL: No plan files found in $PLAN_DIR"
  exit 1
fi

total_plans=${#plan_files[@]}
echo "Found $total_plans plan(s)"

# Check each plan structure
for plan_file in "${plan_files[@]}"; do
  echo ""
  echo "Checking: $(basename "$plan_file")"

  # Required sections
  required=("Goal" "Files" "Tests" "Steps")
  for section in "${required[@]}"; do
    if ! grep -q "## $section" "$plan_file"; then
      echo "❌ FAIL: Missing ## $section in $(basename "$plan_file")"
      exit 1
    fi
  done

  # Check dependencies declared
  if ! grep -q "Depends on:" "$plan_file"; then
    echo "⚠️  WARNING: No dependencies declared in $(basename "$plan_file")"
  fi

  # Check test command specified
  if ! grep -q "pytest\|npm.*test" "$plan_file"; then
    echo "❌ FAIL: No test command in $(basename "$plan_file")"
    echo "Hint: Add test command to ## Tests section (e.g., pytest tests/...)"
    exit 1
  fi

  echo "  ✓ Structure valid"
done

# Check wave structure (parallel vs sequential)
if grep -q "Wave " "$PLAN_DIR"/*-PLAN.md 2>/dev/null; then
  echo ""
  echo "✅ Wave structure detected (parallel execution possible)"
else
  echo ""
  echo "⚠️  No wave structure (sequential execution assumed)"
fi

echo ""
echo "✅ PASS: All plans validated"
echo "Plans: $total_plans"
exit 0
