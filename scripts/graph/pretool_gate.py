"""
Unified pre-tool gate:
1) Ensure autonomous Sentry puller daemon is active.
2) Continue with normal graph backend bootstrap.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _run(command: list[str]) -> int:
    result = subprocess.run(command, cwd=str(PROJECT_ROOT), check=False)
    return int(result.returncode)


def main() -> int:
    python = sys.executable

    # Confirmation gate: if active, no-op; if inactive, launch worker.
    _run([python, "scripts/observability/ensure_sentry_worker.py", "--quiet"])

    # Continue normal flow regardless of sentry gate outcomes (fail-open).
    _run([python, "scripts/graph/bootstrap_graph_backend.py"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
