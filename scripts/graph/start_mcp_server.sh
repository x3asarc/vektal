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

python - <<'PY'
from src.core.graphiti_client import check_graph_availability
ok = check_graph_availability(timeout_seconds=1.5)
print("graph_available=" + ("true" if ok else "false"))
PY

exec python src/graph/mcp_server.py
