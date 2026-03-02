#!/usr/bin/env python3
"""
Health Monitor Daemon (Phase 15 - Intelligent PreToolUse System).

Continuous background monitoring of:
- Sentry issues (polls API every 2 minutes)
- Neo4j connectivity (probes with 2s timeout)
- Critical dependencies (neo4j, graphiti-core)

Writes atomic health cache to .graph/health-cache.json for instant hook reads (<1ms).
Triggers auto-heal workflows in background when issues detected.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

GRAPH_DIR = PROJECT_ROOT / ".graph"
HEALTH_CACHE_PATH = GRAPH_DIR / "health-cache.json"
PID_PATH = GRAPH_DIR / "health-monitor.pid"
HEALTH_PATH = GRAPH_DIR / "health-monitor-health.json"
AUTO_HEAL_LOG_PATH = GRAPH_DIR / "auto-heal-log.jsonl"

# Global shutdown flag
_shutdown_requested = False


def _ensure_graph_dir() -> None:
    """Ensure .graph directory exists."""
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)


def _write_pid() -> None:
    """Write daemon PID to file."""
    _ensure_graph_dir()
    PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
    logger.info("[HealthMonitor] PID file written: %s", PID_PATH)


def _remove_pid() -> None:
    """Remove PID file on shutdown."""
    try:
        if PID_PATH.exists():
            PID_PATH.unlink()
            logger.info("[HealthMonitor] PID file removed.")
    except Exception as exc:
        logger.warning("[HealthMonitor] Failed to remove PID file: %s", exc)


def _signal_handler(signum: int, frame: Any) -> None:
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    global _shutdown_requested
    logger.info("[HealthMonitor] Shutdown signal received (signal=%s).", signum)
    _shutdown_requested = True


def _write_health(status: str, error: Optional[str] = None) -> None:
    """Write daemon self-health status."""
    _ensure_graph_dir()
    payload = {
        "pid": os.getpid(),
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
    }
    HEALTH_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Atomic JSON write using tmp + rename pattern."""
    _ensure_graph_dir()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=GRAPH_DIR, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # Atomic rename
        Path(tmp_path).replace(path)
        logger.debug("[HealthMonitor] Atomic write complete: %s", path)
    except Exception as exc:
        logger.error("[HealthMonitor] Atomic write failed: %s", exc)
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _can_import(module_name: str) -> bool:
    """Check if a Python module is importable."""
    python_exe = sys.executable
    try:
        proc = subprocess.run(
            [python_exe, "-c", f"import {module_name}"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=15,  # Increased timeout for slow imports like graphiti_core
        )
        return proc.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("[HealthMonitor] Import check timed out for %s (treating as unavailable)", module_name)
        return False


def check_dependencies() -> Dict[str, Any]:
    """Check critical Python dependencies."""
    required = ["neo4j", "graphiti_core"]
    missing = [mod for mod in required if not _can_import(mod)]

    status = "ok"
    if missing:
        status = "missing"
        logger.warning("[HealthMonitor] Missing dependencies: %s", missing)
        # Trigger auto-install in background
        _trigger_dependency_install(missing)
        status = "installing"

    return {
        "status": status,
        "missing": missing,
        "last_check": datetime.now(timezone.utc).isoformat(),
    }


def _trigger_dependency_install(missing: list[str]) -> None:
    """Trigger background dependency installation."""
    logger.info("[HealthMonitor] Triggering background install for: %s", missing)
    try:
        # Spawn non-blocking pip install
        subprocess.Popen(
            [sys.executable, "-m", "pip", "install"] + missing,
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.error("[HealthMonitor] Failed to trigger pip install: %s", exc)


def check_neo4j() -> Dict[str, Any]:
    """Probe Neo4j connectivity with timeout."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.warning("[HealthMonitor] neo4j module not available.")
        return {
            "status": "down",
            "uri": None,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "mode": "local_snapshot",
        }

    # Load Neo4j credentials from .env
    env_path = PROJECT_ROOT / ".env"
    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_password:
        logger.warning("[HealthMonitor] NEO4J_PASSWORD not set.")
        return {
            "status": "down",
            "uri": None,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "mode": "local_snapshot",
        }

    # Try to connect
    timeout = 2.0  # 2s timeout
    try:
        # Suppress neo4j driver logging
        logging.getLogger("neo4j").setLevel(logging.CRITICAL)
        with GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password), connection_timeout=timeout) as driver:
            driver.verify_connectivity()
        logger.info("[HealthMonitor] Neo4j reachable at %s", neo4j_uri)
        return {
            "status": "up",
            "uri": neo4j_uri,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "mode": "neo4j",
        }
    except Exception as exc:
        logger.warning("[HealthMonitor] Neo4j unreachable: %s", exc)
        # Trigger fallback to local snapshot
        _trigger_snapshot_fallback()
        return {
            "status": "down",
            "uri": neo4j_uri,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "mode": "local_snapshot",
        }


def _trigger_snapshot_fallback() -> None:
    """Trigger local snapshot warming in background."""
    logger.info("[HealthMonitor] Triggering local snapshot fallback.")
    try:
        subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from src.graph.local_graph_store import get_snapshot; get_snapshot(force_refresh=True)",
            ],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.error("[HealthMonitor] Failed to trigger snapshot fallback: %s", exc)


async def check_sentry() -> Dict[str, Any]:
    """Poll Sentry API for unresolved issues (limit 5)."""
    auth_token = os.getenv("SENTRY_AUTH_TOKEN")
    org_slug = os.getenv("SENTRY_ORG_SLUG", "shopify-scraping-script")
    project_slug = os.getenv("SENTRY_PROJECT_SLUG", "shopify-scraping-script")

    if not auth_token:
        logger.debug("[HealthMonitor] SENTRY_AUTH_TOKEN not set; skipping Sentry check.")
        return {
            "status": "healthy",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
        }

    base_url = f"https://sentry.io/api/0/projects/{org_slug}/{project_slug}/issues/"
    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"query": "is:unresolved level:error", "limit": 5}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(base_url, headers=headers, params=params)

        if resp.status_code != 200:
            logger.warning("[HealthMonitor] Sentry API failed (HTTP %s)", resp.status_code)
            return {
                "status": "unreachable",
                "issue_count": 0,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "auto_heal_running": False,
            }

        issues = resp.json()
        issue_count = len(issues)

        if issue_count > 0:
            logger.info("[HealthMonitor] Sentry: %s unresolved issue(s) detected.", issue_count)
            # Trigger auto-heal in background
            await _trigger_auto_heal(issues)
            return {
                "status": "issues",
                "issue_count": issue_count,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "auto_heal_running": True,
            }

        logger.info("[HealthMonitor] Sentry: No unresolved issues.")
        return {
            "status": "healthy",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
        }

    except Exception as exc:
        logger.error("[HealthMonitor] Sentry check failed: %s", exc)
        return {
            "status": "unreachable",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
        }


async def _trigger_auto_heal(issues: list[Dict[str, Any]]) -> None:
    """Spawn orchestrate_healers.py for each issue in background."""
    # Check if auto-heal already running (read from cache)
    try:
        if HEALTH_CACHE_PATH.exists():
            cache = json.loads(HEALTH_CACHE_PATH.read_text(encoding="utf-8"))
            if cache.get("sentry", {}).get("auto_heal_running"):
                logger.info("[HealthMonitor] Auto-heal already running; skipping duplicate spawn.")
                return
    except Exception:
        pass

    logger.info("[HealthMonitor] Spawning auto-heal for %s issue(s).", len(issues))

    for issue in issues:
        try:
            # Normalize issue to FailureEvent format
            issue_json = json.dumps({
                "event_id": str(issue.get("id", "unknown")),
                "title": issue.get("title", ""),
                "category": "UNKNOWN",  # Let classifier determine
                "culprit": issue.get("culprit", "unknown"),
                "timestamp": issue.get("lastSeen", datetime.now(timezone.utc).isoformat()),
                "tags": {t["key"]: t["value"] for t in issue.get("tags", []) if isinstance(t, dict) and "key" in t},
                "level": issue.get("level", "error"),
            })

            # Spawn non-blocking subprocess
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "graph" / "orchestrate_healers.py"),
                "--issue-json",
                issue_json,
            ]
            subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Log to auto-heal log
            _log_auto_heal_event("triggered", issue_id=str(issue.get("id")), title=issue.get("title"))

        except Exception as exc:
            logger.error("[HealthMonitor] Failed to spawn auto-heal for issue %s: %s", issue.get("id"), exc)


def _log_auto_heal_event(event_type: str, issue_id: str, title: str) -> None:
    """Append to auto-heal log (JSONL format)."""
    _ensure_graph_dir()
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "issue_id": issue_id,
        "title": title,
    }
    try:
        with AUTO_HEAL_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as exc:
        logger.warning("[HealthMonitor] Failed to write auto-heal log: %s", exc)


async def run_health_check() -> Dict[str, Any]:
    """Execute one health check cycle and return full state."""
    logger.info("[HealthMonitor] Running health check cycle...")

    # Run checks in parallel
    sentry_task = asyncio.create_task(check_sentry())
    neo4j_result = check_neo4j()
    deps_result = check_dependencies()
    sentry_result = await sentry_task

    state = {
        "sentry": sentry_result,
        "neo4j": neo4j_result,
        "dependencies": deps_result,
        "daemon": {
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "check_interval_seconds": int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "120")),
        },
    }

    logger.info("[HealthMonitor] Health check complete: Sentry=%s, Neo4j=%s, Deps=%s",
                sentry_result["status"], neo4j_result["status"], deps_result["status"])

    return state


async def run_daemon(interval_seconds: int) -> None:
    """Main daemon loop with graceful shutdown."""
    global _shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    _write_pid()
    _write_health("running")

    logger.info("[HealthMonitor] Daemon started (PID=%s, interval=%ss)", os.getpid(), interval_seconds)

    try:
        while not _shutdown_requested:
            try:
                # Run health check
                state = await run_health_check()

                # Write atomic cache
                _atomic_write_json(HEALTH_CACHE_PATH, state)

                _write_health("running")

            except Exception as exc:
                logger.exception("[HealthMonitor] Health check cycle failed: %s", exc)
                _write_health("error", error=str(exc))

            # Sleep with periodic shutdown checks
            for _ in range(interval_seconds):
                if _shutdown_requested:
                    break
                await asyncio.sleep(1)

    finally:
        logger.info("[HealthMonitor] Daemon shutting down gracefully...")
        _remove_pid()
        _write_health("stopped")


async def _main_async(args: argparse.Namespace) -> int:
    """Async main entry point."""
    if args.daemon:
        await run_daemon(interval_seconds=args.interval)
        return 0

    # Single check mode
    state = await run_health_check()
    _atomic_write_json(HEALTH_CACHE_PATH, state)
    print(json.dumps(state, indent=2))
    return 0


def main() -> int:
    """Main entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Health Monitor Daemon for PreToolUse optimization.")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in daemon mode (recommended).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("HEALTH_CHECK_INTERVAL_SECONDS", "120")),
        help="Health check interval in seconds (default: 120).",
    )
    args = parser.parse_args()

    # Enforce minimum interval
    if args.interval < 30:
        logger.warning("[HealthMonitor] Interval too low; enforcing minimum 30s.")
        args.interval = 30

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
