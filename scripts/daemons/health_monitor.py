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
ROUTER_SOURCE = "scripts/daemons/health_monitor.py"

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


def _write_health(status: str, error: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Write daemon self-health status."""
    _ensure_graph_dir()
    payload = {
        "pid": os.getpid(),
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": error,
        "metadata": metadata or {},
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
        # Remediation now handled by handle_health_issues() via orchestrator

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
    org_slug = os.getenv("SENTRY_ORG_SLUG")
    project_slug = os.getenv("SENTRY_PROJECT_SLUG")

    if not auth_token or not org_slug or not project_slug:
        missing = []
        if not auth_token:
            missing.append("SENTRY_AUTH_TOKEN")
        if not org_slug:
            missing.append("SENTRY_ORG_SLUG")
        if not project_slug:
            missing.append("SENTRY_PROJECT_SLUG")
        logger.debug("[HealthMonitor] Sentry not configured (%s); skipping check.", ", ".join(missing))
        return {
            "status": "not_configured",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
            "active_issue_ids": [],
            "active_issue_fingerprints": [],
            "last_triggered_at": None,
            "context_telemetry": _default_context_telemetry(),
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
                "active_issue_ids": [],
                "active_issue_fingerprints": [],
                "last_triggered_at": None,
                "context_telemetry": _default_context_telemetry(),
            }

        issues = resp.json()
        issue_count = len(issues)

        if issue_count > 0:
            logger.info("[HealthMonitor] Sentry: %s unresolved issue(s) detected.", issue_count)
            routing = await _trigger_auto_heal(issues)
            return {
                "status": "issues",
                "issue_count": issue_count,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "auto_heal_running": routing["auto_heal_running"],
                "issue_ids": [str(issue.get("id", "unknown")) for issue in issues],
                "active_issue_ids": routing["active_issue_ids"],
                "active_issue_fingerprints": routing["active_issue_fingerprints"],
                "last_triggered_at": routing["last_triggered_at"],
                "context_telemetry": routing["context_telemetry"],
            }

        logger.info("[HealthMonitor] Sentry: No unresolved issues.")
        return {
            "status": "healthy",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
            "active_issue_ids": [],
            "active_issue_fingerprints": [],
            "last_triggered_at": None,
            "context_telemetry": _default_context_telemetry(),
        }

    except Exception as exc:
        # Transient network/egress failures should not page as runtime errors.
        logger.warning("[HealthMonitor] Sentry check failed: %s", exc)
        return {
            "status": "unreachable",
            "issue_count": 0,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "auto_heal_running": False,
            "active_issue_ids": [],
            "active_issue_fingerprints": [],
            "last_triggered_at": None,
            "context_telemetry": _default_context_telemetry(),
        }


def _default_context_telemetry() -> Dict[str, Any]:
    return {
        "graph_attempted": False,
        "graph_used": False,
        "fallback_used": False,
        "fallback_reason": "not_applicable_health_monitor",
        "latency_ms": 0,
        "assembled_tokens": 0,
    }


def _issue_fingerprint(issue: Dict[str, Any]) -> str:
    issue_id = str(issue.get("id", "unknown")).strip().lower()
    title = str(issue.get("title", "")).strip().lower()
    culprit = str(issue.get("culprit", "")).strip().lower()
    return f"{issue_id}|{title}|{culprit}"


def _issue_payload_for_event(issue: Dict[str, Any]) -> Dict[str, Any]:
    metadata = issue.get("metadata") if isinstance(issue.get("metadata"), dict) else {}
    return {
        "issue_id": str(issue.get("id", "unknown")),
        "level": str(issue.get("level", "error")),
        "error_type": str(issue.get("error_type") or metadata.get("type") or issue.get("type") or "UnknownError"),
        "affected_module": str(issue.get("affected_module") or issue.get("culprit") or "unknown"),
        "timestamp": str(issue.get("lastSeen") or datetime.now(timezone.utc).isoformat()),
        "title": str(issue.get("title", "")),
    }


def _emit_issue_routed_event(
    issue: Dict[str, Any],
    *,
    routing_status: str,
    context_telemetry: Dict[str, Any],
    detail: str = "",
) -> None:
    try:
        from src.memory.event_log import append_event
        from src.memory.event_schema import EventType, create_event

        payload = _issue_payload_for_event(issue)
        payload["routing_status"] = routing_status
        payload["detail"] = detail
        payload.update(context_telemetry)

        envelope = create_event(
            event_type=EventType.SENTRY_ISSUE_ROUTED,
            provider="sentry",
            session_id=f"health-monitor-{os.getpid()}",
            source=ROUTER_SOURCE,
            scope={"phase": "15.1", "issue_id": payload["issue_id"]},
            payload=payload,
            provenance={"component": "health_monitor"},
        )
        append_event(envelope, fail_open=True)
    except Exception as exc:
        logger.warning("[HealthMonitor] Failed to emit sentry_issue_routed event: %s", exc)


async def _trigger_auto_heal(issues: list[Dict[str, Any]]) -> Dict[str, Any]:
    """Spawn orchestrate_healers.py for each issue in background with per-issue dedupe."""
    prev_auto_heal_running = False
    prev_active_fingerprints: set[str] = set()
    try:
        if HEALTH_CACHE_PATH.exists():
            cache = json.loads(HEALTH_CACHE_PATH.read_text(encoding="utf-8"))
            sentry_cache = cache.get("sentry", {})
            prev_auto_heal_running = bool(sentry_cache.get("auto_heal_running"))
            prev_active_fingerprints = set(sentry_cache.get("active_issue_fingerprints", []))
    except Exception:
        prev_auto_heal_running = False
        prev_active_fingerprints = set()

    logger.info("[HealthMonitor] Spawning auto-heal for %s issue(s).", len(issues))
    context_telemetry = _default_context_telemetry()
    seen_cycle_fingerprints: set[str] = set()
    active_issue_ids: list[str] = []
    active_issue_fingerprints: list[str] = []
    last_triggered_at: Optional[str] = None

    for issue in issues:
        try:
            fingerprint = _issue_fingerprint(issue)
            issue_id = str(issue.get("id", "unknown"))
            if fingerprint in seen_cycle_fingerprints:
                _emit_issue_routed_event(
                    issue,
                    routing_status="skipped_duplicate_same_cycle",
                    context_telemetry=context_telemetry,
                )
                continue
            seen_cycle_fingerprints.add(fingerprint)

            if prev_auto_heal_running and fingerprint in prev_active_fingerprints:
                _emit_issue_routed_event(
                    issue,
                    routing_status="skipped_already_running",
                    context_telemetry=context_telemetry,
                )
                continue

            # Normalize issue to FailureEvent format
            issue_json = json.dumps({
                "event_id": issue_id,
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
            active_issue_ids.append(issue_id)
            active_issue_fingerprints.append(fingerprint)
            last_triggered_at = datetime.now(timezone.utc).isoformat()

            # Log to auto-heal log
            _log_auto_heal_event("triggered", issue_id=issue_id, title=issue.get("title"))
            _emit_issue_routed_event(
                issue,
                routing_status="triggered",
                context_telemetry=context_telemetry,
            )

        except Exception as exc:
            logger.error("[HealthMonitor] Failed to spawn auto-heal for issue %s: %s", issue.get("id"), exc)
            _emit_issue_routed_event(
                issue,
                routing_status="trigger_failed",
                context_telemetry=context_telemetry,
                detail=str(exc),
            )

    return {
        "auto_heal_running": bool(active_issue_ids),
        "active_issue_ids": active_issue_ids,
        "active_issue_fingerprints": active_issue_fingerprints,
        "last_triggered_at": last_triggered_at,
        "context_telemetry": context_telemetry,
    }


def _log_auto_heal_event(event_type: str, issue_id: str, title: str = "", detail: str = "") -> None:
    """Append to auto-heal log (JSONL format)."""
    _ensure_graph_dir()
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "issue_id": issue_id,
        "title": title,
        "detail": detail,
    }
    try:
        with AUTO_HEAL_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as exc:
        logger.warning("[HealthMonitor] Failed to write auto-heal log: %s", exc)


async def _trigger_neo4j_remediation(neo4j_state: Dict[str, Any]) -> None:
    """Trigger Neo4j health remediator via orchestrator."""
    import time

    issue_id = f"neo4j-down-{int(time.time())}"
    uri = neo4j_state.get("uri", "unknown")

    logger.info("[HealthMonitor] Triggering Neo4j remediation for %s", uri)

    synthetic_issue = {
        "id": issue_id,
        "category": "LOCAL_NEO4J_START_FAIL",
        "error_type": "ConnectionRefusedError",
        "error_message": f"Neo4j unreachable at {uri}",
        "affected_module": "src.core.graphiti_client",
        "traceback": "",
    }

    try:
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "graph" / "orchestrate_healers.py"),
            "--issue-json",
            json.dumps(synthetic_issue),
        ]
        subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _log_auto_heal_event("neo4j_down", issue_id=issue_id, detail=uri)
        logger.info("[HealthMonitor] Neo4j remediation spawned successfully.")
    except Exception as exc:
        logger.error("[HealthMonitor] Failed to spawn Neo4j remediation: %s", exc)


async def _trigger_dependency_remediation(deps_state: Dict[str, Any]) -> None:
    """Trigger dependency remediator via orchestrator for each missing dependency."""
    import time

    missing = deps_state.get("missing", [])
    if not missing:
        return

    logger.info("[HealthMonitor] Triggering dependency remediation for: %s", missing)

    for missing_dep in missing:
        issue_id = f"dep-missing-{missing_dep}-{int(time.time())}"

        synthetic_issue = {
            "id": issue_id,
            "category": "CONFIG",
            "error_type": "ModuleNotFoundError",
            "error_message": f"Module '{missing_dep}' not found",
            "affected_module": "dependencies",
            "traceback": "",
        }

        try:
            cmd = [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "graph" / "orchestrate_healers.py"),
                "--issue-json",
                json.dumps(synthetic_issue),
            ]
            subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _log_auto_heal_event("dependency_missing", issue_id=issue_id, detail=missing_dep)
            logger.info("[HealthMonitor] Dependency remediation spawned for %s.", missing_dep)
        except Exception as exc:
            logger.error("[HealthMonitor] Failed to spawn dependency remediation for %s: %s", missing_dep, exc)


async def handle_health_issues(state: Dict[str, Any]) -> None:
    """Route detected health issues to remediation orchestrator."""
    # Check for duplicate triggers (avoid re-triggering same issue)
    try:
        if HEALTH_CACHE_PATH.exists():
            prev_cache = json.loads(HEALTH_CACHE_PATH.read_text(encoding="utf-8"))
        else:
            prev_cache = {}
    except Exception:
        prev_cache = {}

    # 1. Sentry issues (already handled by check_sentry via _trigger_auto_heal)
    # No action needed here - Sentry auto-heal is inline

    # 2. Neo4j down
    neo4j_state = state.get("neo4j", {})
    prev_neo4j_state = prev_cache.get("neo4j", {})

    if (neo4j_state.get("status") == "down" and
        prev_neo4j_state.get("status") != "down"):  # Only trigger on state change
        logger.info("[HealthMonitor] Neo4j down detected, triggering remediation.")
        await _trigger_neo4j_remediation(neo4j_state)

    # 3. Missing dependencies
    deps_state = state.get("dependencies", {})
    prev_deps_state = prev_cache.get("dependencies", {})

    current_missing = set(deps_state.get("missing", []))
    prev_missing = set(prev_deps_state.get("missing", []))
    new_missing = current_missing - prev_missing

    if new_missing:  # Only trigger for newly detected missing deps
        logger.info("[HealthMonitor] New missing dependencies detected: %s", new_missing)
        await _trigger_dependency_remediation({"missing": list(new_missing)})


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

    # Trigger remediation for detected issues
    await handle_health_issues(state)

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

                _write_health(
                    "running",
                    metadata={
                        "auto_heal_running": state.get("sentry", {}).get("auto_heal_running", False),
                        "active_issue_ids": state.get("sentry", {}).get("active_issue_ids", []),
                        "last_triggered_at": state.get("sentry", {}).get("last_triggered_at"),
                    },
                )

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
