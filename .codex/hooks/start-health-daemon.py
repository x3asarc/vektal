#!/usr/bin/env python3
"""
SessionStart Hook: Auto-start Health Monitor Daemon.

Checks if health monitor daemon is running. If not, starts it.
Waits for first cache write (max 5s) to ensure cache is available.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PID_FILE = PROJECT_ROOT / ".graph" / "health-monitor.pid"
CACHE_FILE = PROJECT_ROOT / ".graph" / "health-cache.json"
START_SCRIPT = PROJECT_ROOT / "scripts" / "daemons" / "start_health_monitor.sh"
TOOLS_VALIDATOR = PROJECT_ROOT / "scripts" / "tools" / "validate_external_tools.py"
TOOLS_REPORT = PROJECT_ROOT / ".tooling" / "external-tools-health.json"


def _is_daemon_running() -> bool:
    """Check if daemon is already running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        # Check if process exists (Windows-compatible)
        if sys.platform == "win32":
            # On Windows, use tasklist
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
            )
            return str(pid) in result.stdout
        else:
            # On Unix, send signal 0
            import os
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def _start_tools_validator() -> None:
    """Start external tools quick validation in background for every session."""
    if not TOOLS_VALIDATOR.exists():
        print("[SessionStart] External tools validator not found; skipping")
        return

    try:
        subprocess.Popen(
            [
                sys.executable,
                str(TOOLS_VALIDATOR),
                "--mode",
                "quick",
                "--report",
                str(TOOLS_REPORT),
            ],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        print("[SessionStart] External tools quick validation started")
    except Exception as exc:
        print(f"[SessionStart] WARNING: Failed to start external tools validation: {exc}")


def main() -> int:
    """Main hook entry point."""
    _start_tools_validator()

    if _is_daemon_running():
        print("[SessionStart] Health monitor daemon already running")
        return 0

    print("[SessionStart] Starting health monitor daemon...")

    # Start daemon
    if sys.platform == "win32":
        # Windows: Use Python directly (bash scripts won't work)
        daemon_script = PROJECT_ROOT / "scripts" / "daemons" / "health_monitor.py"
        subprocess.Popen(
            [sys.executable, str(daemon_script), "--daemon"],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
    else:
        # Unix: Use bash script
        subprocess.run(
            ["bash", str(START_SCRIPT)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

    # Wait for first cache write (max 5 seconds)
    for _ in range(10):
        if CACHE_FILE.exists():
            print("[SessionStart] Health cache initialized")
            return 0
        time.sleep(0.5)

    print("[SessionStart] WARNING: Health cache not created within 5s (daemon may still be starting)")
    return 0  # Don't block session start


if __name__ == "__main__":
    raise SystemExit(main())
