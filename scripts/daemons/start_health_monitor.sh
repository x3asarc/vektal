#!/usr/bin/env bash
# Start Health Monitor Daemon
# Usage: bash scripts/daemons/start_health_monitor.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$PROJECT_ROOT/.graph/health-monitor.pid"
LOG_FILE="$PROJECT_ROOT/.graph/health-monitor.log"

cd "$PROJECT_ROOT"

# Check if already running
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "[HealthMonitor] Already running (PID=$PID)"
        exit 0
    else
        echo "[HealthMonitor] Stale PID file found; removing"
        rm -f "$PID_FILE"
    fi
fi

# Ensure .graph directory exists
mkdir -p "$PROJECT_ROOT/.graph"

# Start daemon in background
echo "[HealthMonitor] Starting daemon..."
nohup python scripts/daemons/health_monitor.py --daemon > "$LOG_FILE" 2>&1 &

# Wait for PID file to be created (max 5 seconds)
for i in {1..10}; do
    if [[ -f "$PID_FILE" ]]; then
        PID=$(cat "$PID_FILE")
        echo "[HealthMonitor] Daemon started successfully (PID=$PID)"
        echo "[HealthMonitor] Logs: $LOG_FILE"
        exit 0
    fi
    sleep 0.5
done

echo "[HealthMonitor] WARNING: Daemon started but PID file not created within 5s"
exit 1
