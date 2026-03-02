#!/usr/bin/env bash
# Check Health Monitor Daemon Status
# Usage: bash scripts/daemons/status_health_monitor.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.graph/health-monitor.pid"
HEALTH_FILE="$PROJECT_ROOT/.graph/health-monitor-health.json"
CACHE_FILE="$PROJECT_ROOT/.graph/health-cache.json"

echo "=== Health Monitor Daemon Status ==="
echo ""

# Check if running
if [[ ! -f "$PID_FILE" ]]; then
    echo "Status: NOT RUNNING"
    echo ""
    exit 1
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Status: STOPPED (stale PID file)"
    echo ""
    exit 1
fi

echo "Status: RUNNING"
echo "PID: $PID"
echo ""

# Display daemon health
if [[ -f "$HEALTH_FILE" ]]; then
    echo "--- Daemon Health ---"
    cat "$HEALTH_FILE"
    echo ""
fi

# Display cache status
if [[ -f "$CACHE_FILE" ]]; then
    echo "--- Health Cache ---"
    echo "Last Updated: $(stat -c %y "$CACHE_FILE" 2>/dev/null || stat -f "%Sm" "$CACHE_FILE" 2>/dev/null)"

    # Extract key status fields using Python
    python -c "
import json, sys
from pathlib import Path
cache = json.loads(Path('$CACHE_FILE').read_text())
print(f\"Sentry: {cache['sentry']['status']} ({cache['sentry']['issue_count']} issues)\")
print(f\"Neo4j: {cache['neo4j']['status']} ({cache['neo4j'].get('mode', 'unknown')})\")
print(f\"Dependencies: {cache['dependencies']['status']}\")
" 2>/dev/null || echo "Could not parse cache file"
    echo ""
else
    echo "--- Health Cache ---"
    echo "No cache file found (daemon may be starting)"
    echo ""
fi

exit 0
