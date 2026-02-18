#!/usr/bin/env bash
# scripts/harness/ui/run_e2e.sh
# Run Playwright E2E tests and emit a harness evidence report.
# Usage: bash scripts/harness/ui/run_e2e.sh [--headed] [--test <pattern>]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
RESULTS_DIR="$REPO_ROOT/test-results/playwright-artifacts"
REPORT_DIR="$REPO_ROOT/test-results/playwright-report"

mkdir -p "$RESULTS_DIR" "$REPORT_DIR"

HEADED=""
TEST_FILTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --headed) HEADED="--headed"; shift ;;
    --test)   TEST_FILTER="$2"; shift 2 ;;
    *)        echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "=== Playwright E2E Harness ==="
echo "Results: $RESULTS_DIR"
echo "Report:  $REPORT_DIR"
echo ""

# Install Playwright browsers if not present
if ! npx --prefix "$REPO_ROOT/frontend" playwright --version &>/dev/null 2>&1; then
  echo "Installing Playwright browsers..."
  npx --prefix "$REPO_ROOT/frontend" playwright install --with-deps chromium
fi

# Run tests
CMD="npx playwright test"
if [ -n "$HEADED" ]; then CMD="$CMD $HEADED"; fi
if [ -n "$TEST_FILTER" ]; then CMD="$CMD --grep \"$TEST_FILTER\""; fi

echo "Running: $CMD"
cd "$REPO_ROOT"
eval "$CMD" || EXIT_CODE=$?

# Generate evidence index
python scripts/harness/ui/evidence_index.py \
  --results-dir "$RESULTS_DIR" \
  --output "$RESULTS_DIR/EVIDENCE_INDEX.md" || true

echo ""
echo "=== E2E Complete ==="
echo "Screenshots: $(find "$RESULTS_DIR" -name '*.png' 2>/dev/null | wc -l) files"
echo "Report: $REPORT_DIR/index.html"

exit "${EXIT_CODE:-0}"
