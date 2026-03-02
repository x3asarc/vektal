"""
Pre-tool Sentry worker gate.

Behavior:
- If Sentry worker daemon is healthy/alive, do nothing.
- If not active, launch it detached in daemon mode.
- Always fail-open (exit 0) to avoid blocking primary workflows.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRAPH_DIR = PROJECT_ROOT / ".graph"
PID_PATH = GRAPH_DIR / "sentry-worker.pid"
HEALTH_PATH = GRAPH_DIR / "sentry-worker-health.json"


def _log(message: str, quiet: bool) -> None:
    if not quiet:
        print(message)


def _read_pid() -> Optional[int]:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _health_recent(max_age_seconds: int) -> bool:
    if not HEALTH_PATH.exists():
        return False
    try:
        payload = json.loads(HEALTH_PATH.read_text(encoding="utf-8"))
        updated_at = payload.get("updated_at")
        if not updated_at:
            return False
        ts = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age <= max_age_seconds
    except Exception:
        return False


def _launch_worker(quiet: bool) -> bool:
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "scripts/observability/sentry_issue_puller.py",
        "--daemon",
        "--interval",
        os.getenv("SENTRY_PULL_INTERVAL_SECONDS", "120"),
    ]

    kwargs = {
        "cwd": str(PROJECT_ROOT),
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "stdin": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True

    try:
        subprocess.Popen(cmd, **kwargs)
        _log("[SentryGate] Worker launch requested.", quiet)
        return True
    except Exception as exc:
        _log(f"[SentryGate] Failed to launch worker: {exc}", quiet)
        return False


def _run_once(quiet: bool) -> bool:
    cmd = [sys.executable, "scripts/observability/sentry_issue_puller.py"]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        _log(f"[SentryGate] One-shot poll executed (rc={result.returncode}).", quiet)
        return True
    except Exception as exc:
        _log(f"[SentryGate] One-shot poll failed: {exc}", quiet)
        return False


def ensure_sentry_worker(quiet: bool = False) -> int:
    load_dotenv()

    max_age_seconds = int(os.getenv("SENTRY_WORKER_HEALTH_MAX_AGE_SECONDS", "300"))
    pid = _read_pid()
    active = _health_recent(max_age_seconds)

    if active:
        _log(f"[SentryGate] Worker active (pid={pid or 'n/a'}).", quiet)
        return 0

    # Cleanup stale pid pointer if process is gone.
    if pid and not _process_alive(pid):
        try:
            PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    _log("[SentryGate] Worker inactive; launching autonomous puller daemon.", quiet)
    launched = _launch_worker(quiet)
    if not launched:
        return 0  # fail-open

    # Give daemon a moment to create/update health artifacts.
    time.sleep(1.0)
    pid = _read_pid()
    if pid and _process_alive(pid):
        _log(f"[SentryGate] Worker now active (pid={pid}).", quiet)
    else:
        _log("[SentryGate] Background launch not confirmed; running one-shot autonomous poll.", quiet)
        _run_once(quiet)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure Sentry puller daemon is active.")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    return ensure_sentry_worker(quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
