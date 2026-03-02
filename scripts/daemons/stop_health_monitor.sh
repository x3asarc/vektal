#!/usr/bin/env bash
# Stop Health Monitor Daemon
# Usage: bash scripts/daemons/stop_health_monitor.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.graph/health-monitor.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "[HealthMonitor] Not running (no PID file found)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! kill -0 "$PID" 2>/dev/null; then
    echo "[HealthMonitor] Process not running (stale PID file)"
    rm -f "$PID_FILE"
    exit 0
fi

echo "[HealthMonitor] Stopping daemon (PID=$PID)..."

# Send SIGTERM for graceful shutdown
kill -TERM "$PID"

# Wait up to 10 seconds for cleanup
for i in {1..10}; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "[HealthMonitor] Daemon stopped successfully"
        rm -f "$PID_FILE" 2>/dev/null || true
        exit 0
    fi
    sleep 1
done

# Force kill if still running
echo "[HealthMonitor] WARNING: Daemon did not stop gracefully; forcing kill"
kill -KILL "$PID" 2>/dev/null || true
rm -f "$PID_FILE" 2>/dev/null || true
exit 0
