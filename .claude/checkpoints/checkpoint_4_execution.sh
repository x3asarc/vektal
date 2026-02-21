#!/usr/bin/env bash
# Checkpoint 4: Execution Validation + Intelligence Collection
# Part of Progressive Verification MVP

set -euo pipefail

PHASE=$1
PLAN=$2
PLAN_FILE=".planning/phases/${PHASE}*/PLAN.md"
METRICS_FILE=".claude/metrics/${PHASE}/${PLAN}.json"

echo "=== Checkpoint 4: Execution Validation ==="
echo "Phase: $PHASE"
echo "Plan: $PLAN"

# Find plan file (handle phase directories with suffixes)
plan_path=$(ls .planning/phases/${PHASE}*/${PLAN}-PLAN.md 2>/dev/null | head -1)
if [ -z "$plan_path" ]; then
  echo "❌ FAIL: Plan file not found: ${PHASE}*/${PLAN}-PLAN.md"
  exit 1
fi

echo "Plan file: $plan_path"

# 1. Extract test command from plan
test_cmd=$(grep -oP 'pytest.*|npm.*test.*' "$plan_path" | head -1)
if [ -z "$test_cmd" ]; then
  echo "❌ FAIL: No test command found in plan"
  echo "Hint: Add a test command like 'pytest tests/...' to the plan"
  exit 1
fi

echo "Test command: $test_cmd"

# 2. Run tests and capture output
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

# 3. Parse test results
passed=0
failed=0
if echo "$test_cmd" | grep -q pytest; then
  # Python pytest
  passed=$(grep -oP '\d+(?= passed)' /tmp/test_output.txt 2>/dev/null || echo 0)
  failed=$(grep -oP '\d+(?= failed)' /tmp/test_output.txt 2>/dev/null || echo 0)
elif echo "$test_cmd" | grep -q npm; then
  # Node test runner
  passed=$(grep -oP '\d+(?= pass)' /tmp/test_output.txt 2>/dev/null || echo 0)
  failed=$(grep -oP '\d+(?= fail)' /tmp/test_output.txt 2>/dev/null || echo 0)
fi

# 4. Root cause extraction (intelligence for auto-improver)
root_cause="unknown"
suggested_fix=""

if [ "$test_result" == "FAIL" ]; then
  # Check for common failure patterns
  if grep -q "ModuleNotFoundError" /tmp/test_output.txt; then
    missing_module=$(grep -oP "ModuleNotFoundError: No module named '\K[^']+'" /tmp/test_output.txt 2>/dev/null | head -1)
    if [ -n "$missing_module" ]; then
      root_cause="missing_dependency:${missing_module}"
      suggested_fix="Add ${missing_module} to requirements.txt and run: pip install ${missing_module}"
    else
      root_cause="missing_dependency:unknown"
      suggested_fix="Check ModuleNotFoundError in test output for missing package name"
    fi
  elif grep -q "ImportError" /tmp/test_output.txt; then
    root_cause="import_error"
    suggested_fix="Check file structure and import paths"
  elif grep -q "AssertionError" /tmp/test_output.txt; then
    root_cause="assertion_failed"
    suggested_fix="Logic error in implementation - review test expectations"
  elif grep -q "SyntaxError" /tmp/test_output.txt; then
    root_cause="syntax_error"
    suggested_fix="Fix syntax errors in code"
  elif grep -q "AttributeError" /tmp/test_output.txt; then
    root_cause="attribute_error"
    suggested_fix="Check object attributes and method names"
  elif grep -q "TypeError" /tmp/test_output.txt; then
    root_cause="type_error"
    suggested_fix="Check function arguments and types"
  elif grep -q "ValueError" /tmp/test_output.txt; then
    root_cause="value_error"
    suggested_fix="Check input values and validation"
  fi
fi

# 5. Save metrics (input for auto-improver)
mkdir -p "$(dirname "$METRICS_FILE")"
cat > "$METRICS_FILE" <<EOF
{
  "phase": "$PHASE",
  "plan": "$PLAN",
  "timestamp": "$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)",
  "duration_seconds": $duration,
  "test_result": "$test_result",
  "tests_passed": ${passed},
  "tests_failed": ${failed},
  "exit_code": $exit_code,
  "root_cause": "$root_cause",
  "suggested_fix": "$suggested_fix",
  "test_command": "$test_cmd"
}
EOF

# 6. Trigger auto-improver on failure (background)
if [ "$test_result" == "FAIL" ]; then
  echo ""
  echo "❌ FAIL: Tests failed ($failed failed, $passed passed)"
  echo "Root cause: $root_cause"
  echo "Suggested fix: $suggested_fix"
  echo ""
  echo "Metrics saved: $METRICS_FILE"

  # Trigger auto-improver in background (if it exists)
  if [ -f ".claude/auto-improver/on_execution_complete.py" ]; then
    echo "🔧 Triggering auto-improver in background..."
    nohup python .claude/auto-improver/on_execution_complete.py "$METRICS_FILE" > /tmp/auto-improver.log 2>&1 &
    echo "Auto-improver PID: $!"
  else
    echo "⚠️  Auto-improver not found - skipping automatic improvement"
  fi

  exit 1
fi

echo "✅ PASS: All tests passed ($passed passed, 0 failed)"
echo "Duration: ${duration}s"
echo "Metrics saved: $METRICS_FILE"
exit 0
