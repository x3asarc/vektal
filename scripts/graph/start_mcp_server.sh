#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ "${1:-}" == "--help" ]]; then
  echo "Usage: scripts/graph/start_mcp_server.sh"
  echo "Starts the synthex MCP graph server (stdio transport)."
  exit 0
fi

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"

PYTHON_BIN="${ROOT_DIR}/venv/bin/python"
if [[ -x "${ROOT_DIR}/venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="${ROOT_DIR}/venv/Scripts/python.exe"
elif [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python"
fi

"$PYTHON_BIN" - <<'PY'
from src.core.graphiti_client import check_graph_availability
ok = check_graph_availability(timeout_seconds=1.5)
print("graph_available=" + ("true" if ok else "false"))
PY

exec "$PYTHON_BIN" src/graph/mcp_server.py
