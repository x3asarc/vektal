#!/usr/bin/env python3
"""
Lightweight Health Gate PreToolUse Hook (Phase 15).

Fast (<5ms) cache-based health check for PreToolUse hook system.
Reads .graph/health-cache.json (written by health_monitor daemon).

Never blocks conversation flow - always exits 0.
Logs warnings for stale cache or detected issues.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HEALTH_CACHE_PATH = PROJECT_ROOT / ".graph" / "health-cache.json"
LOG_PATH = PROJECT_ROOT / ".graph" / "health-gate.log"

STALENESS_THRESHOLD_SECONDS = 300  # 5 minutes


def _log(message: str) -> None:
    """Append log message to health-gate.log."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Silent failure - never block


def _read_cache() -> dict | None:
    """Read health cache with error handling."""
    if not HEALTH_CACHE_PATH.exists():
        return None

    try:
        return json.loads(HEALTH_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        _log(f"WARN: Failed to parse health cache: {exc}")
        return None


def _is_stale(cache: dict, threshold_seconds: int) -> bool:
    """Check if cache is older than threshold."""
    try:
        updated_at_str = cache.get("daemon", {}).get("updated_at")
        if not updated_at_str:
            return True

        updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()
        return age_seconds > threshold_seconds

    except Exception:
        return True  # Assume stale on parse error


def main() -> int:
    """Main hook execution - always returns 0 (never blocks)."""
    start_time = time.perf_counter()

    cache = _read_cache()

    if cache is None:
        _log("WARN: Health cache missing - daemon may not be running (this is OK on first session start)")
        return 0  # Continue anyway

    if _is_stale(cache, STALENESS_THRESHOLD_SECONDS):
        _log("WARN: Health cache is stale (>5min) - daemon may have stopped")
        return 0  # Continue anyway

    # Log detected issues (informational only)
    sentry = cache.get("sentry", {})
    if sentry.get("status") == "issues":
        issue_count = sentry.get("issue_count", 0)
        _log(f"INFO: {issue_count} Sentry issue(s) detected - auto-heal daemon will handle in background")

    neo4j = cache.get("neo4j", {})
    if neo4j.get("status") == "down":
        _log("WARN: Neo4j unreachable - using local snapshot fallback")

    deps = cache.get("dependencies", {})
    if deps.get("status") == "missing":
        missing = deps.get("missing", [])
        _log(f"WARN: Missing dependencies: {missing} - background install in progress")

    elapsed_ms = (time.perf_counter() - start_time) * 1000
    _log(f"INFO: Health gate check complete in {elapsed_ms:.2f}ms")

    return 0  # ALWAYS succeed - never block


if __name__ == "__main__":
    raise SystemExit(main())
